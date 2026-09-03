"""Janitor pesanan online: batalkan yang lewat batas konfirmasi, kembalikan uangnya.

Dua kasus, tiap 60 detik, lintas tenant (RLS bypass, CLAUDE.md #16):

1. QRIS belum dibayar > 16 menit (QR berlaku 15): pelanggan nggak jadi bayar.
   Dulu order + stok yang sudah dipotong nyangkut selamanya (janitor stale
   order cuma nyapu dine_in sesudah 24 jam). Sekarang dibatalkan senyap,
   alasan "Pembayaran tidak diselesaikan". Nggak ada WA: nggak ada uang masuk.

2. Sudah lunas (QRIS) atau bayar di kasir, tapi toko belum mengonfirmasi
   dalam `outlets.online_auto_cancel_minutes` (default 10) dihitung dari
   paid_at (QRIS) atau created_at (tunai): dibatalkan, QRIS di-refund
   otomatis (fallback manual + WA pemilik), pelanggan dikabari WA.

Ini janji yang ditulis di halaman checkout pelanggan, jadi janitor ini
bagian dari produk, bukan bersih-bersih.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from backend.core.database import AsyncSessionLocal
from backend.services.online_orders import _redis
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.payment import Payment
from backend.services import online_orders
from backend.services.order_lifecycle import cancel_order

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
UNPAID_QRIS_MINUTES = 16
UNPAID_REASON = "Pembayaran tidak diselesaikan"
UNCONFIRMED_REASON = "Toko belum mengonfirmasi dalam batas waktu"


LOCK_KEY = "online_order_timeout:lock"


async def expire_online_orders_once() -> dict:
    now = datetime.now(timezone.utc)
    stats = {"unpaid": 0, "unconfirmed": 0, "failed": 0}

    # uvicorn jalan 2 worker dan tiap worker punya supervisor sendiri, jadi
    # tanpa kunci pass ini jalan DUA kali bersamaan. Kegigit di deploy
    # pertama (3 Sep 2026): tiap order dibatalkan 2x, stok balik 2x. Kunci
    # Redis bikin cuma satu worker per menit yang menyapu; SKIP LOCKED di
    # query jadi lapis kedua kalau Redis mati.
    try:
        got = await _redis.set(LOCK_KEY, "1", nx=True, ex=50)
        if not got:
            return stats
    except Exception:  # noqa: BLE001
        logger.warning("online_order_timeout: redis lock gagal, lanjut dengan SKIP LOCKED", exc_info=True)

    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

        candidates = (await db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(
                Order.source == "storefront",
                Order.status == "pending",
                Order.accepted_at.is_(None),
                Order.deleted_at.is_(None),
                Order.created_at < now - timedelta(minutes=1),
            )
            .with_for_update(skip_locked=True, of=Order)
        )).scalars().all()

        for order in candidates:
            try:
                if str(getattr(order.status, "value", order.status)) != "pending":
                    continue
                outlet = await db.get(Outlet, order.outlet_id)
                if outlet is None:
                    continue
                payment = (await db.execute(
                    select(Payment).where(Payment.order_id == order.id, Payment.deleted_at.is_(None))
                    .order_by(Payment.created_at.desc()).limit(1)
                )).scalar_one_or_none()

                p_status = _v(payment.status) if payment else None
                p_method = _v(payment.payment_method) if payment else None

                # Kasus 1: QRIS belum dibayar.
                if payment is not None and p_method == "qris" and p_status in ("pending", "pending_manual_check", "failed"):
                    if order.created_at < now - timedelta(minutes=UNPAID_QRIS_MINUTES):
                        await cancel_order(db, order, outlet, reason=UNPAID_REASON, by="system")
                        await db.commit()
                        stats["unpaid"] += 1
                    continue

                # Kasus 2: sudah lunas / tunai, toko diam.
                limit_min = max(1, int(outlet.online_auto_cancel_minutes or 10))
                clock = order.created_at
                if payment is not None and p_status == "paid" and p_method == "qris" and payment.paid_at:
                    clock = payment.paid_at
                if clock >= now - timedelta(minutes=limit_min):
                    continue

                info = await cancel_order(db, order, outlet, reason=UNCONFIRMED_REASON, by="system")
                phone = order.customer_phone
                await db.commit()
                stats["unconfirmed"] += 1

                await online_orders.wa_customer(
                    outlet, phone,
                    online_orders.msg_cancelled(order, outlet, refund_amount=info["refund_amount"],
                                                refund_manual=info["refund_manual"]),
                )
                if info["refund_manual"] and info["refund_amount"]:
                    await online_orders.wa_owner(outlet, online_orders.msg_owner_refund_manual(order, outlet, info["refund_amount"]))
                logger.info("online_order_timeout: cancelled %s (%s)", order.order_number, UNCONFIRMED_REASON)
            except Exception:  # noqa: BLE001
                stats["failed"] += 1
                logger.warning("online_order_timeout gagal order=%s", order.id, exc_info=True)
                await db.rollback()
                await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    return stats


def _v(x) -> str:
    return x.value if hasattr(x, "value") else str(x)


async def online_order_timeout_loop() -> None:
    logger.info("online_order_timeout loop start (every %ss)", CHECK_INTERVAL_SECONDS)
    while True:
        try:
            s = await expire_online_orders_once()
            if s["unpaid"] or s["unconfirmed"] or s["failed"]:
                logger.info("online_order_timeout: %s", s)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.error("online_order_timeout loop error", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
