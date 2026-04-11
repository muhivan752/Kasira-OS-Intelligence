"""
Platform Superadmin routes — tenant management, stats, tier/status changes.
Protected by SUPERADMIN_PHONES env var.
"""
import uuid
from typing import Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text

from backend.api import deps
from backend.models.tenant import Tenant, SubscriptionTier, SubscriptionStatus
from backend.models.user import User
from backend.schemas.response import StandardResponse, ResponseMeta
from backend.services.audit import log_audit
import json

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────

class TenantOverview(BaseModel):
    id: uuid.UUID
    name: str
    schema_name: str
    is_active: bool
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: datetime
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    user_count: int = 0
    outlet_count: int = 0

    class Config:
        from_attributes = True


class PlatformStats(BaseModel):
    total_tenants: int = 0
    active_tenants: int = 0
    starter_count: int = 0
    pro_count: int = 0
    business_count: int = 0
    total_users: int = 0
    new_tenants_7d: int = 0
    new_tenants_30d: int = 0


class TierUpdate(BaseModel):
    tier: str  # starter, pro, business, enterprise


class StatusUpdate(BaseModel):
    is_active: bool
    subscription_status: Optional[str] = None  # active, suspended, cancelled


class TenantDetail(BaseModel):
    id: uuid.UUID
    name: str
    schema_name: str
    is_active: bool
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    users: list = []
    outlets: list = []
    order_count: int = 0
    revenue_total: float = 0

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────

@router.get("/stats", response_model=StandardResponse[PlatformStats])
async def platform_stats(
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Platform-wide statistics."""
    now = datetime.utcnow()
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    # Tenant counts
    stmt = select(
        func.count(Tenant.id).label("total"),
        func.count(case((Tenant.is_active == True, 1))).label("active"),
        func.count(case((Tenant.subscription_tier == SubscriptionTier.starter, 1))).label("starter"),
        func.count(case((Tenant.subscription_tier == SubscriptionTier.pro, 1))).label("pro"),
        func.count(case((Tenant.subscription_tier == SubscriptionTier.business, 1))).label("business"),
        func.count(case((Tenant.created_at >= d7, 1))).label("new_7d"),
        func.count(case((Tenant.created_at >= d30, 1))).label("new_30d"),
    ).where(Tenant.deleted_at == None)
    result = await db.execute(stmt)
    row = result.one()

    # Total users
    user_count_stmt = select(func.count(User.id)).where(User.deleted_at == None)
    user_result = await db.execute(user_count_stmt)
    total_users = user_result.scalar() or 0

    stats = PlatformStats(
        total_tenants=row.total,
        active_tenants=row.active,
        starter_count=row.starter,
        pro_count=row.pro,
        business_count=row.business,
        total_users=total_users,
        new_tenants_7d=row.new_7d,
        new_tenants_30d=row.new_30d,
    )
    return StandardResponse(data=stats)


@router.get("/tenants", response_model=StandardResponse[list[TenantOverview]])
async def list_tenants(
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
    skip: int = 0,
    limit: int = 50,
    tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Any:
    """List all tenants with owner info and counts."""
    from backend.models.outlet import Outlet

    # Base query
    stmt = select(Tenant).where(Tenant.deleted_at == None)

    if tier:
        stmt = stmt.where(Tenant.subscription_tier == tier)
    if search:
        stmt = stmt.where(Tenant.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    # Count total
    count_stmt = select(func.count(Tenant.id)).where(Tenant.deleted_at == None)
    if tier:
        count_stmt = count_stmt.where(Tenant.subscription_tier == tier)
    if search:
        count_stmt = count_stmt.where(Tenant.name.ilike(f"%{search}%"))
    total = (await db.execute(count_stmt)).scalar() or 0

    # Enrich with owner + counts
    items = []
    for t in tenants:
        # Owner (first superuser for this tenant)
        owner_stmt = select(User).where(
            User.tenant_id == t.id, User.is_superuser == True, User.deleted_at == None
        ).limit(1)
        owner = (await db.execute(owner_stmt)).scalar_one_or_none()

        # User count
        uc = (await db.execute(
            select(func.count(User.id)).where(User.tenant_id == t.id, User.deleted_at == None)
        )).scalar() or 0

        # Outlet count
        oc = (await db.execute(
            select(func.count(Outlet.id)).where(Outlet.tenant_id == t.id, Outlet.deleted_at == None)
        )).scalar() or 0

        tier_val = t.subscription_tier.value if hasattr(t.subscription_tier, 'value') else str(t.subscription_tier or 'starter')
        status_val = t.subscription_status.value if hasattr(t.subscription_status, 'value') else str(t.subscription_status or '')

        items.append(TenantOverview(
            id=t.id,
            name=t.name,
            schema_name=t.schema_name,
            is_active=t.is_active,
            subscription_tier=tier_val,
            subscription_status=status_val,
            created_at=t.created_at,
            owner_name=owner.full_name if owner else None,
            owner_phone=owner.phone if owner else None,
            user_count=uc,
            outlet_count=oc,
        ))

    meta = ResponseMeta(page=(skip // limit) + 1, per_page=limit, total=total)
    return StandardResponse(data=items, meta=meta)


@router.get("/tenants/{tenant_id}", response_model=StandardResponse[TenantDetail])
async def tenant_detail(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Detailed view of a single tenant with users, outlets, and usage."""
    from backend.models.outlet import Outlet

    stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at == None)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")

    # Owner
    owner_stmt = select(User).where(
        User.tenant_id == tenant.id, User.is_superuser == True, User.deleted_at == None
    ).limit(1)
    owner = (await db.execute(owner_stmt)).scalar_one_or_none()

    # Users
    users_stmt = select(User).where(User.tenant_id == tenant.id, User.deleted_at == None)
    users = (await db.execute(users_stmt)).scalars().all()
    user_list = [{"id": str(u.id), "name": u.full_name, "phone": u.phone, "is_active": u.is_active, "is_superuser": u.is_superuser} for u in users]

    # Outlets
    outlets_stmt = select(Outlet).where(Outlet.tenant_id == tenant.id, Outlet.deleted_at == None)
    outlets = (await db.execute(outlets_stmt)).scalars().all()
    outlet_list = [{"id": str(o.id), "name": o.name} for o in outlets]

    # Order count & revenue from tenant schema
    order_count = 0
    revenue_total = 0.0
    try:
        schema = tenant.schema_name
        order_q = await db.execute(text(
            f'SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM "{schema}".orders WHERE deleted_at IS NULL'
        ))
        row = order_q.one()
        order_count = row[0] or 0
        revenue_total = float(row[1] or 0)
    except Exception:
        pass

    tier_val = tenant.subscription_tier.value if hasattr(tenant.subscription_tier, 'value') else str(tenant.subscription_tier or 'starter')
    status_val = tenant.subscription_status.value if hasattr(tenant.subscription_status, 'value') else str(tenant.subscription_status or '')

    detail = TenantDetail(
        id=tenant.id,
        name=tenant.name,
        schema_name=tenant.schema_name,
        is_active=tenant.is_active,
        subscription_tier=tier_val,
        subscription_status=status_val,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        owner_name=owner.full_name if owner else None,
        owner_phone=owner.phone if owner else None,
        users=user_list,
        outlets=outlet_list,
        order_count=order_count,
        revenue_total=revenue_total,
    )
    return StandardResponse(data=detail)


