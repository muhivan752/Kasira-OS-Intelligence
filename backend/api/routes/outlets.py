import uuid
from typing import Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.api import deps
from backend.models.outlet import Outlet
from backend.schemas.outlet import Outlet as OutletSchema, OutletCreate, OutletUpdate, OutletPaymentSetup, OutletPaymentStatus
from backend.schemas.response import StandardResponse, ResponseMeta
from backend.services.audit import log_audit
from backend.services.audit import log_audit
import json

router = APIRouter()

@router.get("/", response_model=StandardResponse[List[OutletSchema]])
async def read_outlets(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve outlets.
    """
    stmt = select(Outlet).where(Outlet.deleted_at == None).offset(skip).limit(limit)
    if not current_user.is_superuser:
        stmt = stmt.where(Outlet.tenant_id == current_user.tenant_id)
        
    result = await db.execute(stmt)
    outlets = result.scalars().all()
    
    meta = ResponseMeta(page=(skip // limit) + 1, per_page=limit, total=len(outlets))
    return StandardResponse(data=outlets, meta=meta)

@router.post("/", response_model=StandardResponse[OutletSchema])
async def create_outlet(
    *,
    db: AsyncSession = Depends(deps.get_db),
    outlet_in: OutletCreate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new outlet.
    """
    db_outlet = Outlet(**outlet_in.model_dump())
    db.add(db_outlet)
    await db.flush()
    
    after_state = json.loads(outlet_in.model_dump_json())
    await log_audit(
        db=db,
        action="CREATE",
        entity="outlets",
        entity_id=db_outlet.id,
        after_state=after_state,
        user_id=current_user.id,
        tenant_id=db_outlet.tenant_id
    )
    
    await db.commit()
    await db.refresh(db_outlet)
    return StandardResponse(data=db_outlet, message="Outlet created successfully")

@router.get("/{outlet_id}", response_model=StandardResponse[OutletSchema])
async def read_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Get outlet by ID.
    """
    stmt = select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at == None)
    if not current_user.is_superuser:
        stmt = stmt.where(Outlet.tenant_id == current_user.tenant_id)
        
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    return StandardResponse(data=outlet)

@router.post("/{outlet_id}/payment-setup", response_model=StandardResponse[OutletPaymentStatus])
async def setup_payment(
    request: Request,
    outlet_id: uuid.UUID,
    setup_in: OutletPaymentSetup,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Setup payment gateway for an outlet.
    """
    stmt = select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at == None)
    if not current_user.is_superuser:
        stmt = stmt.where(Outlet.tenant_id == current_user.tenant_id)
        
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()
    
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
        
    now = datetime.now(timezone.utc)
    
    update_stmt = (
        update(Outlet)
        .where(Outlet.id == outlet_id)
        .values(
            xendit_business_id=setup_in.xendit_business_id,
            xendit_connected_at=now,
            row_version=Outlet.row_version + 1
        )
    )
    await db.execute(update_stmt)

    # Golden Rule #2: Setiap WRITE endpoint WAJIB tulis audit log
    await log_audit(
        db=db,
        action="UPDATE",
        entity="outlets",
        entity_id=outlet_id,
        after_state={"xendit_business_id": setup_in.xendit_business_id, "xendit_connected_at": now.isoformat()},
        user_id=current_user.id,
        tenant_id=outlet.tenant_id,
        request_id=getattr(request.state, "request_id", None)
    )

    await db.commit()
    
    status_data = OutletPaymentStatus(
        is_connected=True,
        xendit_business_id=setup_in.xendit_business_id,
        connected_at=now
    )
    
    return StandardResponse(
        success=True,
        data=status_data,
        request_id=request.state.request_id,
        message="Payment gateway berhasil dikonfigurasi"
    )

@router.get("/{outlet_id}/payment-status", response_model=StandardResponse[OutletPaymentStatus])
async def get_payment_status(
    request: Request,
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Get payment gateway status for an outlet.
    """
    stmt = select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at == None)
    if not current_user.is_superuser:
        stmt = stmt.where(Outlet.tenant_id == current_user.tenant_id)
        
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()
    
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
        
    is_connected = outlet.xendit_business_id is not None
    
    status_data = OutletPaymentStatus(
        is_connected=is_connected,
        xendit_business_id=outlet.xendit_business_id,
        connected_at=outlet.xendit_connected_at
    )
    
    return StandardResponse(
        success=True,
        data=status_data,
        request_id=request.state.request_id
    )
