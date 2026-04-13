"""
Tab/Bon + Split Bill — Pro+ Feature
Endpoints:
  POST   /tabs/                     → open tab
  GET    /tabs/                     → list tabs (outlet)
  GET    /tabs/{tab_id}             → get tab detail + splits
  POST   /tabs/{tab_id}/orders      → add order to tab
  POST   /tabs/{tab_id}/split/equal → split rata
  POST   /tabs/{tab_id}/split/per-item → split per item
  POST   /tabs/{tab_id}/split/custom   → split custom
  POST   /tabs/{tab_id}/pay-full    → bayar semua (1 orang)
  POST   /tabs/{tab_id}/splits/{split_id}/pay → bayar 1 split
  POST   /tabs/{tab_id}/cancel      → cancel tab
"""
from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.api.deps import get_current_user, require_pro_tier
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.tab import Tab, TabSplit
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.shift import Shift, ShiftStatus
from backend.schemas.tab import (
    TabCreate, TabAddOrder, TabResponse, TabSplitResponse,
    SplitEqualRequest, SplitPerItemRequest, SplitCustomRequest,
    PaySplitRequest, TabStatus, SplitMethod, TabSplitStatus,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter(dependencies=[Depends(require_pro_tier)])


def _utc_now():
    return datetime.now(timezone.utc)


def _tab_response(tab: Tab) -> TabResponse:
    """Build TabResponse with computed remaining_amount."""
    remaining = max(Decimal('0'), Decimal(str(tab.total_amount)) - Decimal(str(tab.paid_amount)))
    order_ids = [o.id for o in tab.orders] if tab.orders else []
    resp = TabResponse.model_validate(tab)
    resp.remaining_amount = remaining
    resp.order_ids = order_ids
    return resp


async def _get_tab_or_404(
    db: AsyncSession, tab_id: UUID, *, lock: bool = False
) -> Tab:
    query = (
        select(Tab)
        .options(
            selectinload(Tab.splits),
            selectinload(Tab.orders),
        )
        .where(Tab.id == tab_id, Tab.deleted_at.is_(None))
    )
    if lock:
        query = query.with_for_update()
    result = await db.execute(query)
    tab = result.scalar_one_or_none()
    if not tab:
        raise HTTPException(status_code=404, detail="Tab tidak ditemukan")
    return tab


async def _recalculate_tab(db: AsyncSession, tab: Tab):
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


async def _find_active_shift(db: AsyncSession, outlet_id: UUID, user_id: UUID) -> UUID:
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


# ── OPEN TAB ──

@router.post("/", response_model=StandardResponse[TabResponse])
async def open_tab(
    request: Request,
    body: TabCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    outlet_id = body.outlet_id
    shift_id = await _find_active_shift(db, outlet_id, current_user.id)

    # Generate tab number: TAB-YYYYMMDD-NNN
    today = _utc_now().strftime('%Y%m%d')
    count_q = select(func.count(Tab.id)).where(
        Tab.outlet_id == outlet_id,
        Tab.tab_number.like(f'TAB-{today}-%'),
    )
    count_result = await db.execute(count_q)
    seq = (count_result.scalar() or 0) + 1
    tab_number = f"TAB-{today}-{seq:03d}"

    tab = Tab(
        outlet_id=outlet_id,
        table_id=body.table_id,
        shift_session_id=shift_id,
        tab_number=tab_number,
        customer_name=body.customer_name,
        guest_count=body.guest_count,
        opened_by=current_user.id,
        opened_at=_utc_now(),
        notes=body.notes,
    )
    db.add(tab)
    await db.flush()

    await log_audit(
        db=db, action="CREATE", entity="tab", entity_id=tab.id,
        after_state={"tab_number": tab_number, "table_id": str(body.table_id), "guest_count": body.guest_count},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Tab dibuka"
    )


# ── LIST TABS ──

@router.get("/", response_model=StandardResponse[List[TabResponse]])
async def list_tabs(
    request: Request,
    outlet_id: UUID,
    status: Optional[str] = None,
    table_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = (
        select(Tab)
        .options(selectinload(Tab.splits), selectinload(Tab.orders))
        .where(Tab.outlet_id == outlet_id, Tab.deleted_at.is_(None))
    )
    if status:
        query = query.where(Tab.status == status)
    if table_id:
        query = query.where(Tab.table_id == table_id)
    query = query.order_by(Tab.created_at.desc()).limit(50)

    result = await db.execute(query)
    tabs = result.scalars().unique().all()
    return StandardResponse(
        success=True, data=[_tab_response(t) for t in tabs],
        request_id=request.state.request_id,
    )


# ── GET TAB DETAIL ──

@router.get("/{tab_id}", response_model=StandardResponse[TabResponse])
async def get_tab(
    request: Request,
    tab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id,
    )


# ── ADD ORDER TO TAB ──

@router.post("/{tab_id}/orders", response_model=StandardResponse[TabResponse])
async def add_order_to_tab(
    request: Request,
    tab_id: UUID,
    body: TabAddOrder,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status not in ('open', 'asking_bill'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup, tidak bisa tambah order.")

    order = await db.get(Order, body.order_id)
    if not order or order.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    if order.tab_id and order.tab_id != tab.id:
        raise HTTPException(status_code=400, detail="Order sudah terhubung ke tab lain")

    order.tab_id = tab.id
    await db.flush()
    await _recalculate_tab(db, tab)
    tab.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "add_order", "order_id": str(body.order_id), "total_amount": float(tab.total_amount)},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Order ditambahkan ke tab"
    )


# ── SPLIT EQUAL (bagi rata) ──

@router.post("/{tab_id}/split/equal", response_model=StandardResponse[TabResponse])
async def split_equal(
    request: Request,
    tab_id: UUID,
    body: SplitEqualRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")
    if tab.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    total = Decimal(str(tab.total_amount))
    if total <= 0:
        raise HTTPException(status_code=400, detail="Tab kosong, tambah order dulu")

    # Delete existing splits
    for s in list(tab.splits):
        await db.delete(s)

    per_person = (total / body.num_people).quantize(Decimal('0.01'))
    remainder = total - (per_person * body.num_people)

    for i in range(body.num_people):
        amount = per_person + (remainder if i == 0 else Decimal('0'))
        split = TabSplit(
            tab_id=tab.id,
            label=f"Tamu {i + 1}",
            amount=amount,
        )
        db.add(split)

    tab.split_method = 'equal'
    tab.status = 'splitting'
    tab.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "split_equal", "num_people": body.num_people},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message=f"Split rata {body.num_people} orang"
    )


# ── SPLIT PER ITEM (siapa pesan apa) ──

@router.post("/{tab_id}/split/per-item", response_model=StandardResponse[TabResponse])
async def split_per_item(
    request: Request,
    tab_id: UUID,
    body: SplitPerItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")
    if tab.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    total = Decimal(str(tab.total_amount))
    if total <= 0:
        raise HTTPException(status_code=400, detail="Tab kosong, tambah order dulu")

    # Collect all order_item IDs from this tab's orders
    order_ids = [o.id for o in tab.orders]
    if not order_ids:
        raise HTTPException(status_code=400, detail="Tab belum punya order")

    items_q = select(OrderItem).where(
        OrderItem.order_id.in_(order_ids),
        OrderItem.deleted_at.is_(None),
    )
    items_result = await db.execute(items_q)
    all_items = {i.id: i for i in items_result.scalars().all()}

    # Validate all assigned item_ids exist
    assigned_ids = set()
    for assignment in body.assignments:
        for item_id in assignment.item_ids:
            if item_id not in all_items:
                raise HTTPException(status_code=400, detail=f"Item {item_id} tidak ditemukan di tab ini")
            if item_id in assigned_ids:
                raise HTTPException(status_code=400, detail=f"Item {item_id} sudah di-assign ke orang lain")
            assigned_ids.add(item_id)

    # Delete existing splits
    for s in list(tab.splits):
        await db.delete(s)

    # Calculate proportional tax/service per person
    subtotal = Decimal(str(tab.subtotal)) or Decimal('1')
    tax_rate = Decimal(str(tab.tax_amount)) / subtotal if subtotal > 0 else Decimal('0')
    service_rate = Decimal(str(tab.service_charge_amount)) / subtotal if subtotal > 0 else Decimal('0')

    for assignment in body.assignments:
        items_subtotal = sum(
            Decimal(str(all_items[iid].total_price)) for iid in assignment.item_ids
        )
        tax_share = (items_subtotal * tax_rate).quantize(Decimal('0.01'))
        service_share = (items_subtotal * service_rate).quantize(Decimal('0.01'))
        amount = items_subtotal + tax_share + service_share

        split = TabSplit(
            tab_id=tab.id,
            label=assignment.label,
            amount=amount,
            item_ids=[str(iid) for iid in assignment.item_ids],
        )
        db.add(split)

    tab.split_method = 'per_item'
    tab.status = 'splitting'
    tab.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "split_per_item", "assignments": len(body.assignments)},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Split per item berhasil"
    )


# ── SPLIT CUSTOM (nominal bebas) ──

@router.post("/{tab_id}/split/custom", response_model=StandardResponse[TabResponse])
async def split_custom(
    request: Request,
    tab_id: UUID,
    body: SplitCustomRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")
    if tab.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    total = Decimal(str(tab.total_amount))
    if total <= 0:
        raise HTTPException(status_code=400, detail="Tab kosong, tambah order dulu")

    split_total = sum(Decimal(str(s.amount)) for s in body.splits)
    if split_total != total:
        raise HTTPException(
            status_code=400,
            detail=f"Total split Rp{split_total:,.0f} tidak sama dengan total tab Rp{total:,.0f}"
        )

    # Delete existing splits
    for s in list(tab.splits):
        await db.delete(s)

    for item in body.splits:
        split = TabSplit(
            tab_id=tab.id,
            label=item.label,
            amount=item.amount,
        )
        db.add(split)

    tab.split_method = 'custom'
    tab.status = 'splitting'
    tab.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "split_custom", "splits": len(body.splits)},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Split custom berhasil"
    )


