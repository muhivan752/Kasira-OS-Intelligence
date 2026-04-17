"""
Tab service — shared helpers for tab lifecycle, payment, and event logging.
Extracted from api/routes/tabs.py to reduce file size and enable reuse.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from backend.models.tab import Tab, TabSplit
from backend.models.order import Order
from backend.models.payment import Payment
from backend.models.shift import Shift, ShiftStatus
from backend.models.event import Event
from backend.schemas.tab import TabResponse


def utc_now():
    return datetime.now(timezone.utc)


def tab_event(db, tab: Tab, event_type: str, data: dict, user_id=None):
    """Append a tab lifecycle event to event store."""
    base = {
        "tab_id": str(tab.id),
        "tab_number": tab.tab_number,
        "outlet_id": str(tab.outlet_id),
        "table_id": str(tab.table_id) if tab.table_id else None,
        "status": tab.status,
        "total_amount": float(tab.total_amount),
        "guest_count": tab.guest_count,
    }
    base.update(data)
    db.add(Event(
        outlet_id=tab.outlet_id,
        stream_id=f"tab:{tab.id}",
        event_type=event_type,
        event_data=base,
        event_metadata={
            "ts": utc_now().isoformat(),
            "user_id": str(user_id) if user_id else None,
        },
    ))


def tab_response(tab: Tab) -> TabResponse:
    """Build TabResponse with computed remaining_amount."""
    remaining = max(Decimal('0'), Decimal(str(tab.total_amount)) - Decimal(str(tab.paid_amount)))
    order_ids = [o.id for o in tab.orders] if tab.orders else []
    resp = TabResponse.model_validate(tab)
    resp.remaining_amount = remaining
    resp.order_ids = order_ids
    resp.table_name = tab.table.name if tab.table else None
    return resp


async def get_tab_or_404(
    db: AsyncSession, tab_id: UUID, *, lock: bool = False
) -> Tab:
    query = (
        select(Tab)
        .options(
            selectinload(Tab.splits),
            selectinload(Tab.orders),
            selectinload(Tab.table),
        )
        .where(Tab.id == tab_id, Tab.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    result = await db.execute(query)
    tab = result.scalar_one_or_none()
    if not tab:
        raise HTTPException(status_code=404, detail="Tab tidak ditemukan")
    return tab


async def recalculate_tab(db: AsyncSession, tab: Tab):
    """Recalculate tab totals from linked orders."""
    order_q = select(Order).where(
        Order.tab_id == tab.id,
        Order.deleted_at.is_(None),
        Order.status != 'cancelled',
    )
    result = await db.execute(order_q)
    orders = result.scalars().all()

    tab.subtotal = sum(o.subtotal for o in orders)
    tab.tax_amount = sum(o.tax_amount for o in orders)
    tab.service_charge_amount = sum(o.service_charge_amount for o in orders)
    tab.discount_amount = sum(o.discount_amount for o in orders)
    tab.total_amount = sum(o.total_amount for o in orders)


async def find_active_shift(db: AsyncSession, outlet_id: UUID, user_id: UUID) -> UUID:
    shift_q = select(Shift).where(
        Shift.outlet_id == outlet_id,
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.open,
        Shift.deleted_at.is_(None),
    )
    result = await db.execute(shift_q)
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=400, detail="Buka shift dulu sebelum membuka tab.")
    return shift.id
