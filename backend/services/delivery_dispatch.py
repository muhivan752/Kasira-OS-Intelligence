"""Antar pesanan: serahin ke kurir, sampai, gagal. SATU pintu efek samping.

Delivery gelombang 2 (5 Sep 2026, mig 108). Kurir di Selaris itu orang toko,
bukan armada agregator: toko daftarin kurirnya sendiri, pelanggan lihat nama
dan nomornya di halaman lacak lalu bisa chat langsung.

Kenapa `delivery_status` terpisah dari `orders.status`: `ready` artinya
makanannya jadi, bukan lagi di jalan. Pesanan yang dibayar di muka bahkan
bisa langsung `completed` tanpa dapur atau kurir pernah menyentuhnya. Dua
sumbu yang beda, persis alasan `kitchen_status` dipisah di mig 102.

Semua fungsi di sini TIDAK commit. Pemanggil yang commit.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from backend.models.event import Event
from backend.models.order import Order
from backend.services import online_orders

logger = logging.getLogger(__name__)

# Urutan sah: (dari) -> (boleh ke). NULL = belum disentuh kurir.
ON_THE_WAY = "on_the_way"
DELIVERED = "delivered"
FAILED = "failed"


def _val(x) -> str:
    return x.value if hasattr(x, "value") else str(x or "")


def is_delivery(order: Order) -> bool:
    return _val(order.order_type) == "delivery"


def _event(db, order: Order, event_type: str, data: dict, actor_user_id=None) -> None:
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type=event_type,
        event_data={"order_id": str(order.id), "outlet_id": str(order.outlet_id),
                    "order_number": order.order_number, **data},
        event_metadata={"ts": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(actor_user_id) if actor_user_id else None},
    ))


async def dispatch(db, order: Order, outlet, *, courier=None, courier_name: Optional[str] = None,
                   actor_user_id=None) -> None:
    """Pesanan diserahkan ke kurir. Nama kurir di-snapshot ke order.

    Kurir terdaftar (dipilih dari daftar toko) maupun nama ketikan sekali
    jalan sama-sama diterima: warung nggak selalu punya kurir tetap, kadang
    yang nganter tetangga atau ojol panggilan.
    """
    now = datetime.now(timezone.utc)
    order.courier_id = getattr(courier, "id", None)
    order.courier_name = (getattr(courier, "name", None) or courier_name or "").strip()[:80] or None
    order.delivery_status = ON_THE_WAY
    order.dispatched_at = now
    order.delivery_failed_reason = None
    order.row_version += 1
    order.updated_at = now
    _event(db, order, "delivery.dispatched", {
        "courier_id": str(order.courier_id) if order.courier_id else None,
        "courier_name": order.courier_name,
        "delivery_fee": float(order.delivery_fee or 0),
    }, actor_user_id)
    await online_orders.publish(order.outlet_id, "delivery.dispatched",
                                {"order_id": str(order.id), "courier_name": order.courier_name})


async def mark_delivered(db, order: Order, outlet, *, proof_image_url: Optional[str] = None,
                         received_by: Optional[str] = None, actor_user_id=None) -> bool:
    """Kurir sampai. Pesanan ditutup dan COD ditandai lunas.

    Return True kalau status order ikut naik jadi `completed` di sini.
    Idempoten: dipanggil dua kali (kasir + kurir dari HP lain) nggak boleh
    ngitung uangnya dua kali.
    """
    if order.delivery_status == DELIVERED:
        return False
    now = datetime.now(timezone.utc)
    order.delivery_status = DELIVERED
    order.delivered_at = now
    if proof_image_url:
        order.delivery_proof_url = proof_image_url
    if received_by:
        order.delivery_received_by = received_by.strip()[:80]
    order.row_version += 1
    order.updated_at = now

    # COD: uangnya baru berpindah tangan sekarang. Satu pintu bareng
    # PUT /orders/{id}/status completed (delivery gelombang 1).
    from backend.services.order_lifecycle import settle_cod_payment, release_table_if_idle
    await settle_cod_payment(db, order)

    completed = False
    if _val(order.status) not in ("completed", "cancelled"):
        order.status = "completed"
        completed = True
        if order.table_id:
            await release_table_if_idle(db, order)

    _event(db, order, "delivery.delivered", {
        "courier_id": str(order.courier_id) if order.courier_id else None,
        "courier_name": order.courier_name,
        "received_by": order.delivery_received_by,
        "has_proof": bool(order.delivery_proof_url),
        "delivery_fee": float(order.delivery_fee or 0),
        "total_amount": float(order.total_amount or 0),
        "order_completed": completed,
    }, actor_user_id)
    await online_orders.publish(order.outlet_id, "delivery.delivered", {"order_id": str(order.id)})
    return completed


async def mark_failed(db, order: Order, outlet, *, reason: str, actor_user_id=None) -> None:
    """Gagal antar: alamat nggak ketemu, orangnya nggak ada, ditolak.

    SENGAJA nggak membatalkan order dan nggak balikin stok: barangnya sudah
    jadi dan mungkin sudah dibayar. Kasir yang memutuskan mau dikirim ulang
    (dispatch lagi) atau dibatalkan (jalur cancel yang sudah ada, yang tahu
    cara refund dan balikin stok).
    """
    now = datetime.now(timezone.utc)
    order.delivery_status = FAILED
    order.delivery_failed_reason = reason.strip()[:200]
    order.row_version += 1
    order.updated_at = now
    _event(db, order, "delivery.failed", {"reason": order.delivery_failed_reason,
                                          "courier_name": order.courier_name}, actor_user_id)
    await online_orders.publish(order.outlet_id, "delivery.failed",
                                {"order_id": str(order.id), "reason": order.delivery_failed_reason})