# ── PAY FULL (1 orang bayar semua) ──

@router.post("/{tab_id}/pay-full", response_model=StandardResponse[TabResponse])
async def pay_tab_full(
    request: Request,
    tab_id: UUID,
    body: PaySplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")
    if tab.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    total = Decimal(str(tab.total_amount))
    if total <= 0:
        raise HTTPException(status_code=400, detail="Tab kosong")

    # Idempotency check
    if body.idempotency_key:
        existing = await db.execute(
            select(Payment).where(
                Payment.idempotency_key == body.idempotency_key,
                Payment.outlet_id == tab.outlet_id,
            )
        )
        if existing.scalar_one_or_none():
            tab = await _get_tab_or_404(db, tab.id)
            return StandardResponse(
                success=True, data=_tab_response(tab),
                request_id=request.state.request_id, message="Sudah dibayar (idempotent)"
            )

    if body.payment_method == 'cash' and body.amount_paid < total:
        raise HTTPException(status_code=400, detail="Nominal pembayaran kurang dari total tab")

    # Pick first order as payment anchor (or None)
    first_order_id = tab.orders[0].id if tab.orders else None

    change = max(Decimal('0'), body.amount_paid - total)
    payment = Payment(
        order_id=first_order_id,
        outlet_id=tab.outlet_id,
        shift_session_id=tab.shift_session_id,
        payment_method=body.payment_method,
        amount_due=total,
        amount_paid=body.amount_paid,
        change_amount=change,
        status='paid' if body.payment_method == 'cash' else 'pending',
        idempotency_key=body.idempotency_key,
        is_partial=False,
        paid_at=_utc_now() if body.payment_method == 'cash' else None,
        processed_by=current_user.id,
    )
    db.add(payment)
    await db.flush()

    # Delete any existing splits and create a single "full" split
    for s in list(tab.splits):
        await db.delete(s)

    full_split = TabSplit(
        tab_id=tab.id, label="Bayar Penuh", amount=total,
        payment_id=payment.id,
        status='paid' if body.payment_method == 'cash' else 'pending',
        paid_at=_utc_now() if body.payment_method == 'cash' else None,
    )
    db.add(full_split)

    if body.payment_method == 'cash':
        tab.paid_amount = total
        tab.status = 'paid'
        tab.split_method = 'full'
        tab.closed_by = current_user.id
        tab.closed_at = _utc_now()
        # Mark all orders as completed
        for order in tab.orders:
            if order.status not in ('completed', 'cancelled'):
                order.status = 'completed'
                order.row_version += 1

    tab.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "pay_full", "amount": float(total), "method": body.payment_method},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Tab dibayar penuh"
    )


