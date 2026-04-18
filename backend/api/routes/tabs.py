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
  POST   /tabs/{tab_id}/move-table  → pindah meja
  POST   /tabs/{tab_id}/merge       → gabung tab lain ke tab ini
  POST   /tabs/{tab_id}/request-bill → minta bill (ubah status ke asking_bill)
  GET    /tabs/by-table/{table_id}  → get open tab for a table (for storefront)
  GET    /tabs/{tab_id}/items       → list items in tab (for per-item split UI)
"""
from typing import Any, List, Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.api.deps import get_current_user, require_pro_tier
from backend.models.user import User
from backend.models.tab import Tab, TabSplit
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.reservation import Table
from backend.schemas.tab import (
    TabCreate, TabAddOrder, TabResponse,
    SplitEqualRequest, SplitPerItemRequest, SplitCustomRequest,
    PaySplitRequest, MoveTableRequest, MergeTabRequest,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.tab_service import (
    utc_now as _utc_now,
    tab_event as _tab_event,
    tab_response as _tab_response,
    get_tab_or_404 as _get_tab_or_404,
    recalculate_tab as _recalculate_tab,
    find_active_shift as _find_active_shift,
)

router = APIRouter(dependencies=[Depends(require_pro_tier)])


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

    # Mark table as occupied
    if body.table_id:
        tbl = await db.get(Table, body.table_id)
        if tbl and tbl.status == 'available':
            tbl.status = 'occupied'
            tbl.row_version += 1

    await db.flush()

    _tab_event(db, tab, "tab.opened", {"customer_name": body.customer_name}, current_user.id)
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
        .options(selectinload(Tab.splits), selectinload(Tab.orders), selectinload(Tab.table))
        .where(Tab.outlet_id == outlet_id, Tab.deleted_at.is_(None))
        .execution_options(populate_existing=True)
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

    _tab_event(db, tab, "tab.order_added", {"order_id": str(body.order_id)}, current_user.id)
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

    _tab_event(db, tab, "tab.split", {"method": "equal", "num_people": body.num_people}, current_user.id)
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

    _tab_event(db, tab, "tab.split", {"method": "per_item", "assignments": len(body.assignments)}, current_user.id)
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

    _tab_event(db, tab, "tab.split", {"method": "custom", "splits": len(body.splits)}, current_user.id)
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
        tab_id=tab.id,
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
        # Release table
        if tab.table_id:
            tbl = await db.get(Table, tab.table_id)
            if tbl and tbl.status == 'occupied':
                tbl.status = 'available'
                tbl.row_version += 1

    tab.row_version += 1

    _tab_event(db, tab, "tab.paid", {
        "method": "full", "amount": float(total),
        "payment_method": body.payment_method, "payment_id": str(payment.id),
        "order_ids": [str(o.id) for o in tab.orders],
    }, current_user.id)
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
        tab_id=tab.id,
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
            # Release table
            if tab.table_id:
                tbl = await db.get(Table, tab.table_id)
                if tbl and tbl.status == 'occupied':
                    tbl.status = 'available'
                    tbl.row_version += 1
    else:
        split.status = 'pending'
        split.payment_id = payment.id
        split.row_version += 1

    tab.row_version += 1

    _tab_event(db, tab, "tab.split_paid", {
        "split_id": str(split_id), "split_label": split.label,
        "amount": float(split_amount), "payment_method": body.payment_method,
        "payment_id": str(payment.id), "all_paid": tab.status == 'paid',
    }, current_user.id)
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

    # Release table
    if tab.table_id:
        tbl = await db.get(Table, tab.table_id)
        if tbl and tbl.status == 'occupied':
            tbl.status = 'available'
            tbl.row_version += 1

    # Unlink orders from tab
    unlinked_order_ids = [str(o.id) for o in tab.orders]
    for order in tab.orders:
        order.tab_id = None

    _tab_event(db, tab, "tab.cancelled", {"unlinked_orders": unlinked_order_ids}, current_user.id)
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


# ── MOVE TABLE (pindah meja) ──

@router.post("/{tab_id}/move-table", response_model=StandardResponse[TabResponse])
async def move_table(
    request: Request,
    tab_id: UUID,
    body: MoveTableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")
    if tab.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    # Validate new table
    new_table = (await db.execute(
        select(Table).where(
            Table.id == body.new_table_id,
            Table.is_active == True,
            Table.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not new_table:
        raise HTTPException(status_code=404, detail="Meja tujuan tidak ditemukan")
    if new_table.outlet_id != tab.outlet_id:
        raise HTTPException(status_code=400, detail="Meja bukan milik outlet ini")

    # Check target table doesn't have another open tab
    existing_tab = (await db.execute(
        select(Tab).where(
            Tab.table_id == body.new_table_id,
            Tab.status.in_(['open', 'asking_bill', 'splitting']),
            Tab.id != tab.id,
            Tab.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing_tab:
        raise HTTPException(status_code=400, detail=f"Meja {new_table.name} sudah ada tab aktif ({existing_tab.tab_number})")

    old_table_id = tab.table_id
    old_table_name = tab.table.name if tab.table else None

    # Release old table
    if tab.table_id:
        old_table = await db.get(Table, tab.table_id)
        if old_table and old_table.status == 'occupied':
            old_table.status = 'available'
            old_table.row_version += 1

    # Assign new table
    tab.table_id = body.new_table_id
    tab.row_version += 1

    # Mark new table as occupied
    if new_table.status == 'available':
        new_table.status = 'occupied'
        new_table.row_version += 1

    # Update table_id on linked orders too
    for order in tab.orders:
        if order.status not in ('completed', 'cancelled'):
            order.table_id = body.new_table_id

    _tab_event(db, tab, "tab.moved_table", {
        "from_table": old_table_name, "to_table": new_table.name,
        "from_table_id": str(old_table_id) if old_table_id else None,
        "to_table_id": str(body.new_table_id),
    }, current_user.id)
    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "move_table", "from": old_table_name, "to": new_table.name},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id,
        message=f"Pindah ke Meja {new_table.name}"
    )


# ── MERGE TAB (gabung tab) ──

@router.post("/{tab_id}/merge", response_model=StandardResponse[TabResponse])
async def merge_tab(
    request: Request,
    tab_id: UUID,
    body: MergeTabRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Gabung source_tab ke tab ini. Semua order dari source pindah ke target."""
    if tab_id == body.source_tab_id:
        raise HTTPException(status_code=400, detail="Tidak bisa gabung tab ke dirinya sendiri")

    target = await _get_tab_or_404(db, tab_id, lock=True)
    if target.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab tujuan sudah ditutup")
    if target.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    source = await _get_tab_or_404(db, body.source_tab_id, lock=True)
    if source.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sumber sudah ditutup")
    if source.paid_amount and Decimal(str(source.paid_amount)) > 0:
        raise HTTPException(status_code=400, detail="Tab sumber sudah ada pembayaran, tidak bisa digabung")

    # Move all orders from source to target
    for order in source.orders:
        order.tab_id = target.id
        # Update table_id to target's table
        if target.table_id and order.status not in ('completed', 'cancelled'):
            order.table_id = target.table_id

    # Update guest count
    target.guest_count += source.guest_count

    # Cancel source tab
    source.status = 'cancelled'
    source.closed_by = current_user.id
    source.closed_at = _utc_now()
    source.notes = (source.notes or '') + f' [Digabung ke {target.tab_number}]'
    source.row_version += 1

    # Release source table if it had one
    if source.table_id and source.table_id != target.table_id:
        src_table = await db.get(Table, source.table_id)
        if src_table and src_table.status == 'occupied':
            src_table.status = 'available'
            src_table.row_version += 1

    # Delete any existing splits on target (need to re-split after merge)
    for s in list(target.splits):
        await db.delete(s)
    target.split_method = None

    # Recalculate target totals
    await db.flush()
    await _recalculate_tab(db, target)
    target.row_version += 1

    _tab_event(db, target, "tab.merged", {
        "source_tab_id": str(source.id), "source_tab_number": source.tab_number,
        "new_guest_count": target.guest_count,
    }, current_user.id)
    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=target.id,
        after_state={
            "action": "merge_tab",
            "source_tab": source.tab_number,
            "new_total": float(target.total_amount),
            "new_guest_count": target.guest_count,
        },
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    target = await _get_tab_or_404(db, target.id)
    return StandardResponse(
        success=True, data=_tab_response(target),
        request_id=request.state.request_id,
        message=f"Tab {source.tab_number} digabung ke {target.tab_number}"
    )


