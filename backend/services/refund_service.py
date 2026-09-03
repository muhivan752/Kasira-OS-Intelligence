"""Refund otomatis untuk pesanan online yang dibatalkan sesudah dibayar QRIS.

Dipanggil dari `order_lifecycle.cancel_order` (tolak oleh kasir, batas
konfirmasi lewat). Selalu bikin baris `payment_refunds` supaya kelihatan di
dashboard, apa pun hasil ke Xendit:

- Xendit sukses (SUCCEEDED / PENDING) -> refund `completed`, payment `refunded`,
  reference_id = id refund Xendit. Pakai `_settle_refund` yang sama dengan
  jalur refund manual supaya stok dan tab diperlakukan sama.
- Xendit gagal (kunci nggak ada, channel nggak dukung, 4xx) -> refund tetap
  `pending` + alasan di metadata, pemilik dikabari WA. Ini yang dimaksud
  "refund manual": uangnya dikembalikan orang, catatannya tetap ada.

Nggak pernah raise dan nggak commit. Panggil di dalam transaksi pemanggil.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from backend.models.event import Event
from backend.models.payment_refund import PaymentRefund

logger = logging.getLogger(__name__)


def _qr_payment_id(payment) -> Optional[str]:
    raw = payment.xendit_raw or {}
    if not isinstance(raw, dict):
        return None
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    pid = data.get("id") or data.get("payment_id")
    if isinstance(pid, str) and pid.startswith("qrpy"):
        return pid
    return None


async def auto_refund_payment(db, payment, outlet, *, reason: str, actor_user_id=None) -> tuple[Optional[PaymentRefund], bool]:
    """Return (refund, is_manual). refund None kalau nggak ada yang perlu dikembalikan."""
    method = payment.payment_method.value if hasattr(payment.payment_method, "value") else str(payment.payment_method)
    status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    if status != "paid" or method != "qris":
        return None, False

    existing = (await db.execute(
        select(PaymentRefund).where(
            PaymentRefund.payment_id == payment.id,
            PaymentRefund.deleted_at.is_(None),
            PaymentRefund.status.in_(["pending", "approved", "completed"]),
        )
    )).scalars().first()
    if existing:
        return existing, existing.status != "completed"

    amount = Decimal(str(payment.amount_paid))
    refund = PaymentRefund(
        payment_id=payment.id,
        amount=amount,
        reason=reason[:500],
        requested_by=actor_user_id,
        metadata_payload={"source": "storefront_auto"},
    )
    db.add(refund)
    await db.flush()

    manual = True
    error: Optional[str] = None
    qrpy = _qr_payment_id(payment)
    has_key = bool(outlet.xendit_api_key or outlet.xendit_business_id)
    if qrpy and has_key:
        try:
            from backend.services.xendit import xendit_service
            res = await xendit_service.create_qr_refund(
                qr_payment_id=qrpy,
                amount=int(amount),
                reason="CANCELLATION",
                reference_id=f"refund::{refund.id}",
                merchant_api_key=outlet.xendit_api_key,
                for_user_id=outlet.xendit_business_id if not outlet.xendit_api_key else None,
            )
            x_status = str(res.get("status", "")).upper()
            refund.reference_id = res.get("id")
            refund.metadata_payload = {**(refund.metadata_payload or {}), "xendit": res}
            if x_status in ("SUCCEEDED", "PENDING"):
                manual = False
            else:
                error = f"status Xendit {x_status or 'tidak dikenal'}"
        except Exception as e:  # noqa: BLE001
            error = str(e)[:300]
            logger.warning("auto refund Xendit gagal payment=%s: %s", payment.id, e, exc_info=True)
    elif not qrpy:
        error = "id pembayaran QR tidak ditemukan di payload Xendit"
    else:
        error = "outlet belum terhubung Xendit"

    now = datetime.now(timezone.utc)
    if manual:
        refund.metadata_payload = {**(refund.metadata_payload or {}), "manual_reason": error}
        db.add(Event(
            outlet_id=payment.outlet_id,
            stream_id=f"refund:{refund.id}",
            event_type="refund.requested",
            event_data={"refund_id": str(refund.id), "payment_id": str(payment.id),
                        "amount": float(amount), "reason": reason, "auto": True, "manual_reason": error},
            event_metadata={"ts": now.isoformat()},
        ))
        return refund, True

    from backend.api.routes.payments import _settle_refund  # lazy: hindari import melingkar
    await _settle_refund(db, refund, actor_user_id, now)
    db.add(Event(
        outlet_id=payment.outlet_id,
        stream_id=f"refund:{refund.id}",
        event_type="refund.completed",
        event_data={"refund_id": str(refund.id), "payment_id": str(payment.id),
                    "amount": float(amount), "auto": True, "xendit_id": refund.reference_id},
        event_metadata={"ts": now.isoformat()},
    ))
    return refund, False
