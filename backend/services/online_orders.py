"""Pesanan online (storefront): kabar ke pelanggan, ke pemilik, dan ke app kasir.

Satu tempat untuk semua teks WA alur pesanan online, supaya bahasa yang
dibaca pelanggan dan yang dibaca kasir konsisten. Halaman lacak di web
(`app/[slug]/order/[id]`) memakai label yang sama.

Alur status (orders.source = 'storefront'):
  pending  -> menunggu konfirmasi toko (QRIS: menunggu pembayaran dulu)
  preparing-> toko menerima, ada perkiraan waktu (accepted_at + eta_minutes)
  ready    -> siap diambil / sedang diantar / diantar ke meja
  completed-> selesai
  cancelled-> ditolak toko, dibatalkan sistem (lewat batas konfirmasi), atau
              pembayaran QRIS tidak diselesaikan

Kabar ke app kasir lewat Redis pub/sub kanal `orders:{outlet_id}`, dibaca
`GET /orders/stream` (SSE). Publish nggak pernah raise: kalau Redis mati,
order tetap tersimpan dan app masih bisa polling.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

import redis.asyncio as redis

from backend.core.config import settings
from backend.services.fonnte import send_whatsapp_message, send_whatsapp_with_token

logger = logging.getLogger(__name__)

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

ORDER_TYPE_LABEL = {
    "takeaway": "Ambil sendiri",
    "pickup": "Ambil sendiri",
    "delivery": "Antar ke alamat",
    "dine_in": "Makan di tempat",
}


def channel_for(outlet_id) -> str:
    return f"orders:{outlet_id}"


async def publish(outlet_id, event_type: str, data: dict) -> None:
    """Kabar real-time ke app kasir. Gagal = log, jangan ganggu transaksi."""
    try:
        payload = {"type": event_type, "ts": datetime.now(timezone.utc).isoformat(), **data}
        await _redis.publish(channel_for(outlet_id), json.dumps(payload, default=str))
    except Exception:  # noqa: BLE001
        logger.warning("online_orders publish gagal outlet=%s type=%s", outlet_id, event_type, exc_info=True)


def track_url(outlet_slug: Optional[str], order_id) -> str:
    return f"{settings.SITE_URL}/{outlet_slug}/order/{order_id}"


def order_type_label(order_type) -> str:
    key = order_type.value if hasattr(order_type, "value") else str(order_type or "")
    return ORDER_TYPE_LABEL.get(key, key)


def _rp(amount) -> str:
    try:
        return "Rp " + f"{int(round(float(amount))):,}".replace(",", ".")
    except Exception:  # noqa: BLE001
        return f"Rp {amount}"


def _items_lines(items: Iterable) -> str:
    lines = []
    for it in items:
        name = getattr(it, "product_name", None) or "Item"
        lines.append(f"- {it.quantity}x {name}")
    return "\n".join(lines)


async def wa_customer(outlet, phone: Optional[str], message: str) -> bool:
    """Kirim WA ke pelanggan dari nomor toko kalau toko punya token Fonnte
    sendiri, kalau tidak dari nomor platform. Nggak pernah raise."""
    if not phone:
        return False
    try:
        token = getattr(outlet, "fonnte_token", None)
        if token:
            ok = await send_whatsapp_with_token(token, phone, message)
            if ok:
                return True
        return await send_whatsapp_message(phone, message)
    except Exception:  # noqa: BLE001
        logger.warning("online_orders wa_customer gagal ke %s", phone, exc_info=True)
        return False


async def wa_owner(outlet, message: str) -> bool:
    """Kabar ke pemilik: WA (nomor WhatsApp toko, kalau kosong nomor outlet)
    plus Sefrekuensi kalau pintunya sudah dicolok. Ini SATU-SATUNYA pintu
    notifikasi merchant (pesanan online, reservasi, refund manual); kanal
    baru ditambah di sini, bukan di pemanggilnya."""
    await push_sefrekuensi(outlet, message)
    if not getattr(outlet, "online_notify_owner_wa", True):
        return False
    target = (getattr(outlet, "whatsapp_number", None) or getattr(outlet, "phone", None) or "").strip()
    if not target:
        return False
    try:
        return await send_whatsapp_message(target, message)
    except Exception:  # noqa: BLE001
        logger.warning("online_orders wa_owner gagal ke %s", target, exc_info=True)
        return False


async def push_sefrekuensi(outlet, message: str) -> bool:
    """Notifikasi merchant ke Sefrekuensi (strategi akuisisi user, keputusan
    Ivan 4 Sep 2026). Nggak aktif sampai SEFREKUENSI_NOTIFY_URL diisi.
    Kontrak: POST JSON {phone, outlet_id, outlet_name, message, source}
    dengan header Authorization Bearer. Gagal = catat log, jangan ganggu WA."""
    url = (settings.SEFREKUENSI_NOTIFY_URL or "").strip()
    if not url:
        return False
    target = (getattr(outlet, "whatsapp_number", None) or getattr(outlet, "phone", None) or "").strip()
    try:
        import httpx
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
            r = await client.post(url, json={
                "phone": target, "outlet_id": str(outlet.id), "outlet_name": outlet.name,
                "message": message, "source": "selaris",
            }, headers={"Authorization": f"Bearer {settings.SEFREKUENSI_NOTIFY_TOKEN}"} if settings.SEFREKUENSI_NOTIFY_TOKEN else {})
        return r.status_code < 300
    except Exception:  # noqa: BLE001
        logger.warning("push_sefrekuensi gagal outlet=%s", getattr(outlet, "id", None), exc_info=True)
        return False


# ── Teks pesan ────────────────────────────────────────────────────────────

def msg_received(order, outlet, *, awaiting_payment: bool, auto_cancel_minutes: int, manual_qris: bool = False) -> str:
    head = f"Pesanan #{order.display_number} di {outlet.name} sudah kami terima."
    if manual_qris:
        body = (
            f"Bayar {_rp(order.total_amount)} ke QRIS toko yang tampil di halaman pesanan, "
            "lalu balas pesan ini dengan bukti bayarnya. "
            f"Toko akan mengonfirmasi dalam {auto_cancel_minutes} menit setelah bukti diterima."
        )
    elif awaiting_payment:
        body = (
            "Selesaikan pembayaran QRIS lewat halaman pesanan. Setelah lunas, "
            "toko akan mengonfirmasi pesanan Anda."
        )
    else:
        body = (
            f"Toko akan mengonfirmasi dalam {auto_cancel_minutes} menit. "
            "Kalau tidak dikonfirmasi, pesanan dibatalkan otomatis dan pembayaran dikembalikan."
        )
    return f"{head}\n{body}\n\nLacak pesanan: {track_url(outlet.slug, order.id)}"


def msg_paid(order, outlet, *, auto_cancel_minutes: int) -> str:
    return (
        f"Pembayaran {_rp(order.total_amount)} untuk pesanan #{order.display_number} di {outlet.name} sudah kami terima.\n"
        f"Toko akan mengonfirmasi dalam {auto_cancel_minutes} menit. Kalau tidak dikonfirmasi, "
        "pesanan dibatalkan otomatis dan pembayaran dikembalikan.\n\n"
        f"Lacak pesanan: {track_url(outlet.slug, order.id)}"
    )


def msg_accepted(order, outlet) -> str:
    eta = order.eta_minutes or 15
    what = {
        "takeaway": "siap diambil",
        "delivery": "siap diantar",
        "dine_in": "diantar ke meja Anda",
    }.get(_type_key(order), "siap")
    return (
        f"Pesanan #{order.display_number} dikonfirmasi {outlet.name}.\n"
        f"Perkiraan {what} dalam {eta} menit.\n\n"
        f"Lacak pesanan: {track_url(outlet.slug, order.id)}"
    )


def msg_ready(order, outlet) -> str:
    key = _type_key(order)
    if key == "delivery":
        line = "Pesanan Anda sedang diantar ke alamat tujuan."
    elif key == "dine_in":
        line = "Pesanan Anda sedang diantar ke meja."
    else:
        line = f"Pesanan Anda sudah siap diambil di {outlet.name}."
    return f"Pesanan #{order.display_number} siap.\n{line}\n\nLacak pesanan: {track_url(outlet.slug, order.id)}"


def msg_cancelled(order, outlet, *, refund_amount=None, refund_manual: bool = False) -> str:
    reason = order.cancel_reason or "dibatalkan oleh toko"
    text = f"Pesanan #{order.display_number} di {outlet.name} dibatalkan.\nAlasan: {reason}."
    if refund_amount:
        if refund_manual:
            text += (
                f"\nPembayaran {_rp(refund_amount)} akan dikembalikan oleh toko. "
                "Silakan hubungi toko lewat tombol WhatsApp di halaman pesanan."
            )
        else:
            text += (
                f"\nPembayaran {_rp(refund_amount)} dikembalikan ke metode pembayaran Anda, "
                "biasanya 1 sampai 3 hari kerja."
            )
    return text + f"\n\nDetail: {track_url(outlet.slug, order.id)}"


def msg_owner_new_order(order, outlet, customer_name: Optional[str], items: Iterable, *, paid: bool,
                        manual_qris: bool = False) -> str:
    if paid:
        pay = "Lunas (QRIS)"
    elif manual_qris:
        pay = "QRIS toko, cek bukti bayar"
    else:
        pay = "Bayar di kasir"
    lines = _items_lines(items)
    extra = ""
    lat, lng = getattr(order, "delivery_lat", None), getattr(order, "delivery_lng", None)
    if lat is not None and lng is not None:
        from backend.services.geo_service import maps_link
        km = getattr(order, "delivery_distance_km", None)
        extra = f"\nPeta: {maps_link(lat, lng)}" + (f" ({float(km):.1f} km)" if km is not None else "")
    return (
        f"Pesanan online baru #{order.display_number}\n"
        f"{order_type_label(order.order_type)} · {pay}\n"
        f"Pemesan: {customer_name or '-'}\n"
        f"{lines}\n"
        f"Total {_rp(order.total_amount)}{extra}\n\n"
        f"Buka aplikasi kasir untuk mengonfirmasi. Batas {outlet.online_auto_cancel_minutes} menit."
    )


def msg_owner_new_reservation(reservation, outlet, *, deposit: Optional[dict]) -> str:
    when = f"{reservation.reservation_date} pukul {reservation.start_time.strftime('%H:%M') if reservation.start_time else '-'}"
    dp = ""
    if deposit and deposit.get("amount"):
        dp = f"\nDP {_rp(deposit['amount'])}: " + ("lunas" if deposit.get("status") == "paid" else "menunggu bukti bayar")
    return (
        f"Reservasi online baru\n"
        f"{reservation.customer_name or '-'} · {reservation.guest_count} tamu\n"
        f"{when}{dp}\n\n"
        "Konfirmasi lewat aplikasi kasir atau dashboard, menu Reservasi."
    )


def msg_customer_reservation(reservation, outlet, *, deposit: Optional[dict], track: str) -> str:
    when = f"{reservation.reservation_date} pukul {reservation.start_time.strftime('%H:%M') if reservation.start_time else '-'}"
    head = f"Reservasi di {outlet.name} untuk {reservation.guest_count} tamu, {when}, sudah kami terima."
    if deposit and deposit.get("status") in ("pending", "pending_manual_check"):
        body = (
            f"Untuk mengamankan meja, bayar DP {_rp(deposit['amount'])} lewat halaman reservasi "
            f"dan unggah bukti bayarnya di sana. Toko mengonfirmasi setelah DP diterima. "
            f"Batas {60} menit."
        )
    elif _val(reservation.status) == "confirmed":
        body = "Reservasi sudah dikonfirmasi. Sampai bertemu."
    else:
        body = "Toko akan mengonfirmasi reservasi Anda."
    return f"{head}\n{body}\n\nDetail: {track}"


def _val(x) -> str:
    return x.value if hasattr(x, "value") else str(x)


def msg_owner_refund_manual(order, outlet, amount) -> str:
    return (
        f"Refund {_rp(amount)} untuk pesanan #{order.display_number} belum bisa diproses otomatis.\n"
        "Kembalikan ke pelanggan lewat dashboard Xendit atau transfer, lalu tandai selesai di "
        f"Dashboard {settings.BRAND_NAME} menu Refund."
    )


def _type_key(order) -> str:
    t = order.order_type
    return t.value if hasattr(t, "value") else str(t or "")