# ── PAY SINGLE SPLIT ──

@router.post("/{tab_id}/splits/{split_id}/pay", response_model=StandardResponse[TabResponse])
async def pay_split(
    request: Request,
    tab_id: UUID,
    split_id: UUID,
    body: PaySplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")

    split = None
    for s in tab.splits:
        if s.id == split_id:
            split = s
            break
    if not split:
        raise HTTPException(status_code=404, detail="Split tidak ditemukan")
    if split.status == 'paid':
        raise HTTPException(status_code=400, detail="Split ini sudah dibayar")
    if split.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    split_amount = Decimal(str(split.amount))

    if body.payment_method == 'cash' and body.amount_paid < split_amount:
        raise HTTPException(status_code=400, detail="Nominal pembayaran kurang")

    # Idempotency
    if body.idempotency_key:
        existing = await db.execute(
            select(Payment).where(
                Payment.idempotency_key == body.idempotency_key,
                Payment.outlet_id == tab.outlet_id,
            )
        )
        if existing.scalar_one_or_none():
            tab = await _get_tab_or_404(db, tab.id)
            return StandardResponse(
                success=True, data=_tab_response(tab),
                request_id=request.state.request_id, message="Sudah dibayar (idempotent)"
            )

    first_order_id = tab.orders[0].id if tab.orders else None
    change = max(Decimal('0'), body.amount_paid - split_amount)

    payment = Payment(
        order_id=first_order_id,
        outlet_id=tab.outlet_id,
        shift_session_id=tab.shift_session_id,
        payment_method=body.payment_method,
        amount_due=split_amount,
        amount_paid=body.amount_paid,
        change_amount=change,
        status='paid' if body.payment_method == 'cash' else 'pending',
        idempotency_key=body.idempotency_key,
        is_partial=True,
        paid_at=_utc_now() if body.payment_method == 'cash' else None,
        processed_by=current_user.id,
    )
    db.add(payment)
    await db.flush()

    if body.payment_method == 'cash':
        split.status = 'paid'
        split.paid_at = _utc_now()
        split.payment_id = payment.id
        split.row_version += 1

        tab.paid_amount = Decimal(str(tab.paid_amount)) + split_amount

        # Check if all splits paid → close tab
        all_paid = all(
            s.status == 'paid' or s.id == split_id
            for s in tab.splits
        )
        if all_paid:
            tab.status = 'paid'
            tab.closed_by = current_user.id
            tab.closed_at = _utc_now()
            for order in tab.orders:
                if order.status not in ('completed', 'cancelled'):
                    order.status = 'completed'
                    order.row_version += 1
    else:
        split.status = 'pending'
        split.payment_id = payment.id
        split.row_version += 1

    tab.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "pay_split", "split_id": str(split_id), "amount": float(split_amount), "method": body.payment_method},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id,
        message=f"Split '{split.label}' dibayar"
    )


# ── CANCEL TAB ──

@router.post("/{tab_id}/cancel", response_model=StandardResponse[TabResponse])
async def cancel_tab(
    request: Request,
    tab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status == 'paid':
        raise HTTPException(status_code=400, detail="Tab sudah dibayar, tidak bisa cancel")
    if tab.paid_amount and Decimal(str(tab.paid_amount)) > 0:
        raise HTTPException(status_code=400, detail="Ada split yang sudah dibayar, tidak bisa cancel seluruh tab")

    tab.status = 'cancelled'
    tab.closed_by = current_user.id
    tab.closed_at = _utc_now()
    tab.row_version += 1

    # Unlink orders from tab
    for order in tab.orders:
        order.tab_id = None

    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "cancel"},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Tab dibatalkan"
    )
