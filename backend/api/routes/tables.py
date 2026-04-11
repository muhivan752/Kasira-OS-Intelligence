from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.reservation import Table
from backend.schemas.reservation import TableCreate, TableUpdate, TableResponse
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter()


@router.get("/", response_model=StandardResponse[List[TableResponse]])
async def get_tables(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List semua meja di outlet."""
    result = await db.execute(
        select(Table).where(
            Table.outlet_id == outlet_id,
            Table.deleted_at.is_(None),
        ).order_by(Table.floor_section.nullsfirst(), Table.name)
    )
    tables = result.scalars().all()
    return StandardResponse(
        success=True,
        data=[TableResponse.model_validate(t) for t in tables],
        request_id=request.state.request_id,
    )


@router.post("/", response_model=StandardResponse[TableResponse])
async def create_table(
    request: Request,
    outlet_id: UUID,
    body: TableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Tambah meja baru."""
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.tenant_id == current_user.tenant_id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    table = Table(
        outlet_id=outlet_id,
        name=body.name,
        capacity=body.capacity,
        floor_section=body.floor_section,
        is_active=body.is_active,
    )
    db.add(table)
    await db.commit()
    await db.refresh(table)

    await log_audit(db=db, action="CREATE", entity="table", entity_id=table.id,
                    after_state={"name": body.name, "capacity": body.capacity},
                    user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True, data=TableResponse.model_validate(table),
        request_id=request.state.request_id, message="Meja berhasil ditambahkan",
    )


@router.put("/{table_id}", response_model=StandardResponse[TableResponse])
async def update_table(
    request: Request,
    table_id: UUID,
    body: TableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update meja."""
    table = (await db.execute(
        select(Table).where(Table.id == table_id, Table.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Meja tidak ditemukan")

    # Validate outlet belongs to tenant
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == table.outlet_id, Outlet.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(table, key, value)
    table.row_version += 1

    await db.commit()
    await db.refresh(table)

    await log_audit(db=db, action="UPDATE", entity="table", entity_id=table.id,
                    after_state=update_data, user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True, data=TableResponse.model_validate(table),
        request_id=request.state.request_id, message="Meja berhasil diupdate",
    )


@router.delete("/{table_id}", response_model=StandardResponse)
async def delete_table(
    request: Request,
    table_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Soft delete meja."""
    from datetime import datetime, timezone
    table = (await db.execute(
        select(Table).where(Table.id == table_id, Table.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Meja tidak ditemukan")

    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == table.outlet_id, Outlet.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    table.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    await log_audit(db=db, action="DELETE", entity="table", entity_id=table.id,
                    after_state={"name": table.name}, user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True, request_id=request.state.request_id, message="Meja berhasil dihapus",
    )
