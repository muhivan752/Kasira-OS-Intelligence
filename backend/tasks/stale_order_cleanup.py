"""
Stale Order Cleanup — Janitor task for abandoned dine-in pending orders.

Background:
- Cashier creates dine-in order at table → stock deducted, table occupied.
- Cashier forgets to complete/cancel (shift change, distraction, crash).
- Table release guard in orders.py:519 + payments.py:303 counts active orders
  → stale pending blocks new customer from occupying that table.

Loop:
- Runs every 1 hour.
- Scope: status IN ('pending', 'preparing') — real kitchen prep ≤30min,
  so >24h in either state = unambiguously abandoned.
- Threshold: 24 hours since created_at AND 24 hours since updated_at
  (double-guard: no recent activity = truly abandoned).
- Per stale order: restore stock, cancel order, release table, emit event.
- Orphan heal pass: any `tables.status='occupied'` with zero active orders
  → force `available`. Catches legacy residue from pre-Batch #19 bug +
  any future gap.
- Reuses helpers from orders.py cancel path (restore_stock_on_cancel /
  restore_ingredients_on_cancel) — zero new stock logic.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, text, update
from sqlalchemy.orm import selectinload

from backend.core.database import AsyncSessionLocal
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.outlet import Outlet
from backend.models.tenant import Tenant
from backend.models.table import Table
from backend.models.tab import Tab
from backend.models.event import Event
from backend.services.stock_service import restore_stock_on_cancel
from backend.services.ingredient_stock_service import restore_ingredients_on_cancel
from backend.services.tab_service import recalculate_tab

logger = logging.getLogger(__name__)

STALE_THRESHOLD_HOURS = 24
CHECK_INTERVAL_SECONDS = 3600  # 1 jam


async def cleanup_stale_orders_once() -> dict:
    """Single pass: find stale pending dine_in orders, cancel + restore stock + release table."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_THRESHOLD_HOURS)
    cancelled_count = 0
    failed_count = 0

    async with AsyncSessionLocal() as db:
        # Bypass RLS — janitor cross-tenant
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

        stale_q = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(
                Order.status.in_(['pending', 'preparing']),
                Order.order_type == 'dine_in',
                Order.deleted_at.is_(None),
                Order.created_at < cutoff,
                Order.updated_at < cutoff,
            )
        )
        stale = (await db.execute(stale_q)).scalars().all()

        if stale:
            logger.info(f"stale_order_cleanup: found {len(stale)} stale order(s)")

        for order in stale:
            try:
                from_status = order.status.value if hasattr(order.status, 'value') else str(order.status)

                # Resolve tier + stock_mode (mirror orders.py:461-474)
                outlet = await db.get(Outlet, order.outlet_id)
                tier = "starter"
                stock_mode = "simple"
                if outlet:
                    sm = getattr(outlet, 'stock_mode', 'simple')
                    stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')
                    if outlet.tenant_id:
                        tenant = await db.get(Tenant, outlet.tenant_id)
                        if tenant:
                            raw_tier = getattr(tenant, 'subscription_tier', None) or "starter"
                            tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)

                # Restore stock (mirror orders.py:475-495)
                for item in order.items:
                    product = await db.get(Product, item.product_id)
                    if product and product.stock_enabled:
                        if stock_mode == 'recipe':
                            await restore_ingredients_on_cancel(
                                db,
                                product_id=product.id,
                                quantity=item.quantity,
                                outlet_id=order.outlet_id,
                                order_id=order.id,
                                tier=tier,
                            )
                        else:
                            await restore_stock_on_cancel(
                                db,
                                product=product,
                                quantity=item.quantity,
                                outlet_id=order.outlet_id,
                                order_id=order.id,
                                tier=tier,
                            )

                # Cancel order
                order.status = 'cancelled'
                order.row_version += 1

                # Recalc parent tab (mirror orders.py:498-517 cancel path).
                # Janitor cancel leaves stale tab.total_amount otherwise → Batch #20 gap.
                # Skip if tab already closed (paid/cancelled) or deleted.
                if order.tab_id:
                    try:
                        linked_tab = (await db.execute(
                            select(Tab).where(
                                Tab.id == order.tab_id,
                                Tab.deleted_at.is_(None),
                            )
                        )).scalar_one_or_none()
                        if linked_tab and linked_tab.status not in ('paid', 'cancelled'):
                            await recalculate_tab(db, linked_tab)
                            linked_tab.row_version += 1
                    except Exception as e:
                        logger.error(
                            f"stale_order_cleanup: tab recalc failed for order {order.id} "
                            f"(tab {order.tab_id}): {e}"
                        )

                # Release table if no other active orders (mirror orders.py:519-533)
                if order.table_id:
                    active_orders = (await db.execute(
                        select(func.count(Order.id)).where(
                            Order.table_id == order.table_id,
                            Order.id != order.id,
                            Order.status.notin_(['completed', 'cancelled']),
                            Order.deleted_at.is_(None),
                        )
                    )).scalar() or 0
                    if active_orders == 0:
                        await db.execute(
                            update(Table).where(Table.id == order.table_id)
                            .values(status='available', row_version=Table.row_version + 1)
                        )

                # Emit cancellation event (auditable)
                db.add(Event(
                    outlet_id=order.outlet_id,
                    stream_id=f"order:{order.id}",
                    event_type="order.cancelled",
                    event_data={
                        "order_id": str(order.id),
                        "outlet_id": str(order.outlet_id),
                        "order_number": order.order_number,
                        "from_status": from_status,
                        "to_status": "cancelled",
                        "total_amount": float(order.total_amount),
                        "order_type": order.order_type,
                        "item_count": len(order.items),
                        "table_id": str(order.table_id) if order.table_id else None,
                        "reason": f"auto_cleanup: stale {from_status} >{STALE_THRESHOLD_HOURS}h",
                    },
                    event_metadata={
                        "actor": "janitor:stale_order_cleanup",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    },
                ))

                cancelled_count += 1
            except Exception as e:
                logger.error(f"stale_order_cleanup: failed to cancel order {order.id}: {e}")
                failed_count += 1
                # Don't rollback here — let other orders commit; bad one just logged
                continue

        # Orphan table heal pass: tables.status='occupied' but zero active orders
        # → force 'available'. Catches legacy residue from pre-Batch #19 bug
        # (cash payment didn't release table) + any future gap.
        # GUARD: SKIP heal kalau table punya tab yang masih aktif (open/asking_bill/
        # splitting). Order completed via Kitchen Display tidak otomatis = paid;
        # table harus stay occupied sampai tab.status = paid/cancelled.
        orphan_healed = 0
        try:
            occupied_tables = (await db.execute(
                select(Table).where(Table.status == 'occupied')
            )).scalars().all()

            for tbl in occupied_tables:
                # Cek tab aktif di table — kalau ada, skip heal
                active_tab = (await db.execute(
                    select(func.count(Tab.id)).where(
                        Tab.table_id == tbl.id,
                        Tab.deleted_at.is_(None),
                        Tab.status.notin_(['paid', 'cancelled']),
                    )
                )).scalar() or 0
                if active_tab > 0:
                    continue  # skip heal — tab masih owe payment

                active = (await db.execute(
                    select(func.count(Order.id)).where(
                        Order.table_id == tbl.id,
                        Order.status.notin_(['completed', 'cancelled']),
                        Order.deleted_at.is_(None),
                    )
                )).scalar() or 0
                if active == 0:
                    tbl.status = 'available'
                    tbl.row_version += 1
                    orphan_healed += 1
                    db.add(Event(
                        outlet_id=tbl.outlet_id,
                        stream_id=f"table:{tbl.id}",
                        event_type="table.auto_released",
                        event_data={
                            "table_id": str(tbl.id),
                            "table_name": tbl.name,
                            "reason": "orphan_heal: occupied with zero active orders",
                        },
                        event_metadata={
                            "actor": "janitor:stale_order_cleanup",
                            "ts": datetime.now(timezone.utc).isoformat(),
                        },
                    ))
            if orphan_healed:
                logger.info(f"stale_order_cleanup: healed {orphan_healed} orphan occupied table(s)")
        except Exception as e:
            logger.error(f"stale_order_cleanup: orphan heal pass error: {e}")

        try:
            await db.commit()
        except Exception as e:
            logger.error(f"stale_order_cleanup: commit failed: {e}")
            await db.rollback()
            return {"cancelled": 0, "failed": len(stale), "orphan_healed": 0}

        if cancelled_count or failed_count or orphan_healed:
            logger.info(
                f"stale_order_cleanup: cancelled={cancelled_count}, "
                f"failed={failed_count}, orphan_healed={orphan_healed}"
            )
        return {"cancelled": cancelled_count, "failed": failed_count, "orphan_healed": orphan_healed}


async def stale_order_cleanup_loop():
    """Run cleanup every hour, forever."""
    logger.info(
        f"Stale order cleanup loop started "
        f"(interval: {CHECK_INTERVAL_SECONDS}s, threshold: {STALE_THRESHOLD_HOURS}h)"
    )
    await asyncio.sleep(90)  # stagger: 90s after startup (avoid startup congestion)
    while True:
        try:
            await cleanup_stale_orders_once()
        except Exception as e:
            logger.error(f"stale_order_cleanup_loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
