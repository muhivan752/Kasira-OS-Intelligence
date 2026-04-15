"""
Platform Superadmin routes — tenant management, stats, tier/status changes.
Protected by SUPERADMIN_PHONES env var.
"""
import uuid
import calendar
from typing import Any, Optional
from datetime import datetime, timedelta, timezone, date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text

from backend.api import deps
from backend.models.tenant import Tenant, SubscriptionTier, SubscriptionStatus
from backend.models.user import User
from backend.models.audit_log import AuditLog
from backend.models.subscription_invoice import SubscriptionInvoice
from backend.schemas.response import StandardResponse, ResponseMeta
from backend.services.audit import log_audit
from backend.services.xendit import xendit_service
import json
import logging

sa_logger = logging.getLogger(__name__)


def _add_month(d: date_type) -> date_type:
    """Add 1 month, clamp day."""
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=min(d.day, 31))
    next_m = d.month + 1
    max_day = calendar.monthrange(d.year, next_m)[1]
    return d.replace(month=next_m, day=min(d.day, max_day))

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


# ── Audit Logs ──────────────────────────────────────────

class AuditLogItem(BaseModel):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    entity: str
    entity_id: uuid.UUID
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    request_id: Optional[str] = None
    created_at: datetime
    tenant_name: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/audit-logs", response_model=StandardResponse[list[AuditLogItem]])
