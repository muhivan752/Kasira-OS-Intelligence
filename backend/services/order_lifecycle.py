"""Siklus hidup order: terima, tandai siap, batalkan. SATU pintu untuk efek samping.

Sebelum ini logika "order dibatalkan" (balikin stok, hitung ulang tab, lepas
meja) cuma hidup inline di `PUT /orders/{id}/status`. Pesanan online butuh
dua pemanggil baru (tolak oleh kasir, batas konfirmasi lewat di janitor), jadi
logikanya ditarik ke sini dan endpoint lama ikut memakainya. Stok tetap lewat
`stock_service` / `ingredient_stock_service` (ARCHITECTURE.md: 6+ code path).

Semua fungsi di sini TIDAK commit. Pemanggil yang commit.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update

from backend.models.event import Event
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.payment import Payment
from backend.models.product import Product
from backend.models.reservation import Table
from backend.models.tenant import Tenant
from backend.services.stock_service import restore_stock_on_cancel
from backend.services.ingredient_stock_service import restore_ingredients_on_cancel
from backend.services import online_orders

logger = logging.getLogger(__name__)


def _val(x) -> str:
    return x.value if hasattr(x, "value") else str(x)


async def tier_and_stock_mode(db, outlet: Optional[Outlet]) -> tuple[str, str]:
    tier, stock_mode = "starter", "simple"
    if outlet:
        stock_mode = _val(getattr(outlet, "stock_mode", "simple") or "simple")
        if outlet.tenant_id:
            tenant = await db.get(Tenant, outlet.tenant_id)
            if tenant:
                tier = _val(getattr(tenant, "subscription_tier", None) or "starter")
    return tier, stock_mode


async def restore_stock_for_order(db, order: Order, outlet: Optional[Outlet]) -> None:
    """Balikin stok semua item order (simple: produk, recipe: bahan)."""
    tier, stock_mode = await tier_and_stock_mode(db, outlet)
    for item in order.items:
        product = await db.get(Product, item.product_id)
        if not product or not product.stock_enabled:
            continue
        if stock_mode == "recipe":
            await restore_ingredients_on_cancel(
                db, product_id=product.id, quantity=item.quantity,
                outlet_id=order.outlet_id, order_id=order.id, tier=tier,
            )
        else:
            await restore_stock_on_cancel(
                db, product=product, quantity=item.quantity,
                outlet_id=order.outlet_id, order_id=order.id, tier=tier,
            )


async def recalc_tab_after_cancel(db, order: Order) -> None:
    if not order.tab_id:
        return
    from backend.models.tab import Tab
    tab = (await db.execute(
        select(Tab).where(Tab.id == order.tab_id, Tab.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not tab or _val(tab.status) in ("paid", "cancelled"):
        return
    remaining = (await db.execute(
        select(Order).where(
            Order.tab_id == tab.id, Order.deleted_at.is_(None), Order.status != "cancelled",
        )
    )).scalars().all()
    tab.subtotal = sum(o.subtotal for o in remaining)
    tab.tax_amount = sum(o.tax_amount for o in remaining)
    tab.service_charge_amount = sum(o.service_charge_amount for o in remaining)
    tab.discount_amount = sum(o.discount_amount for o in remaining)
    tab.total_amount = sum(o.total_amount for o in remaining)
    tab.row_version += 1


async def release_table_if_idle(db, order: Order) -> None:
    """Lepas meja kalau nggak ada order aktif lain. GUARD tab aktif (CLAUDE.md #15)."""
    if not order.table_id:
        return
    if order.tab_id:
        from backend.models.tab import Tab
        tab_status = (await db.execute(
            select(Tab.status).where(Tab.id == order.tab_id, Tab.deleted_at.is_(None))
        )).scalar_one_or_none()
        if tab_status is not None and _val(tab_status) not in ("paid", "cancelled"):
            return
    active = (await db.execute(
        select(func.count(Order.id)).where(
            Order.table_id == order.table_id,
            Order.id != order.id,
            Order.status.notin_(["completed", "cancelled"]),
            Order.deleted_at.is_(None),
        )
    )).scalar() or 0
    if active == 0:
        await db.execute(
            update(Table).where(Table.id == order.table_id)
            .values(status="available", row_version=Table.row_version + 1)
        )


async def _set_connect_status(db, order_id, status: str) -> None:
    from backend.models.connect import ConnectOrder
    co = (await db.execute(select(ConnectOrder).where(ConnectOrder.order_id == order_id))).scalar_one_or_none()
    if co:
        co.status = status
        co.row_version = (co.row_version or 0) + 1


async def latest_payment(db, order_id) -> Optional[Payment]:
    return (await db.execute(
        select(Payment).where(Payment.order_id == order_id, Payment.deleted_at.is_(None))
        .order_by(Payment.created_at.desc()).limit(1)
    )).scalar_one_or_none()


async def accept_order(db, order: Order, outlet: Outlet, *, eta_minutes: int, actor_user_id=None) -> None:
    """pending -> preparing dengan perkiraan waktu. Kabar ke pelanggan + app kasir."""
    now = datetime.now(timezone.utc)
    order.status = "preparing"
    order.accepted_at = now
    order.eta_minutes = eta_minutes
    order.row_version += 1
    order.updated_at = now
    await _set_connect_status(db, order.id, "accepted")
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type="order.accepted",
        event_data={"order_id": str(order.id), "outlet_id": str(order.outlet_id),
                    "order_number": order.order_number, "eta_minutes": eta_minutes,
                    "source": order.source},
        event_metadata={"ts": now.isoformat(), "user_id": str(actor_user_id) if actor_user_id else None},
    ))
    await online_orders.publish(order.outlet_id, "order.accepted", {"order_id": str(order.id)})


