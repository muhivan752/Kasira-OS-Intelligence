"""Kurir toko — /couriers (delivery gelombang 2, mig 108).

Semua tier. Antar itu kebutuhan dasar warung, bukan fitur analitik, dan
kurirnya orang toko sendiri: nggak ada akun, nggak ada aplikasi kurir, nggak
ada bagi hasil. Toko cuma nyatet siapa saja yang biasa nganter supaya kasir
tinggal pilih dan pelanggan tahu siapa yang datang.
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.courier import Courier
from backend.models.outlet import Outlet
from backend.models.user import User
from backend.schemas.courier import CourierCreate, CourierResponse, CourierUpdate, VEHICLES
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_vehicle(v: Optional[str]) -> None:
    if v is not None and v not in VEHICLES:
        raise HTTPException(status_code=400, detail=f"Kendaraan tidak dikenal: {v}")


async def _get_owned(db: AsyncSession, courier_id: UUID, tenant_id: UUID) -> Courier:
    cour = (await db.execute(
        select(Courier).where(
            Courier.id == courier_id, Courier.tenant_id == tenant_id, Courier.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not cour:
        raise HTTPException(status_code=404, detail="Kurir tidak ditemukan")
    return cour


@router.get("/", response_model=StandardResponse[List[CourierResponse]])
async def list_couriers(
    request: Request,
    outlet_id: Optional[UUID] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Kurir milik tenant. Yang `outlet_id` NULL berlaku buat semua outlet
    (toko satu cabang nggak perlu mikirin ini)."""
    q = select(Courier).where(Courier.tenant_id == current_user.tenant_id, Courier.deleted_at.is_(None))
    if outlet_id:
        q = q.where((Courier.outlet_id == outlet_id) | (Courier.outlet_id.is_(None)))
    if not include_inactive:
        q = q.where(Courier.is_active.is_(True))
    rows = (await db.execute(q.order_by(Courier.sort_order, Courier.name))).scalars().all()
    return StandardResponse(
        success=True, data=[CourierResponse.model_validate(c) for c in rows],
        request_id=request.state.request_id,
    )


@router.post("/", response_model=StandardResponse[CourierResponse])
async def create_courier(
    request: Request,
    body: CourierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    _check_vehicle(body.vehicle)
    name = body.name.strip()
    dup = (await db.execute(
        select(Courier).where(
            Courier.tenant_id == current_user.tenant_id,
            Courier.deleted_at.is_(None),
            func.lower(Courier.name) == name.lower(),
        )
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail=f"Kurir '{dup.name}' sudah ada")
    if body.outlet_id:
        outlet = (await db.execute(
            select(Outlet).where(Outlet.id == body.outlet_id, Outlet.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not outlet or outlet.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    cour = Courier(tenant_id=current_user.tenant_id, **body.model_dump())
    cour.name = name
    db.add(cour)
    await db.flush()
    await log_audit(
        db=db, action="CREATE", entity="couriers", entity_id=cour.id,
        after_state={"name": cour.name, "phone": cour.phone, "vehicle": cour.vehicle},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(cour)
    return StandardResponse(
        success=True, data=CourierResponse.model_validate(cour),
        message="Kurir ditambahkan", request_id=request.state.request_id,
    )


@router.put("/{courier_id}", response_model=StandardResponse[CourierResponse])
async def update_courier(
    request: Request,
    courier_id: UUID,
    body: CourierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    cour = await _get_owned(db, courier_id, current_user.tenant_id)
    if cour.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data kurir sudah berubah, muat ulang dulu")
    _check_vehicle(body.vehicle)
    before = {"name": cour.name, "phone": cour.phone, "vehicle": cour.vehicle, "is_active": cour.is_active}
    for k, v in body.model_dump(exclude_unset=True, exclude={"row_version"}).items():
        setattr(cour, k, v.strip() if isinstance(v, str) and k == "name" else v)
    cour.row_version += 1
    await log_audit(
        db=db, action="UPDATE", entity="couriers", entity_id=cour.id,
        before_state=before,
        after_state={"name": cour.name, "phone": cour.phone, "vehicle": cour.vehicle, "is_active": cour.is_active},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(cour)
    return StandardResponse(
        success=True, data=CourierResponse.model_validate(cour),
        message="Kurir diperbarui", request_id=request.state.request_id,
    )


@router.delete("/{courier_id}", response_model=StandardResponse[dict])
async def delete_courier(
    request: Request,
    courier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Soft delete (Rule #7). Pesanan lama tetap nulis nama kurirnya karena
    namanya di-snapshot ke `orders.courier_name` waktu ditugaskan."""
    cour = await _get_owned(db, courier_id, current_user.tenant_id)
    cour.deleted_at = datetime.now(timezone.utc)
    cour.row_version += 1
    await log_audit(
        db=db, action="DELETE", entity="couriers", entity_id=cour.id,
        before_state={"name": cour.name}, user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return StandardResponse(
        success=True, data={"id": str(courier_id)},
        message="Kurir dihapus", request_id=request.state.request_id,
    )
