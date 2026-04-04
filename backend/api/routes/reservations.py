"""
Kasira Reservations Route — Owner/Kasir mengelola reservasi meja

GET  /reservations/                    → list reservasi outlet
GET  /reservations/{id}               → detail reservasi
PUT  /reservations/{id}/confirm       → konfirmasi + set meja = reserved (Golden Rule #24)
PUT  /reservations/{id}/cancel        → batalkan + release meja
PUT  /reservations/{id}/complete      → selesaikan + release meja (Golden Rule #24)

Rules:
- Rule #2: Audit log setiap WRITE
- Rule #9: Async ONLY
- Rule #30: Optimistic lock via row_version
- Rule #33: reservations WAJIB row_version
- Golden Rule #24: Meja reserved otomatis saat confirmed, release saat done/cancel
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.customer import Customer
from backend.models.outlet import Outlet
from backend.models.reservation import Reservation, Table
from backend.models.user import User
from backend.services.audit import log_audit

router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])
logger = logging.getLogger(__name__)


class ConfirmReservationInput(BaseModel):
    table_id: Optional[UUID] = None


@router.get("/")
async def list_reservations(
    outlet_id: UUID = Query(..., description="ID outlet"),
    status: Optional[str] = Query(None, description="Filter status: pending/confirmed/cancelled/completed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List reservasi untuk satu outlet (owner/kasir)."""
    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    stmt = select(Reservation).where(
        Reservation.outlet_id == outlet_id,
        Reservation.deleted_at.is_(None),
    )
    if status:
        stmt = stmt.where(Reservation.status == status)
    stmt = stmt.order_by(Reservation.reservation_time.asc())

    result = await db.execute(stmt)
    reservations = result.scalars().all()

    # Bulk load customers and tables to avoid N+1
    customer_ids = list({r.customer_id for r in reservations})
    table_ids = list({r.table_id for r in reservations if r.table_id})

    customers: dict[UUID, Customer] = {}
    if customer_ids:
        cust_result = await db.execute(
            select(Customer).where(Customer.id.in_(customer_ids))
        )
        customers = {c.id: c for c in cust_result.scalars().all()}

    tables: dict[UUID, Table] = {}
    if table_ids:
        tbl_result = await db.execute(
            select(Table).where(Table.id.in_(table_ids))
        )
        tables = {t.id: t for t in tbl_result.scalars().all()}

    items = []
    for r in reservations:
        customer = customers.get(r.customer_id)
        table = tables.get(r.table_id) if r.table_id else None
        items.append({
            "id": str(r.id),
            "customer_name": customer.name if customer else "Guest",
            "customer_phone": customer.phone if customer else None,
            "table_id": str(r.table_id) if r.table_id else None,
            "table_name": table.name if table else None,
            "reservation_time": r.reservation_time.isoformat(),
            "guest_count": r.guest_count,
            "status": r.status,
            "notes": r.notes,
            "row_version": r.row_version,
            "created_at": r.created_at.isoformat(),
        })

    return {"success": True, "data": items, "meta": {"total": len(items)}}


@router.get("/{reservation_id}")
async def get_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Detail satu reservasi."""
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.deleted_at.is_(None),
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")

    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == reservation.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Akses ditolak")

    cust_result = await db.execute(select(Customer).where(Customer.id == reservation.customer_id))
    customer = cust_result.scalar_one_or_none()

    table_name = None
    if reservation.table_id:
        tbl_result = await db.execute(select(Table).where(Table.id == reservation.table_id))
        tbl = tbl_result.scalar_one_or_none()
        table_name = tbl.name if tbl else None

    return {
        "success": True,
        "data": {
            "id": str(reservation.id),
            "customer_name": customer.name if customer else "Guest",
            "customer_phone": customer.phone if customer else None,
            "table_id": str(reservation.table_id) if reservation.table_id else None,
            "table_name": table_name,
            "reservation_time": reservation.reservation_time.isoformat(),
            "guest_count": reservation.guest_count,
            "status": reservation.status,
            "notes": reservation.notes,
            "row_version": reservation.row_version,
            "created_at": reservation.created_at.isoformat(),
        },
    }


@router.put("/{reservation_id}/confirm")
async def confirm_reservation(
    reservation_id: UUID,
    body: ConfirmReservationInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Konfirmasi reservasi.
    Jika table_id dikirim → set meja jadi 'reserved' (Golden Rule #24).
    """
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.deleted_at.is_(None),
        ).with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")

    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == reservation.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Akses ditolak")

    if reservation.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Hanya reservasi pending yang bisa dikonfirmasi (saat ini: {reservation.status})",
        )

    table_name = None
    if body.table_id:
        tbl_result = await db.execute(
            select(Table).where(
                Table.id == body.table_id,
                Table.outlet_id == reservation.outlet_id,
                Table.deleted_at.is_(None),
            ).with_for_update()
        )
        table = tbl_result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
        if table.status not in ("available",):
            raise HTTPException(
                status_code=409,
                detail=f"Meja tidak tersedia (status: {table.status}), pilih meja lain",
            )
        if table.capacity < reservation.guest_count:
            raise HTTPException(
                status_code=400,
                detail=f"Kapasitas meja ({table.capacity}) kurang dari jumlah tamu ({reservation.guest_count})",
            )

        # Golden Rule #24: reserve table
        table.status = "reserved"
        table.row_version += 1
        reservation.table_id = body.table_id
        table_name = table.name

    reservation.status = "confirmed"
    reservation.row_version += 1

    await log_audit(
        db=db,
        action="reservation_confirm",
        entity="reservation",
        entity_id=str(reservation_id),
        after_state={"status": "confirmed", "table_id": str(body.table_id) if body.table_id else None},
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "status": "confirmed",
            "table_name": table_name,
            "row_version": reservation.row_version,
        },
    }


@router.put("/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Batalkan reservasi + release meja (Golden Rule #24)."""
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.deleted_at.is_(None),
        ).with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")

    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == reservation.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Akses ditolak")

    if reservation.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail=f"Reservasi sudah {reservation.status}")

    # Golden Rule #24: release table
    if reservation.table_id:
        tbl_result = await db.execute(
            select(Table).where(Table.id == reservation.table_id).with_for_update()
        )
        table = tbl_result.scalar_one_or_none()
        if table and table.status == "reserved":
            table.status = "available"
            table.row_version += 1

    reservation.status = "cancelled"
    reservation.row_version += 1

    await log_audit(
        db=db,
        action="reservation_cancel",
        entity="reservation",
        entity_id=str(reservation_id),
        after_state={"status": "cancelled"},
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )
    await db.commit()

    return {"success": True, "data": {"status": "cancelled"}}


@router.put("/{reservation_id}/complete")
async def complete_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Selesaikan reservasi + release meja (Golden Rule #24 — release saat done)."""
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.deleted_at.is_(None),
        ).with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")

    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == reservation.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Akses ditolak")

    if reservation.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Hanya reservasi confirmed yang bisa diselesaikan",
        )

    # Golden Rule #24: release table saat done
    if reservation.table_id:
        tbl_result = await db.execute(
            select(Table).where(Table.id == reservation.table_id).with_for_update()
        )
        table = tbl_result.scalar_one_or_none()
        if table and table.status == "reserved":
            table.status = "available"
            table.row_version += 1

    reservation.status = "completed"
    reservation.row_version += 1

    await log_audit(
        db=db,
        action="reservation_complete",
        entity="reservation",
        entity_id=str(reservation_id),
        after_state={"status": "completed"},
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )
    await db.commit()

    return {"success": True, "data": {"status": "completed"}}
