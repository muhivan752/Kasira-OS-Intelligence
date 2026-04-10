"""
Payment Reconciliation — Golden Rule #38
Periodic task: cek pending payments >10 menit → auto-expire.
QRIS expired_at = created_at + 15 menit (Rule #41).

Dijalankan sebagai asyncio background task di FastAPI lifespan,
bukan Celery — cukup untuk Starter (<500 outlet).
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.models.payment import Payment
from backend.services.audit import log_audit

logger = logging.getLogger(__name__)

RECONCILE_INTERVAL = 300  # 5 menit
PENDING_TIMEOUT = timedelta(minutes=10)
QRIS_EXPIRY = timedelta(minutes=15)


async def reconcile_payments():
    """Auto-expire pending payments yang sudah lewat timeout."""
    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            cutoff = now - PENDING_TIMEOUT

            # Cari pending payments yang sudah >10 menit
            stmt = select(Payment).where(
                Payment.status == "pending",
                Payment.created_at < cutoff,
                Payment.deleted_at.is_(None),
            )
            result = await db.execute(stmt)
            stale_payments = result.scalars().all()

            if not stale_payments:
                return 0

            expired_count = 0
            for payment in stale_payments:
                payment.status = "expired"
                payment.row_version += 1
                expired_count += 1

                # Audit log
                await log_audit(
                    db=db,
                    action="AUTO_EXPIRE_PAYMENT",
                    entity="payment",
                    entity_id=str(payment.id),
                    after_state={
                        "reason": "pending > 10 minutes",
                        "payment_method": payment.payment_method,
                        "amount_due": float(payment.amount_due),
                    },
                    user_id=None,
                    tenant_id=None,
                )

            await db.commit()

            if expired_count > 0:
                logger.info(f"Payment reconciliation: expired {expired_count} stale payments")
            return expired_count

    except Exception as e:
        logger.error(f"Payment reconciliation error: {e}")
        return 0


async def payment_reconciliation_loop():
    """Background loop — jalan setiap 5 menit."""
    logger.info("Payment reconciliation task started (interval: %ds)", RECONCILE_INTERVAL)
    while True:
        await asyncio.sleep(RECONCILE_INTERVAL)
        try:
            count = await reconcile_payments()
            if count:
                logger.info(f"Reconciled {count} payments")
        except Exception as e:
            logger.error(f"Reconciliation loop error: {e}")