# ── REQUEST BILL (minta bill) ──

@router.post("/{tab_id}/request-bill", response_model=StandardResponse[TabResponse])
async def request_bill(
    request: Request,
    tab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Ubah status tab ke asking_bill — customer minta bill."""
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status != 'open':
        raise HTTPException(status_code=400, detail=f"Tab status '{tab.status}', hanya tab open yang bisa minta bill")

    tab.status = 'asking_bill'
    tab.row_version += 1

    _tab_event(db, tab, "tab.asking_bill", {}, current_user.id)
    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={"action": "request_bill"},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id, message="Bill diminta"
    )


# ── GET TAB BY TABLE (for storefront/connect integration) ──

@router.get("/by-table/{table_id}", response_model=StandardResponse[Optional[TabResponse]])
async def get_tab_by_table(
    request: Request,
    table_id: UUID,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get open tab for a specific table. Scoped to outlet for security."""
    query = (
        select(Tab)
        .options(selectinload(Tab.splits), selectinload(Tab.orders), selectinload(Tab.table))
        .where(
            Tab.table_id == table_id,
            Tab.outlet_id == outlet_id,
            Tab.status.in_(['open', 'asking_bill', 'splitting']),
            Tab.deleted_at.is_(None),
        )
        .order_by(Tab.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    tab = result.scalar_one_or_none()

    return StandardResponse(
        success=True,
        data=_tab_response(tab) if tab else None,
        request_id=request.state.request_id,
    )


# ── GET TAB ITEMS (for per-item split UI) ──

@router.get("/{tab_id}/items", response_model=StandardResponse[List[dict]])
async def get_tab_items(
    request: Request,
    tab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all order items across orders in this tab. Used for per-item split assignment."""
    tab = await _get_tab_or_404(db, tab_id)
    if not tab.orders:
        return StandardResponse(success=True, data=[], request_id=request.state.request_id)

    order_ids = [o.id for o in tab.orders]
    items_q = (
        select(OrderItem)
        .options(selectinload(OrderItem.product))
        .where(
            OrderItem.order_id.in_(order_ids),
            OrderItem.deleted_at.is_(None),
        )
        .order_by(OrderItem.created_at)
    )
    result = await db.execute(items_q)
    items = result.scalars().all()

    data = [
        {
            "id": str(i.id),
            "order_id": str(i.order_id),
            "product_id": str(i.product_id) if i.product_id else None,
            "product_name": i.product.name if i.product else "Item",
            "quantity": i.quantity,
            "unit_price": float(i.unit_price),
            "total_price": float(i.total_price),
        }
        for i in items
    ]
    return StandardResponse(success=True, data=data, request_id=request.state.request_id)
