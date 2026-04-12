"""
Subscription Billing routes — tenant-facing billing info and payment retry.
"""
import uuid
import logging
from typing import Any, Optional, List
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.subscription_invoice import SubscriptionInvoice
from backend.schemas.response import StandardResponse
from backend.services.xendit import xendit_service
from backend.services.audit import log_audit

router = APIRouter()
logger = logging.getLogger(__name__)

TIER_PRICES = {
    "starter": 99_000,
    "pro": 299_000,
    "business": 499_000,
    "enterprise": 0,
}

TIER_LABELS = {
    "starter": "Starter",
    "pro": "Pro",
    "business": "Business",
    "enterprise": "Enterprise",
}


# ── Schemas ──────────────────────────────────────────────

class BillingInfo(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    tier: str
    tier_label: str
    price: int
    subscription_status: Optional[str] = None
    billing_day: int = 1
    next_billing_date: Optional[date] = None
    latest_invoice: Optional[dict] = None

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: uuid.UUID
    tier: str
    amount: int
    billing_period_start: date
    billing_period_end: date
    due_date: date
    status: str
    xendit_invoice_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ── Endpoints ────────────────────────────────────────────

@router.get("/current", response_model=StandardResponse[BillingInfo])
async def get_billing_current(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(deps.get_current_user),
) -> Any:
    """Info billing tenant: plan, next billing, latest invoice."""
    tenant = await _get_user_tenant(db, user)
    tier = _tier_value(tenant)

    # Latest invoice
    stmt = (
        select(SubscriptionInvoice)
        .where(
            SubscriptionInvoice.tenant_id == tenant.id,
            SubscriptionInvoice.deleted_at.is_(None),
        )
        .order_by(desc(SubscriptionInvoice.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    latest = result.scalar_one_or_none()

    latest_dict = None
    if latest:
        latest_dict = {
            "id": str(latest.id),
            "status": latest.status,
            "amount": latest.amount,
            "due_date": latest.due_date.isoformat() if latest.due_date else None,
            "xendit_invoice_url": latest.xendit_invoice_url,
            "paid_at": latest.paid_at.isoformat() if latest.paid_at else None,
        }

    return StandardResponse(
        data=BillingInfo(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tier=tier,
            tier_label=TIER_LABELS.get(tier, tier),
            price=TIER_PRICES.get(tier, 0),
            subscription_status=_status_value(tenant),
            billing_day=tenant.billing_day or 1,
            next_billing_date=tenant.next_billing_date,
            latest_invoice=latest_dict,
        ),
        message="Billing info",
    )


@router.get("/invoices", response_model=StandardResponse[List[InvoiceOut]])
async def get_billing_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(deps.get_current_user),
) -> Any:
    """Riwayat invoice subscription tenant."""
    tenant = await _get_user_tenant(db, user)

    stmt = (
        select(SubscriptionInvoice)
        .where(
            SubscriptionInvoice.tenant_id == tenant.id,
            SubscriptionInvoice.deleted_at.is_(None),
        )
        .order_by(desc(SubscriptionInvoice.created_at))
        .limit(50)
    )
    result = await db.execute(stmt)
    invoices = result.scalars().all()

    return StandardResponse(
        data=[
            InvoiceOut(
                id=inv.id,
                tier=inv.tier,
                amount=inv.amount,
                billing_period_start=inv.billing_period_start,
                billing_period_end=inv.billing_period_end,
                due_date=inv.due_date,
                status=inv.status,
                xendit_invoice_url=inv.xendit_invoice_url,
                paid_at=inv.paid_at,
                created_at=inv.created_at,
                notes=inv.notes,
            )
            for inv in invoices
        ],
        message="Invoice list",
    )


@router.post("/invoices/{invoice_id}/retry", response_model=StandardResponse[dict])
async def retry_invoice_payment(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(deps.get_current_user),
) -> Any:
    """Re-create Xendit invoice untuk invoice yang expired/grace/suspended."""
    tenant = await _get_user_tenant(db, user)

    stmt = select(SubscriptionInvoice).where(
        SubscriptionInvoice.id == invoice_id,
        SubscriptionInvoice.tenant_id == tenant.id,
        SubscriptionInvoice.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice sudah dibayar")

    # Create new Xendit invoice
    external_id = f"sub::{tenant.id}::{invoice.id}"
    tier_label = TIER_LABELS.get(invoice.tier, invoice.tier)

    try:
        xendit_resp = await xendit_service.create_invoice(
            external_id=external_id,
            amount=invoice.amount,
            payer_email=tenant.owner_email or f"{tenant.schema_name}@kasira.online",
            description=f"Langganan Kasira {tier_label} - {invoice.billing_period_start.strftime('%b %Y')}",
        )

        invoice.xendit_invoice_id = xendit_resp.get("id")
        invoice.xendit_invoice_url = xendit_resp.get("invoice_url")
        invoice.status = "pending"
        invoice.row_version += 1

        await log_audit(
            db=db, action="RETRY_INVOICE", entity="subscription_invoices",
            entity_id=invoice.id, after_state={"xendit_invoice_id": invoice.xendit_invoice_id},
            user_id=user.id, tenant_id=tenant.id,
        )
        await db.commit()

        return StandardResponse(
            data={
                "invoice_id": str(invoice.id),
                "xendit_invoice_url": invoice.xendit_invoice_url,
            },
            message="Invoice baru dibuat. Silakan bayar.",
        )

    except Exception as e:
        logger.error(f"Xendit create_invoice failed: {e}")
        raise HTTPException(status_code=502, detail="Gagal membuat invoice Xendit")


# ── Helpers ──────────────────────────────────────────────

async def _get_user_tenant(db: AsyncSession, user: User) -> Tenant:
    stmt = select(Tenant).where(Tenant.id == user.tenant_id, Tenant.deleted_at.is_(None))
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")
    return tenant


def _tier_value(tenant: Tenant) -> str:
    raw = getattr(tenant, "subscription_tier", "starter") or "starter"
    return raw.value if hasattr(raw, "value") else str(raw)


def _status_value(tenant: Tenant) -> str:
    raw = getattr(tenant, "subscription_status", "active") or "active"
    return raw.value if hasattr(raw, "value") else str(raw)