async def list_audit_logs(
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
    skip: int = 0,
    limit: int = 50,
    tenant_id: Optional[uuid.UUID] = Query(None),
    entity: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
) -> Any:
    """List audit logs with optional filters."""
    stmt = select(AuditLog)

    if tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if action:
        stmt = stmt.where(AuditLog.action == action)

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    # Count total
    count_stmt = select(func.count(AuditLog.id))
    if tenant_id:
        count_stmt = count_stmt.where(AuditLog.tenant_id == tenant_id)
    if entity:
        count_stmt = count_stmt.where(AuditLog.entity == entity)
    if action:
        count_stmt = count_stmt.where(AuditLog.action == action)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Enrich with tenant/user names
    tenant_cache: dict[uuid.UUID, str] = {}
    user_cache: dict[uuid.UUID, str] = {}

    items = []
    for log in logs:
        t_name = None
        u_name = None

        if log.tenant_id:
            if log.tenant_id not in tenant_cache:
                t = (await db.execute(select(Tenant.name).where(Tenant.id == log.tenant_id))).scalar_one_or_none()
                tenant_cache[log.tenant_id] = t or ""
            t_name = tenant_cache[log.tenant_id] or None

        if log.user_id:
            if log.user_id not in user_cache:
                u = (await db.execute(select(User.full_name).where(User.id == log.user_id))).scalar_one_or_none()
                user_cache[log.user_id] = u or ""
            u_name = user_cache[log.user_id] or None

        items.append(AuditLogItem(
            id=log.id,
            tenant_id=log.tenant_id,
            user_id=log.user_id,
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            before_state=log.before_state,
            after_state=log.after_state,
            request_id=log.request_id,
            created_at=log.created_at,
            tenant_name=t_name,
            user_name=u_name,
        ))

    meta = ResponseMeta(page=(skip // limit) + 1, per_page=limit, total=total)
    return StandardResponse(data=items, meta=meta)


# ── Billing Management ───────────────────────────────────

TIER_PRICES = {
    "starter": 99_000,
    "pro": 299_000,
    "business": 499_000,
    "enterprise": 0,
}

TIER_PRICES_ANNUAL = {
    "starter": 990_000,
    "pro": 2_990_000,
    "business": 4_990_000,
    "enterprise": 0,
}

TIER_LABELS = {
    "starter": "Starter",
    "pro": "Pro",
    "business": "Business",
    "enterprise": "Enterprise",
}


class BillingOverviewItem(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    tier: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: bool
    next_billing_date: Optional[datetime] = None
    last_invoice_status: Optional[str] = None
    last_invoice_amount: Optional[int] = None
    last_paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/billing", response_model=StandardResponse[list[BillingOverviewItem]])
async def billing_overview(
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Overview billing semua tenant."""
    tenants_stmt = select(Tenant).where(Tenant.deleted_at.is_(None)).order_by(Tenant.created_at.desc())
    tenants = (await db.execute(tenants_stmt)).scalars().all()

    items = []
    for t in tenants:
        tier_raw = getattr(t, "subscription_tier", "starter") or "starter"
        tier = tier_raw.value if hasattr(tier_raw, "value") else str(tier_raw)
        status_raw = getattr(t, "subscription_status", "active") or "active"
        sub_status = status_raw.value if hasattr(status_raw, "value") else str(status_raw)

        inv_stmt = (
            select(SubscriptionInvoice)
            .where(SubscriptionInvoice.tenant_id == t.id, SubscriptionInvoice.deleted_at.is_(None))
            .order_by(SubscriptionInvoice.created_at.desc())
            .limit(1)
        )
        inv = (await db.execute(inv_stmt)).scalar_one_or_none()

        items.append(BillingOverviewItem(
            tenant_id=t.id,
            tenant_name=t.name,
            tier=tier,
            subscription_status=sub_status,
            is_active=t.is_active,
            next_billing_date=t.next_billing_date,
            last_invoice_status=inv.status if inv else None,
            last_invoice_amount=inv.amount if inv else None,
            last_paid_at=inv.paid_at if inv else None,
        ))

    return StandardResponse(data=items, message="Billing overview")


@router.get("/billing/{tenant_id}/invoices", response_model=StandardResponse[list])
async def get_tenant_invoices(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """List invoices for a specific tenant."""
    from sqlalchemy import desc
    stmt = (
        select(SubscriptionInvoice)
        .where(SubscriptionInvoice.tenant_id == tenant_id, SubscriptionInvoice.deleted_at.is_(None))
        .order_by(desc(SubscriptionInvoice.created_at))
        .limit(50)
    )
    invoices = (await db.execute(stmt)).scalars().all()
    return StandardResponse(
        data=[
            {
                "id": str(inv.id),
                "tier": inv.tier,
                "amount": inv.amount,
                "billing_period_start": inv.billing_period_start.isoformat() if inv.billing_period_start else None,
                "billing_period_end": inv.billing_period_end.isoformat() if inv.billing_period_end else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "status": inv.status,
                "xendit_invoice_url": inv.xendit_invoice_url,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "notes": inv.notes,
            }
            for inv in invoices
        ],
        message="Tenant invoices",
    )


@router.post("/billing/{tenant_id}/generate", response_model=StandardResponse[dict])
async def generate_invoice(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Generate invoice manual untuk tenant."""
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")

    tier = getattr(tenant, "subscription_tier", "starter") or "starter"
    tier = tier.value if hasattr(tier, "value") else str(tier)
    price = TIER_PRICES.get(tier, 0)

    if price == 0:
        raise HTTPException(status_code=400, detail="Tier enterprise tidak di-billing otomatis")

    today = date_type.today()
    period_start = today.replace(day=1)
    period_end = _add_month(period_start) - timedelta(days=1)

    existing = (await db.execute(
        select(SubscriptionInvoice).where(
            SubscriptionInvoice.tenant_id == tenant.id,
            SubscriptionInvoice.billing_period_start == period_start,
            SubscriptionInvoice.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    if existing:
        return StandardResponse(
            data={"invoice_id": str(existing.id), "status": existing.status},
            message="Invoice untuk periode ini sudah ada",
        )

    invoice = SubscriptionInvoice(
        tenant_id=tenant.id,
        tier=tier,
        amount=price,
        billing_period_start=period_start,
        billing_period_end=period_end,
        due_date=today,
        status="pending",
        notes="Manual generate by admin",
    )
    db.add(invoice)
    await db.flush()

    external_id = f"sub::{tenant.id}::{invoice.id}"
    tier_label = TIER_LABELS.get(tier, tier)
    try:
        xendit_resp = await xendit_service.create_invoice(
            external_id=external_id,
            amount=price,
            payer_email=tenant.owner_email or f"{tenant.schema_name}@kasira.online",
            description=f"Langganan Kasira {tier_label} - {period_start.strftime('%b %Y')}",
        )
        invoice.xendit_invoice_id = xendit_resp.get("id")
        invoice.xendit_invoice_url = xendit_resp.get("invoice_url")
    except Exception as e:
        sa_logger.error(f"Xendit create_invoice failed for tenant {tenant.id}: {e}")
        invoice.notes = f"Manual generate - Xendit failed: {str(e)[:200]}"

    await log_audit(
        db=db, action="GENERATE_INVOICE", entity="subscription_invoices",
        entity_id=invoice.id, after_state={"tier": tier, "amount": price},
        user_id=admin.id, tenant_id=tenant.id,
    )
    await db.commit()

    return StandardResponse(
        data={
            "invoice_id": str(invoice.id),
            "xendit_invoice_url": invoice.xendit_invoice_url,
            "amount": price,
        },
        message="Invoice berhasil dibuat",
    )


@router.post("/billing/{tenant_id}/activate", response_model=StandardResponse[dict])
async def activate_tenant_billing(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    admin: User = Depends(deps.get_platform_admin),
) -> Any:
    """Manual activate: mark latest unpaid invoice as paid, reactivate tenant."""
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")

    inv_stmt = (
        select(SubscriptionInvoice)
        .where(
            SubscriptionInvoice.tenant_id == tenant.id,
            SubscriptionInvoice.status.in_(["pending", "expired", "grace", "suspended"]),
            SubscriptionInvoice.deleted_at.is_(None),
        )
        .order_by(SubscriptionInvoice.created_at.desc())
        .limit(1)
    )
    invoice = (await db.execute(inv_stmt)).scalar_one_or_none()

    if invoice:
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
        invoice.notes = (invoice.notes or "") + " | Manual activate by admin"
        invoice.row_version += 1

    tenant.subscription_status = SubscriptionStatus.active
    tenant.is_active = True
    tenant.row_version += 1

    today = date_type.today()
    billing_day = min(tenant.billing_day or 1, 28)
    next_date = today.replace(day=billing_day)
    if next_date <= today:
        next_date = _add_month(next_date)
    tenant.next_billing_date = next_date

    await log_audit(
        db=db, action="MANUAL_ACTIVATE", entity="tenants",
        entity_id=tenant.id,
        after_state={"subscription_status": "active", "is_active": True},
        user_id=admin.id, tenant_id=tenant.id,
    )
    await db.commit()

    return StandardResponse(
        data={"id": str(tenant.id), "is_active": True, "next_billing_date": str(tenant.next_billing_date)},
        message="Tenant diaktifkan",
    )


# ---------------------------------------------------------------------------
# WhatsApp Broadcast
# ---------------------------------------------------------------------------
class BroadcastRequest(BaseModel):
    message: str
    tenant_ids: Optional[list[str]] = None  # None = all active tenants

@router.post("/broadcast", response_model=StandardResponse[dict])
async def broadcast_whatsapp(
    body: BroadcastRequest,
    admin: User = Depends(deps.get_platform_admin),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Send WhatsApp broadcast to tenant owners."""
    from backend.services.fonnte import send_whatsapp_message

    if body.tenant_ids:
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID
        stmt = (
            select(User.phone, User.full_name, Tenant.name)
            .join(Tenant, Tenant.id == User.tenant_id)
            .where(
                User.is_superuser == True,
                User.is_active == True,
                Tenant.is_active == True,
                Tenant.id.in_([uuid.UUID(t) for t in body.tenant_ids]),
                User.deleted_at == None,
            )
        )
    else:
        stmt = (
            select(User.phone, User.full_name, Tenant.name)
            .join(Tenant, Tenant.id == User.tenant_id)
            .where(
                User.is_superuser == True,
                User.is_active == True,
                Tenant.is_active == True,
                User.deleted_at == None,
            )
        )

    results = (await db.execute(stmt)).all()
    sent = 0
    failed = 0
    for phone, owner_name, tenant_name in results:
        msg = body.message.replace("{owner}", owner_name or "").replace("{tenant}", tenant_name or "")
        ok = await send_whatsapp_message(phone, msg)
        if ok:
            sent += 1
        else:
            failed += 1

    await log_audit(
        db=db, action="WA_BROADCAST", entity="system", entity_id=str(admin.id),
        after_state={"sent": sent, "failed": failed, "total": len(results)},
        user_id=admin.id, tenant_id=admin.tenant_id,
    )
    await db.commit()

    return StandardResponse(
        data={"sent": sent, "failed": failed, "total": len(results)},
        message=f"Broadcast selesai: {sent} terkirim, {failed} gagal",
    )