@router.put("/tenants/{tenant_id}/tier", response_model=StandardResponse[dict])
async def update_tier(
    tenant_id: uuid.UUID,
    payload: TierUpdate,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Upgrade or downgrade a tenant's subscription tier."""
    valid_tiers = {"starter", "pro", "business", "enterprise"}
    if payload.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Tier harus salah satu dari: {', '.join(valid_tiers)}")

    stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at == None)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")

    old_tier = tenant.subscription_tier.value if hasattr(tenant.subscription_tier, 'value') else str(tenant.subscription_tier)
    tenant.subscription_tier = payload.tier
    tenant.row_version += 1

    await log_audit(
        db=db, action="UPDATE_TIER", entity="tenants", entity_id=tenant.id,
        before_state={"tier": old_tier},
        after_state={"tier": payload.tier},
        user_id=admin.id, tenant_id=tenant.id,
    )
    await db.commit()
    return StandardResponse(data={"id": str(tenant.id), "tier": payload.tier}, message=f"Tier diubah ke {payload.tier}")


@router.put("/tenants/{tenant_id}/status", response_model=StandardResponse[dict])
async def update_status(
    tenant_id: uuid.UUID,
    payload: StatusUpdate,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Activate or suspend a tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at == None)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")

    tenant.is_active = payload.is_active
    if payload.subscription_status:
        tenant.subscription_status = payload.subscription_status
    tenant.row_version += 1

    await log_audit(
        db=db, action="UPDATE_STATUS", entity="tenants", entity_id=tenant.id,
        after_state={"is_active": payload.is_active, "subscription_status": payload.subscription_status},
        user_id=admin.id, tenant_id=tenant.id,
    )
    await db.commit()

    status_label = "diaktifkan" if payload.is_active else "dinonaktifkan"
    return StandardResponse(
        data={"id": str(tenant.id), "is_active": payload.is_active},
        message=f"Tenant {status_label}",
    )
