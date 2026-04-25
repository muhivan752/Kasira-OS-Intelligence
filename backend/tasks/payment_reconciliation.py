"""
Payment Reconciliation — Golden Rule #38
Periodic task: cek pending QRIS payments → poll Xendit + auto-update status.
Non-QRIS pending stale → auto-expire.

Dijalankan sebagai asyncio background task di FastAPI lifespan,
bukan Celery — cukup untuk Starter (<500 outlet).

Scope coverage (FIX #3 dari security audit):
  1. Payment.status == 'pending_manual_check' (any method, hampir selalu QRIS)
     → poll Xendit untuk dapat status final
  2. Payment.status == 'pending' AND created_at < NOW() - 10 min
     → kalau QRIS, poll Xendit dulu sebelum expire (cegah false-expire saat
        webhook telat / hilang). Kalau non-QRIS, langsung expire (legacy).

Catatan side-effect:
  Kalau Xendit konfirmasi PAID untuk pending stale, hanya `payment.status`
  yang di-update jadi 'paid' + paid_at. **Order settlement (table release,
  tab recalc, dst) TIDAK otomatis di-trigger** — itu surface area kompleks
  yang owned by webhook handler atau admin manual. Log WARNING dipasang
  supaya admin aware perlu verify order.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.models.payment import Payment
from backend.models.outlet import Outlet
from backend.services.audit import log_audit

logger = logging.getLogger(__name__)

RECONCILE_INTERVAL = 300  # 5 menit
PENDING_TIMEOUT = timedelta(minutes=10)
QRIS_EXPIRY = timedelta(minutes=15)


async def _reconcile_qris_payment(
    db: AsyncSession,
    payment: Payment,
    now: datetime,
    stats: dict,
) -> None:
    """
    Reconcile satu QRIS payment via Xendit poll.
    Mutate payment in-place; caller commit. Tidak raise — error di-log.
    """
    # Lazy import — hindari circular + setup overhead saat task gak punya QRIS
    from backend.services.xendit import (
        xendit_service,
        XenditTransientError,
        XenditPermanentError,
    )

    xendit_raw = payment.xendit_raw or {}
    qr_code_id = xendit_raw.get("id") if isinstance(xendit_raw, dict) else None

    if not qr_code_id:
        # Tidak ada qr_code_id → biasanya transient error saat create.
        # `pending_manual_check`: leave untuk admin (manual via Xendit dashboard).
        # `pending` stale: expire (gak bisa di-poll, treat as failed flow).
        if payment.status == "pending":
            payment.status = "expired"
            payment.row_version += 1
            payment.reconciled_at = now
            await log_audit(
                db=db,
                action="RECONCILE_PAYMENT_EXPIRED",
                entity="payment",
                entity_id=str(payment.id),
                after_state={
                    "reason": "QRIS pending stale tanpa qr_code_id (gagal poll)",
                    "payment_method": "qris",
                    "amount_due": float(payment.amount_due),
                },
                user_id=None,
                tenant_id=None,
            )
            stats["expired"] += 1
            logger.warning(
                "reconcile: QRIS payment %s no qr_code_id → expire (stale, no poll possible)",
                payment.id,
            )
        else:
            stats["skipped"] += 1
            logger.warning(
                "reconcile: payment %s pending_manual_check but no qr_code_id; "
                "needs manual Xendit dashboard check by admin",
                payment.id,
            )
        return

    # Lookup outlet untuk sub-account API (xendit_business_id)
    outlet = await db.get(Outlet, payment.outlet_id)
    for_user_id = getattr(outlet, "xendit_business_id", None) if outlet else None

    try:
        xres = await xendit_service.get_qr_code_status(
            qr_code_id=qr_code_id,
            for_user_id=for_user_id,
        )
    except (XenditTransientError, XenditPermanentError) as e:
        # Xendit error — leave state unchanged, retry next cycle.
        stats["skipped"] += 1
        logger.warning(
            "reconcile: Xendit poll failed payment=%s qr=%s: %s — retry next cycle",
            payment.id, qr_code_id, e,
        )
        return
    except Exception as e:
        stats["skipped"] += 1
        logger.warning(
            "reconcile: unexpected error polling Xendit payment=%s: %s",
            payment.id, e,
        )
        return

    xstatus = str(xres.get("status") or "").upper()
    logger.info(
        "reconcile: payment=%s qr=%s xendit_status=%s prev=%s",
        payment.id, qr_code_id, xstatus, payment.status,
    )

    if xstatus in ("SUCCEEDED", "PAID"):
        # Xendit konfirmasi paid — webhook missed/late. Update payment status.
        # Order settlement TIDAK auto-trigger (bukan scope reconciliation).
        payment.status = "paid"
        payment.paid_at = now
        payment.row_version += 1
        payment.reconciled_at = now
        merged_raw = dict(xendit_raw)
        merged_raw["reconciled_status"] = xres
        payment.xendit_raw = merged_raw
        await log_audit(
            db=db,
            action="RECONCILE_PAYMENT_PAID",
            entity="payment",
            entity_id=str(payment.id),
            after_state={
                "reason": "Xendit poll confirmed PAID — webhook missed/late",
                "payment_method": "qris",
                "amount_due": float(payment.amount_due),
                "xendit_status": xstatus,
                "note": "Order settlement (table release, tab recalc) needs admin verification",
            },
            user_id=None,
            tenant_id=outlet.tenant_id if outlet else None,
        )
        stats["paid"] += 1
        logger.warning(
            "reconcile: payment %s → PAID via Xendit poll. "
            "ORDER SETTLEMENT may need manual admin verification "
            "(table release, tab recalc, receipt notification).",
            payment.id,
        )
    elif xstatus in ("EXPIRED", "INACTIVE"):
        payment.status = "expired"
        payment.row_version += 1
        payment.reconciled_at = now
        await log_audit(
            db=db,
            action="RECONCILE_PAYMENT_EXPIRED",
            entity="payment",
            entity_id=str(payment.id),
            after_state={
                "reason": "Xendit confirmed EXPIRED",
                "payment_method": "qris",
                "amount_due": float(payment.amount_due),
                "xendit_status": xstatus,
            },
            user_id=None,
            tenant_id=outlet.tenant_id if outlet else None,
        )
        stats["expired"] += 1
        logger.info("reconcile: payment %s → expired (Xendit confirmed)", payment.id)
    elif xstatus == "FAILED":
        payment.status = "failed"
        payment.row_version += 1
        payment.reconciled_at = now
        await log_audit(
            db=db,
            action="RECONCILE_PAYMENT_FAILED",
            entity="payment",
            entity_id=str(payment.id),
            after_state={
                "reason": "Xendit confirmed FAILED",
                "payment_method": "qris",
                "amount_due": float(payment.amount_due),
                "xendit_status": xstatus,
            },
            user_id=None,
            tenant_id=outlet.tenant_id if outlet else None,
        )
        stats["failed"] += 1
        logger.info("reconcile: payment %s → failed (Xendit confirmed)", payment.id)
    elif xstatus in ("ACTIVE", "PENDING"):
        # Customer belum bayar / Xendit masih menunggu. Skip — biarkan stale
        # threshold next cycle decide. Jangan expire kalau Xendit masih ACTIVE
        # (mungkin customer baru aja scan QR, race window).
        stats["skipped"] += 1
        logger.info(
            "reconcile: payment %s still %s in Xendit, retry next cycle",
            payment.id, xstatus,
        )
    else:
        stats["skipped"] += 1
        logger.warning(
            "reconcile: payment %s unknown Xendit status '%s', skip",
            payment.id, xstatus,
        )


async def reconcile_payments():
    """
    Main reconciliation loop body. Run setiap RECONCILE_INTERVAL detik.

    Returns dict stats: {total, paid, expired, failed, skipped}
    (atau dict dengan 'error' key kalau exception di outer scope).
    """
    try:
        async with AsyncSessionLocal() as db:
            # RLS bypass — background task lintas tenant. Pattern sama dengan
            # stale_order_cleanup.py:57. Tanpa ini, RLS policy `payments`
            # block query (current_setting unset = NULL ≠ '').
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

            now = datetime.now(timezone.utc)
            cutoff = now - PENDING_TIMEOUT

            # Query: pending_manual_check (selalu poll) + pending stale
            stmt = select(Payment).where(
                Payment.deleted_at.is_(None),
                or_(
                    Payment.status == "pending_manual_check",
                    and_(
                        Payment.status == "pending",
                        Payment.created_at < cutoff,
                    ),
                ),
            )
            result = await db.execute(stmt)
            candidates = result.scalars().all()

            stats = {
                "total": len(candidates),
                "paid": 0,
                "expired": 0,
                "failed": 0,
                "skipped": 0,
            }

            if not candidates:
                return stats

            logger.info(
                "Payment reconciliation cycle: %d candidates to check",
                stats["total"],
            )

            for payment in candidates:
                # Branch: QRIS payment → poll Xendit
                if payment.payment_method == "qris":
                    await _reconcile_qris_payment(db, payment, now, stats)
                else:
                    # Non-QRIS pending stale → legacy auto-expire (cash/transfer
                    # rarely stuck pending; biasanya cash settle immediate).
                    # `pending_manual_check` non-QRIS shouldn't exist tapi
                    # defensive: skip (admin manual).
                    if payment.status == "pending":
                        payment.status = "expired"
                        payment.row_version += 1
                        payment.reconciled_at = now
                        await log_audit(
                            db=db,
                            action="RECONCILE_PAYMENT_EXPIRED",
                            entity="payment",
                            entity_id=str(payment.id),
                            after_state={
                                "reason": "Non-QRIS pending > 10 minutes",
                                "payment_method": payment.payment_method,
                                "amount_due": float(payment.amount_due),
                            },
                            user_id=None,
                            tenant_id=None,
                        )
                        stats["expired"] += 1
                        logger.info(
                            "reconcile: non-QRIS payment %s (%s) → expired (stale)",
                            payment.id, payment.payment_method,
                        )
                    else:
                        stats["skipped"] += 1
                        logger.warning(
                            "reconcile: non-QRIS payment %s in status %s, skip "
                            "(admin manual review)",
                            payment.id, payment.status,
                        )

            await db.commit()

            if any(stats[k] > 0 for k in ("paid", "expired", "failed")):
                logger.info(
                    "Payment reconciliation done: total=%d paid=%d expired=%d failed=%d skipped=%d",
                    stats["total"], stats["paid"], stats["expired"],
                    stats["failed"], stats["skipped"],
                )
            return stats

    except Exception as e:
        logger.error("Payment reconciliation error: %s", e, exc_info=True)
        return {"total": 0, "paid": 0, "expired": 0, "failed": 0, "skipped": 0, "error": str(e)}


async def payment_reconciliation_loop():
    """Background loop — jalan setiap 5 menit."""
    logger.info("Payment reconciliation task started (interval: %ds)", RECONCILE_INTERVAL)
    while True:
        await asyncio.sleep(RECONCILE_INTERVAL)
        try:
            stats = await reconcile_payments()
            if stats.get("total", 0) > 0:
                logger.info(
                    "Reconciled cycle: %s",
                    {k: v for k, v in stats.items() if k != "total" or v > 0},
                )
        except Exception as e:
            logger.error("Reconciliation loop error: %s", e, exc_info=True)