async def mark_ready(db, order: Order) -> None:
    now = datetime.now(timezone.utc)
    order.ready_at = order.ready_at or now
    await _set_connect_status(db, order.id, "ready")
    await online_orders.publish(order.outlet_id, "order.ready", {"order_id": str(order.id)})


async def cancel_order(
    db, order: Order, outlet: Optional[Outlet], *,
    reason: str, actor_user_id=None, by: str = "cashier",
) -> dict:
    """Batalkan order + semua efek samping. `by`: cashier | system | customer.

    Return {"refund_amount", "refund_manual"} buat penyusun pesan WA.
    order.items HARUS sudah ter-load (selectinload) sebelum dipanggil.
    """
    now = datetime.now(timezone.utc)
    from_status = _val(order.status)
    if from_status == "cancelled":
        # Idempoten: dua pemanggil (kasir + janitor, atau dua worker) nggak
        # boleh balikin stok dua kali.
        return {"refund_amount": None, "refund_manual": False}
    order.status = "cancelled"
    order.cancel_reason = reason[:200]
    order.row_version += 1
    order.updated_at = now

    await restore_stock_for_order(db, order, outlet)
    await recalc_tab_after_cancel(db, order)
    await release_table_if_idle(db, order)
    await _set_connect_status(db, order.id, "rejected" if by == "cashier" else "cancelled")

    refund_amount = None
    refund_manual = False
    payment = await latest_payment(db, order.id)
    if payment is not None:
        p_status = _val(payment.status)
        p_method = _val(payment.payment_method)
        if p_status == "paid" and p_method == "qris" and outlet is not None:
            from backend.services.refund_service import auto_refund_payment
            refund, refund_manual = await auto_refund_payment(
                db, payment, outlet, reason=f"Pesanan #{order.display_number} dibatalkan: {reason}",
                actor_user_id=actor_user_id,
            )
            if refund is not None:
                refund_amount = float(refund.amount)
        elif p_status in ("pending", "pending_manual_check"):
            # QRIS belum dibayar: tutup supaya webhook telat nggak nge-paid order batal.
            payment.status = "cancelled"
            payment.row_version += 1
        elif p_status == "paid" and p_method == "cash":
            # Bayar di kasir tapi belum sampai kasir: nggak ada uang yang berpindah.
            payment.status = "cancelled"
            payment.row_version += 1

    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type="order.cancelled",
        event_data={
            "order_id": str(order.id), "outlet_id": str(order.outlet_id),
            "order_number": order.order_number, "from_status": from_status, "to_status": "cancelled",
            "reason": reason, "by": by, "source": order.source,
            "total_amount": float(order.total_amount), "order_type": _val(order.order_type),
            "item_count": len(order.items), "refund_amount": refund_amount, "refund_manual": refund_manual,
            "table_id": str(order.table_id) if order.table_id else None,
            "customer_id": str(order.customer_id) if order.customer_id else None,
        },
        event_metadata={"ts": now.isoformat(), "user_id": str(actor_user_id) if actor_user_id else None},
    ))
    await online_orders.publish(order.outlet_id, "order.cancelled", {"order_id": str(order.id), "by": by})
    return {"refund_amount": refund_amount, "refund_manual": refund_manual}
