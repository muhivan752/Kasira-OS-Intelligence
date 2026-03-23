import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api import deps
from backend.models.tenant import Tenant
from backend.schemas.tenant import Tenant as TenantSchema, TenantCreate, TenantUpdate
from backend.schemas.response import StandardResponse, ResponseMeta
from backend.services.audit import log_audit
import json

router = APIRouter()

@router.get("/", response_model=StandardResponse[List[TenantSchema]])
async def read_tenants(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve tenants.
    """
    stmt = select(Tenant).where(Tenant.deleted_at == None).offset(skip).limit(limit)
    result = await db.execute(stmt)
    tenants = result.scalars().all()
    
    # In a real app, you would count total records
    meta = ResponseMeta(page=(skip // limit) + 1, per_page=limit, total=len(tenants))
    return StandardResponse(data=tenants, meta=meta)

@router.post("/", response_model=StandardResponse[TenantSchema])
async def create_tenant(
    *,
    db: AsyncSession = Depends(deps.get_db),
    tenant_in: TenantCreate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new tenant.
    """
    stmt = select(Tenant).where(Tenant.schema_name == tenant_in.schema_name)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if tenant:
        raise HTTPException(
            status_code=400,
            detail="The tenant with this schema name already exists in the system.",
        )
    
    db_tenant = Tenant(**tenant_in.model_dump())
    db.add(db_tenant)
    await db.flush()
    
    after_state = json.loads(tenant_in.model_dump_json())
    await log_audit(
        db=db,
        action="CREATE",
        entity="tenants",
        entity_id=db_tenant.id,
        after_state=after_state,
        user_id=current_user.id,
        tenant_id=db_tenant.id
    )
    
    await db.commit()
    await db.refresh(db_tenant)
    return StandardResponse(data=db_tenant, message="Tenant created successfully")

@router.get("/{tenant_id}", response_model=StandardResponse[TenantSchema])
async def read_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get tenant by ID.
    """
    stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at == None)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return StandardResponse(data=tenant)
