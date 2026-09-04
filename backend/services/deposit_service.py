"""DP (uang muka) reservasi, 4 Sep 2026.

Kolomnya sudah ada sejak reservasi lahir (reservation_settings.require_deposit
+ deposit_amount, reservations.deposit_amount + deposit_payment_id) tapi nggak
pernah dipakai: reservasi online tanpa DP itu janji kosong, meja ditahan dan
tamunya nggak datang. Keputusan Ivan: DP itu PILIHAN merchant, nggak dipaksa.

Alur:
- Storefront: kalau toko mensyaratkan DP dan punya metode non-tunai aktif,
  reservasi lahir `pending` + satu Payment (order_id NULL, reference_id
  `reservation:{id}`) lewat pola metode bayar yang sama dengan pesanan
  (services/payment_methods.py): QRIS Xendit = QR dinamis + webhook, QRIS
  statis/transfer = pelanggan unggah bukti, kasir konfirmasi.
- Konfirmasi reservasi oleh kasir = DP manual ditandai lunas.
- Tamu duduk (seat) + meja punya tab: DP nempel ke tab sebagai pembayaran
  yang sudah masuk, jadi tagihan meja otomatis berkurang. Payment dapat
  tab_id supaya laporan/keuangan menghitungnya sekali.
- Belum bayar > DEPOSIT_TIMEOUT_MINUTES: reservasi dibatalkan janitor.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from backend.models.event import Event
from backend.models.outlet import Outlet
from backend.models.payment import Payment
from backend.models.reservation import Reservation
from backend.services import payment_methods as pm

logger = logging.getLogger(__name__)

DEPOSIT_TIMEOUT_MINUTES = 60
DEPOSIT_CANCEL_REASON = "DP tidak dibayar dalam 60 menit"


def _val(x) -> str:
    return x.value if hasattr(x, "value") else str(x)


def deposit_methods(outlet) -> list[str]:
    """Metode yang bisa dipakai bayar DP dari jauh: semua yang aktif kecuali tunai."""
    return [m for m in pm.enabled_methods(outlet) if m != "cash"]


def deposit_required(settings_row, outlet) -> bool:
    return bool(settings_row and settings_row.require_deposit and Decimal(str(settings_row.deposit_amount or 0)) > 0
                and deposit_methods(outlet))


async def create_deposit_payment(db, outlet: Outlet, reservation: Reservation, *, method: Optional[str], tenant_id) -> Payment:
    methods = deposit_methods(outlet)
    m = (method or "").lower() if method else None
    if m not in methods:
        m = methods[0]
    channel = pm.resolve_channel(outlet, m)
    amount = Decimal(str(reservation.deposit_amount or 0))
    payment = Payment(
        order_id=None,
        outlet_id=outlet.id,
        payment_method=m,
        channel=channel,
        amount_due=amount,
        amount_paid=Decimal("0"),
        change_amount=Decimal("0"),
        status="pending",
        reference_id=f"reservation:{reservation.id}",
        idempotency_key=f"resv-dp:{reservation.id}",
    )
    db.add(payment)
    await db.flush()

    if m == "qris" and channel == pm.CHANNEL_XENDIT:
        from backend.services.xendit import xendit_service, XenditTransientError, XenditPermanentError
        try:
            res = await xendit_service.create_qris_transaction(
                reference_id=f"{tenant_id}::{payment.id}",
                amount=float(amount),
                for_user_id=outlet.xendit_business_id if not outlet.xendit_api_key else None,
                platform_fee_percent=0.2,
                merchant_api_key=outlet.xendit_api_key,
            )
            payment.qris_url = res.get("qr_string") or res.get("qr_url")
            payment.xendit_raw = res
            exp = res.get("expires_at")
            if exp:
                try:
                    payment.qris_expired_at = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                except ValueError:
                    pass
        except XenditPermanentError as e:
            logger.error("deposit xendit permanent payment=%s: %s", payment.id, e)
            payment.status = "failed"
            payment.xendit_raw = {"error": str(e), "error_type": "permanent"}
        except XenditTransientError as e:
            logger.error("deposit xendit transient payment=%s: %s", payment.id, e)
            payment.status = "pending_manual_check"
            payment.xendit_raw = {"error": str(e), "error_type": "transient_exhausted"}
        except Exception as e:  # noqa: BLE001
            logger.exception("deposit xendit unexpected payment=%s", payment.id)
            payment.status = "pending_manual_check"
            payment.xendit_raw = {"error": str(e), "error_type": "unexpected"}

    reservation.deposit_payment_id = payment.id
    return payment


def deposit_info(payment: Optional[Payment], outlet: Optional[Outlet], amount: Optional[Decimal] = None) -> Optional[dict]:
    """Bentuk yang dibaca halaman lacak, dashboard, dan app kasir."""
    if payment is None and not amount:
        return None
    if payment is None:
        return {"amount": float(amount), "status": "none", "method": None, "channel": None}
    method = _val(payment.payment_method)
    channel = payment.channel or ("xendit" if method == "qris" else "manual")
    status = _val(payment.status)
    info = {
        "payment_id": str(payment.id),
        "amount": float(payment.amount_due),
        "method": method,
        "channel": channel,
        "status": status,  # pending | paid | failed | cancelled | pending_manual_check
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "proof_image_url": payment.proof_image_url,
        "proof_uploaded_at": payment.proof_uploaded_at.isoformat() if payment.proof_uploaded_at else None,
        "qris_url": payment.qris_url if channel == "xendit" else None,
        "qris_expired_at": payment.qris_expired_at.isoformat() if (channel == "xendit" and payment.qris_expired_at) else None,
        "qris_static_image_url": None,
        "bank_name": None, "bank_account_number": None, "bank_account_name": None,
    }
    if outlet is not None and status in ("pending", "pending_manual_check") and channel == "manual":
        if method == "qris":
            info["qris_static_image_url"] = outlet.qris_static_image_url
        elif method == "transfer":
            info["bank_name"] = outlet.bank_name
            info["bank_account_number"] = outlet.bank_account_number
            info["bank_account_name"] = outlet.bank_account_name
    return info


def mark_paid_if_manual(payment: Optional[Payment], *, now: Optional[datetime] = None) -> bool:
    """Kasir konfirmasi = uang dianggap masuk, untuk saluran manual saja.
    QRIS Xendit menunggu webhook, jangan dipaksa lunas dari sini."""
    if payment is None:
        return False
    if (payment.channel or "xendit") != "manual":
        return False
    if _val(payment.status) not in ("pending", "pending_manual_check"):
        return False
    now = now or datetime.now(timezone.utc)
    payment.status = "paid"
    payment.paid_at = now
    payment.amount_paid = payment.amount_due
    payment.row_version = (payment.row_version or 0) + 1
    return True


async def load_deposit_payment(db, reservation: Reservation) -> Optional[Payment]:
    if not reservation.deposit_payment_id:
        return None
    return await db.get(Payment, reservation.deposit_payment_id)


async def load_deposit_map(db, reservations) -> dict:
    ids = [r.deposit_payment_id for r in reservations if r.deposit_payment_id]
    if not ids:
        return {}
    rows = (await db.execute(select(Payment).where(Payment.id.in_(ids)))).scalars().all()
    return {p.id: p for p in rows}


async def apply_deposit_to_tab(db, reservation: Reservation, payment: Optional[Payment], outlet: Outlet) -> Optional[object]:
    """Tamu duduk: DP yang sudah lunas jadi pembayaran awal tagihan meja.

    Tab dibuka kalau belum ada (helper yang sama dengan pesanan meja online).
    `tab.paid_amount` adalah bagian yang sudah dibayar lewat tab (bukan per
    item), jadi pay-full/split menghitung sisa = total - paid_amount - item
    lunas. Payment dapat `tab_id` supaya laporan shift/keuangan menghitung
    uangnya di tab ini, sekali.
    """
    if payment is None or _val(payment.status) != "paid" or not reservation.table_id:
        return None
    if payment.tab_id is not None:
        return None  # sudah pernah dipasang
    from backend.services.order_lifecycle import open_tab_for_table
    tab = await open_tab_for_table(
        db, outlet, reservation.table_id,
        customer_name=reservation.customer_name, guest_count=reservation.guest_count,
        notes=f"Reservasi {reservation.customer_name or ''}".strip(),
    )
    payment.tab_id = tab.id
    payment.row_version = (payment.row_version or 0) + 1
    tab.paid_amount = Decimal(str(tab.paid_amount or 0)) + Decimal(str(payment.amount_paid or 0))
    tab.row_version = (tab.row_version or 0) + 1
    db.add(Event(
        outlet_id=outlet.id,
        stream_id=f"tab:{tab.id}",
        event_type="tab.deposit_applied",
        event_data={"tab_id": str(tab.id), "reservation_id": str(reservation.id), "payment_id": str(payment.id),
                    "amount": float(payment.amount_paid or 0)},
        event_metadata={"ts": datetime.now(timezone.utc).isoformat()},
    ))
    from backend.services.tab_service import recalculate_tab
    await recalculate_tab(db, tab)
    return tab


async def expire_unpaid_deposits(db, *, now: Optional[datetime] = None) -> int:
    """Janitor: reservasi pending yang DP-nya belum dibayar > 60 menit dibatalkan.
    Berjalan di loop online_order_timeout (sudah punya kunci Redis + RLS bypass)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=DEPOSIT_TIMEOUT_MINUTES)
    rows = (await db.execute(
        select(Reservation, Payment).join(Payment, Payment.id == Reservation.deposit_payment_id).where(
            Reservation.status == "pending",
            Reservation.deleted_at.is_(None),
            Reservation.created_at < cutoff,
            Payment.status.in_(["pending", "pending_manual_check", "failed"]),
            Payment.proof_image_url.is_(None),  # sudah kirim bukti = tunggu kasir, jangan dibatalkan
        ).with_for_update(skip_locked=True, of=Reservation)
    )).all()
    n = 0
    for reservation, payment in rows:
        reservation.status = "cancelled"
        reservation.cancelled_at = now
        reservation.notes = ((reservation.notes or "") + f"\n[{DEPOSIT_CANCEL_REASON}]").strip()
        reservation.row_version = (reservation.row_version or 0) + 1
        if _val(payment.status) != "failed":
            payment.status = "cancelled"
            payment.cancelled_at = now
        db.add(Event(
            outlet_id=reservation.outlet_id,
            stream_id=f"reservation:{reservation.id}",
            event_type="reservation.cancelled",
            event_data={"reservation_id": str(reservation.id), "reason": DEPOSIT_CANCEL_REASON, "by": "system"},
            event_metadata={"ts": now.isoformat()},
        ))
        outlet = await db.get(Outlet, reservation.outlet_id)
        if outlet is not None and reservation.customer_phone:
            from backend.services import online_orders as _oo
            try:
                await _oo.wa_customer(
                    outlet, reservation.customer_phone,
                    f"Reservasi Anda di {outlet.name} pada {reservation.reservation_date} pukul "
                    f"{reservation.start_time.strftime('%H:%M') if reservation.start_time else '-'} dibatalkan karena DP belum diterima "
                    f"dalam {DEPOSIT_TIMEOUT_MINUTES} menit. Silakan reservasi ulang kalau masih berminat.",
                )
            except Exception:  # noqa: BLE001
                logger.warning("WA batal DP gagal reservation=%s", reservation.id, exc_info=True)
        n += 1
    return n
