"""
Subscription Billing Tasks
- generate_invoices_loop: tiap 1 jam, generate invoice untuk tenant yang jatuh tempo
- grace_period_loop: tiap 6 jam, enforce grace period + auto-suspend
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, date

import calendar
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.models.tenant import Tenant, SubscriptionStatus
from backend.models.subscription_invoice import SubscriptionInvoice
from backend.services.xendit import xendit_service
from backend.services.fonnte import send_whatsapp_message
from backend.services.audit import log_audit

logger = logging.getLogger(__name__)

GENERATE_INTERVAL = 3600       # 1 jam
GRACE_CHECK_INTERVAL = 21600   # 6 jam
GRACE_PERIOD_DAYS = 3

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

def _add_month(d: date) -> date:
    """Add 1 month to a date, clamping day to month max."""
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=min(d.day, 31))
    next_month = d.month + 1
    max_day = calendar.monthrange(d.year, next_month)[1]
    return d.replace(month=next_month, day=min(d.day, max_day))


TIER_LABELS = {
    "starter": "Starter",
    "pro": "Pro",
    "business": "Business",
    "enterprise": "Enterprise",
}


def _tier_str(tenant: Tenant) -> str:
    raw = getattr(tenant, "subscription_tier", "starter") or "starter"
    return raw.value if hasattr(raw, "value") else str(raw)


def _next_billing(billing_day: int, after_date: date) -> date:
    """Calculate next billing date after given date."""
    day = min(billing_day, 28)
    candidate = after_date.replace(day=day)
    if candidate <= after_date:
        candidate = _add_month(candidate)
    return candidate


async def _get_owner_phone(db: AsyncSession, tenant_id) -> str | None:
    """Get tenant owner's phone number."""
    from backend.models.user import User
    stmt = select(User.phone).where(
        User.tenant_id == tenant_id,
        User.is_superuser == True,
        User.deleted_at.is_(None),
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def generate_invoices():
    """Generate subscription invoices untuk tenant yang jatuh tempo."""
    try:
        async with AsyncSessionLocal() as db:
            today = date.today()

            # Cari tenant yang perlu di-billing
            stmt = select(Tenant).where(
                Tenant.next_billing_date <= today,
                Tenant.subscription_status.in_([
                    SubscriptionStatus.active,
                    SubscriptionStatus.trial,
                ]),
                Tenant.is_active == True,
                Tenant.deleted_at.is_(None),
            )
            result = await db.execute(stmt)
            tenants = result.scalars().all()

            if not tenants:
                return 0

            generated = 0
            for tenant in tenants:
                tier = _tier_str(tenant)
                interval = getattr(tenant, "billing_interval", "monthly") or "monthly"
                if hasattr(interval, "value"):
                    interval = interval.value

                if str(interval) == "annual":
                    price = TIER_PRICES_ANNUAL.get(tier, 0)
                else:
                    price = TIER_PRICES.get(tier, 0)

                # Skip enterprise (custom billing)
                if price == 0:
                    continue

                billing_day = min(tenant.billing_day or 1, 28)
                period_start = today.replace(day=1)
                if str(interval) == "annual":
                    period_end = period_start.replace(year=period_start.year + 1) - timedelta(days=1)
                else:
                    period_end = _add_month(period_start) - timedelta(days=1)

                # Idempotency: skip if invoice exists
                existing = (await db.execute(
                    select(SubscriptionInvoice.id).where(
                        SubscriptionInvoice.tenant_id == tenant.id,
                        SubscriptionInvoice.billing_period_start == period_start,
                        SubscriptionInvoice.deleted_at.is_(None),
                    )
                )).scalar_one_or_none()

                if existing:
                    # Still update next_billing_date so we don't re-check
                    tenant.next_billing_date = _next_billing(billing_day, today)
                    await db.commit()
                    continue

                # Create invoice
                invoice = SubscriptionInvoice(
                    tenant_id=tenant.id,
                    tier=tier,
                    amount=price,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                    due_date=today,
                    status="pending",
                )
                db.add(invoice)
                await db.flush()

                # Create Xendit invoice
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
                    logger.error(f"Xendit invoice failed for tenant {tenant.id}: {e}")
                    invoice.notes = f"Xendit failed: {str(e)[:200]}"

                # Update next billing date
                if str(interval) == "annual":
                    tenant.next_billing_date = today.replace(year=today.year + 1)
                else:
                    tenant.next_billing_date = _next_billing(billing_day, today)
                tenant.row_version += 1

                await log_audit(
                    db=db, action="AUTO_GENERATE_INVOICE", entity="subscription_invoices",
                    entity_id=invoice.id,
                    after_state={"tier": tier, "amount": price, "tenant": tenant.name},
                    user_id=None, tenant_id=tenant.id,
                )
                await db.commit()
                generated += 1

                # Send WhatsApp notification
                if invoice.xendit_invoice_url:
                    owner_phone = await _get_owner_phone(db, tenant.id)
                    if owner_phone:
                        price_k = f"{price // 1000}rb"
                        msg = (
                            f"📋 *Invoice Kasira*\n\n"
                            f"Halo! Invoice langganan Kasira {tier_label} ({price_k}/bulan) "
                            f"untuk periode {period_start.strftime('%B %Y')} sudah tersedia.\n\n"
                            f"💳 Bayar di sini:\n{invoice.xendit_invoice_url}\n\n"
                            f"Terima kasih! 🙏"
                        )
                        try:
                            await send_whatsapp_message(owner_phone, msg)
                        except Exception as e:
                            logger.error(f"WA send failed for {owner_phone}: {e}")

                # Small delay between tenants to avoid rate limits
                await asyncio.sleep(1)

            if generated:
                logger.info(f"Subscription billing: generated {generated} invoices")
            return generated

    except Exception as e:
        logger.error(f"Generate invoices error: {e}", exc_info=True)
        return 0


async def enforce_grace_period():
    """Check unpaid invoices: mark grace after due, suspend after grace period."""
    try:
        async with AsyncSessionLocal() as db:
            today = date.today()
            grace_cutoff = today - timedelta(days=GRACE_PERIOD_DAYS)

            # 1. Pending invoices past due date but within grace → mark grace
            grace_stmt = select(SubscriptionInvoice).where(
                SubscriptionInvoice.status == "pending",
                SubscriptionInvoice.due_date < today,
                SubscriptionInvoice.due_date >= grace_cutoff,
                SubscriptionInvoice.deleted_at.is_(None),
            )
            grace_invoices = (await db.execute(grace_stmt)).scalars().all()

            for inv in grace_invoices:
                inv.status = "grace"
                inv.row_version += 1

                # Send reminder
                owner_phone = await _get_owner_phone(db, inv.tenant_id)
                if owner_phone and inv.xendit_invoice_url:
                    msg = (
                        f"⚠️ *Pengingat Pembayaran Kasira*\n\n"
                        f"Invoice langganan Anda sudah jatuh tempo. "
                        f"Silakan bayar dalam {GRACE_PERIOD_DAYS} hari untuk menghindari penangguhan.\n\n"
                        f"💳 Bayar: {inv.xendit_invoice_url}"
                    )
                    try:
                        await send_whatsapp_message(owner_phone, msg)
                    except Exception:
                        pass

            if grace_invoices:
                await db.commit()
                logger.info(f"Grace period: marked {len(grace_invoices)} invoices as grace")

            # 2. Grace/pending invoices past grace period → suspend
            suspend_stmt = select(SubscriptionInvoice).where(
                SubscriptionInvoice.status.in_(["pending", "grace"]),
                SubscriptionInvoice.due_date < grace_cutoff,
                SubscriptionInvoice.deleted_at.is_(None),
            )
            suspend_invoices = (await db.execute(suspend_stmt)).scalars().all()

            for inv in suspend_invoices:
                inv.status = "suspended"
                inv.row_version += 1

                # Suspend tenant
                tenant = (await db.execute(
                    select(Tenant).where(Tenant.id == inv.tenant_id)
                )).scalar_one_or_none()

                if tenant and tenant.is_active:
                    tenant.subscription_status = SubscriptionStatus.suspended
                    tenant.is_active = False
                    tenant.row_version += 1

                    await log_audit(
                        db=db, action="AUTO_SUSPEND", entity="tenants",
                        entity_id=tenant.id,
                        after_state={"reason": "unpaid_invoice", "invoice_id": str(inv.id)},
                        user_id=None, tenant_id=tenant.id,
                    )

                    # Invalidate tenant cache — suspended tenant TIDAK BOLEH lolos
                    # gate pake cached snapshot stale. Fix CRITICAL #15.
                    try:
                        from backend.services.subscription import invalidate_tenant_cache
                        from backend.services.redis import get_redis_client
                        redis = await get_redis_client()
                        await invalidate_tenant_cache(redis, tenant.id)
                    except Exception as e:
                        # Log tapi jangan fail task — TTL 30s akan clean up auto
                        logger.warning(
                            "auto-suspend cache invalidate failed tenant=%s: %s "
                            "(next read stale until TTL)",
                            tenant.id, e,
                        )

                    # Notify via WA
                    owner_phone = await _get_owner_phone(db, inv.tenant_id)
                    if owner_phone:
                        msg = (
                            f"🚫 *Langganan Kasira Ditangguhkan*\n\n"
                            f"Akun bisnis Anda telah ditangguhkan karena pembayaran belum diterima.\n\n"
                            f"Untuk mengaktifkan kembali, silakan hubungi tim Kasira "
                            f"atau bayar invoice terakhir Anda."
                        )
                        try:
                            await send_whatsapp_message(owner_phone, msg)
                        except Exception:
                            pass

            if suspend_invoices:
                await db.commit()
                logger.info(f"Grace period: suspended {len(suspend_invoices)} tenants")

            return len(grace_invoices) + len(suspend_invoices)

    except Exception as e:
        logger.error(f"Grace period enforcement error: {e}", exc_info=True)
        return 0


async def generate_invoices_loop():
    """Background loop — generate invoices tiap 1 jam."""
    logger.info("Subscription billing loop started (interval: %ds)", GENERATE_INTERVAL)
    while True:
        await asyncio.sleep(GENERATE_INTERVAL)
        try:
            await generate_invoices()
        except Exception as e:
            logger.error(f"Invoice generation loop error: {e}")


async def grace_period_loop():
    """Background loop — enforce grace period tiap 6 jam."""
    logger.info("Grace period enforcement loop started (interval: %ds)", GRACE_CHECK_INTERVAL)
    while True:
        await asyncio.sleep(GRACE_CHECK_INTERVAL)
        try:
            await enforce_grace_period()
        except Exception as e:
            logger.error(f"Grace period loop error: {e}")
