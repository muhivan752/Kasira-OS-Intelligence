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
from backend.models.outlet import Outlet
from backend.models.outlet_tax_config import OutletTaxConfig
from backend.schemas.tab import (
    TabCreate, TabAddOrder, TabResponse,
    SplitEqualRequest, SplitPerItemRequest, SplitCustomRequest,
    PaySplitRequest, PayItemsRequest, MoveTableRequest, MergeTabRequest,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.tab_service import (
    utc_now as _utc_now,
    tab_event as _tab_event,
    tab_response as _tab_response,
    get_tab_or_404 as _get_tab_or_404,
    recalculate_tab as _recalculate_tab,
    tab_remaining_after_items as _tab_remaining_after_items,
    compute_paid_items_total as _compute_paid_items_total,
    items_proportional_due as _items_proportional_due,
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
        .options(
            selectinload(Tab.splits),
            selectinload(Tab.orders).selectinload(Order.items),
            selectinload(Tab.table),
        )
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

    # Effective total = exclude items udah paid via ad-hoc + amount yg sudah di-split paid
    paid_items_total = _compute_paid_items_total(tab)
    effective_total = max(Decimal('0'), total - Decimal(str(tab.paid_amount or 0)) - paid_items_total)
    if effective_total <= 0:
        raise HTTPException(
            status_code=400,
            detail={"code": "ALREADY_FULLY_PAID", "message": "Semua sudah dibayar individual — tidak ada sisa untuk di-split"}
        )

    # Delete existing splits
    for s in list(tab.splits):
        await db.delete(s)

    per_person = (effective_total / body.num_people).quantize(Decimal('0.01'))
    remainder = effective_total - (per_person * body.num_people)

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

    _tab_event(db, tab, "tab.split", {"method": "equal", "num_people": body.num_people, "effective_total": float(effective_total)}, current_user.id)
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

    items_q = (
        select(OrderItem)
        .options(selectinload(OrderItem.product))
        .where(
            OrderItem.order_id.in_(order_ids),
            OrderItem.deleted_at.is_(None),
        )
    )
    items_result = await db.execute(items_q)
    all_items = {i.id: i for i in items_result.scalars().all()}

    # Validate all assigned item_ids exist + belum dibayar (ad-hoc paid items
    # gak boleh re-assigned ke split — double-pay risk)
    assigned_ids = set()
    for assignment in body.assignments:
        for item_id in assignment.item_ids:
            if item_id not in all_items:
                raise HTTPException(status_code=400, detail=f"Item {item_id} tidak ditemukan di tab ini")
            if all_items[item_id].paid_at is not None:
                item_name = all_items[item_id].product_name or 'Unknown'
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "ITEM_ALREADY_PAID",
                        "message": f"Item '{item_name}' sudah dibayar individual — tidak bisa di-assign ke split"
                    }
                )
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

    # Compute effective amount (subtract items udah paid via ad-hoc per-item)
    paid_items_total = _compute_paid_items_total(tab)
    effective_total = max(Decimal('0'), total - Decimal(str(tab.paid_amount or 0)) - paid_items_total)
    if effective_total <= 0:
        raise HTTPException(
            status_code=400,
            detail={"code": "ALREADY_FULLY_PAID", "message": "Semua sudah dibayar — tidak ada sisa untuk pay-full"}
        )

    # Guard: block payment if all underlying orders already auto-cancelled by system
    # (mirror payments.py cancelled-guard — prevents "ghost race" with stale_order_cleanup janitor)
    if tab.orders and all(
        (o.status.value if hasattr(o.status, 'value') else str(o.status)) == 'cancelled'
        for o in tab.orders
    ):
        raise HTTPException(
            status_code=400,
            detail="Order di tab ini sudah dibatalkan otomatis oleh sistem (stale cleanup) — silakan buat tab/order baru."
        )

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

    if body.payment_method == 'cash' and body.amount_paid < effective_total:
        raise HTTPException(status_code=400, detail="Nominal pembayaran kurang dari sisa tab")

    # Pick first order as payment anchor (or None)
    first_order_id = tab.orders[0].id if tab.orders else None

    change = max(Decimal('0'), Decimal(str(body.amount_paid)) - effective_total)
    payment = Payment(
        order_id=first_order_id,
        tab_id=tab.id,
        outlet_id=tab.outlet_id,
        shift_session_id=tab.shift_session_id,
        payment_method=body.payment_method,
        amount_due=effective_total,
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
        tab_id=tab.id, label="Bayar Penuh (Sisa)" if paid_items_total > 0 else "Bayar Penuh",
        amount=effective_total,
        payment_id=payment.id,
        status='paid' if body.payment_method == 'cash' else 'pending',
        paid_at=_utc_now() if body.payment_method == 'cash' else None,
    )
    db.add(full_split)

    if body.payment_method == 'cash':
        # Mark remaining unpaid items as paid via this payment (settle sisa)
        now = _utc_now()
        for o in tab.orders:
            ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
            if ostatus == 'cancelled' or o.deleted_at is not None:
                continue
            for item in (o.items or []):
                if item.deleted_at is None and item.paid_at is None:
                    item.paid_at = now
                    item.paid_payment_id = payment.id
                    item.row_version = (item.row_version or 0) + 1

        tab.paid_amount = Decimal(str(tab.paid_amount or 0)) + effective_total
        tab.status = 'paid'
        tab.split_method = 'full'
        tab.closed_by = current_user.id
        tab.closed_at = now
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

    # Guard: block payment if all underlying orders already auto-cancelled by system
    # (mirror payments.py cancelled-guard — prevents "ghost race" with stale_order_cleanup janitor)
    if tab.orders and all(
        (o.status.value if hasattr(o.status, 'value') else str(o.status)) == 'cancelled'
        for o in tab.orders
    ):
        raise HTTPException(
            status_code=400,
            detail="Order di tab ini sudah dibatalkan otomatis oleh sistem (stale cleanup) — silakan buat tab/order baru."
        )

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


# ── PAY ITEMS (warkop ad-hoc per-item payment) ──

async def _complete_order_if_fully_paid(db: AsyncSession, order: Order) -> None:
    """Helper: set order.status='completed' kalau semua items udah paid_at NOT NULL.

    Skip kalau order udah completed/cancelled. Skip table release karena
    parent tab guard (Rule #15) — tab.status closing logic yg trigger release.
    Order completion di sini cuma flip status biar reports/analytics akurat.
    """
    order_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
    if order_status in ('completed', 'cancelled'):
        return
    if not order.items:
        return
    all_paid = all(
        (item.deleted_at is not None) or (item.paid_at is not None)
        for item in order.items
    )
    if all_paid:
        order.status = 'completed'
        order.row_version = (order.row_version or 0) + 1


@router.post("/{tab_id}/pay-items", response_model=StandardResponse[TabResponse])
async def pay_items(
    request: Request,
    tab_id: UUID,
    body: PayItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Bayar items spesifik di tab (warkop ad-hoc).

    Validate: items belong to tab, semua unpaid (paid_at IS NULL), order parent
    tidak cancelled. Compute total dari items[].total_price → buat Payment record
    (is_partial=True), set items.paid_at + paid_payment_id, increment tab.paid_amount.

    Auto-trigger: kalau tab_remaining_after_items == 0 → tab.status='paid' + close
    + release table (Rule #15 guard preserved).
    """
    tab = await _get_tab_or_404(db, tab_id, lock=True)
    if tab.status in ('paid', 'cancelled'):
        raise HTTPException(status_code=400, detail="Tab sudah ditutup")

    # Ghost race guard — kalau semua orders cancelled by janitor
    if tab.orders and all(
        (o.status.value if hasattr(o.status, 'value') else str(o.status)) == 'cancelled'
        for o in tab.orders
    ):
        raise HTTPException(
            status_code=400,
            detail="Order di tab ini sudah dibatalkan otomatis oleh sistem (stale cleanup)."
        )

    # Build map item_id → (order, item) dari tab.orders.items, skip cancelled/deleted
    items_in_tab = {}
    for o in tab.orders:
        order_status = o.status.value if hasattr(o.status, 'value') else str(o.status)
        if order_status == 'cancelled' or o.deleted_at is not None:
            continue
        for it in (o.items or []):
            if it.deleted_at is None:
                items_in_tab[it.id] = (o, it)

    # Validate semua requested item_ids exist + unpaid
    target_items = []
    for iid in body.order_item_ids:
        pair = items_in_tab.get(iid)
        if pair is None:
            raise HTTPException(
                status_code=400,
                detail=f"Item {iid} tidak ditemukan di tab atau order sudah dibatalkan"
            )
        order, item = pair
        if item.paid_at is not None:
            item_name = item.product_name or 'Unknown'
            raise HTTPException(
                status_code=400,
                detail={"code": "ITEM_ALREADY_PAID", "message": f"Item '{item_name}' sudah dibayar sebelumnya"}
            )
        target_items.append((order, item))

    # Compute total dgn proportional tax + service charge share.
    # Mirror split_per_item logic + konsisten dgn compute_paid_items_total
    # (tab_service.py) — kalau diverge, tab gak close 'paid' walau semua
    # items lunas (tax/SC orphan stuck di remaining).
    items_subtotal = sum((Decimal(str(it.total_price or 0)) for _, it in target_items), Decimal('0'))
    total_due = _items_proportional_due(tab, items_subtotal)
    if total_due <= 0:
        raise HTTPException(status_code=400, detail="Total item Rp 0, tidak ada yg perlu dibayar")

    if body.payment_method == 'cash' and body.amount_paid < total_due:
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

    first_order_id = target_items[0][0].id if target_items else None
    change = max(Decimal('0'), Decimal(str(body.amount_paid)) - total_due)

    payment = Payment(
        order_id=first_order_id,
        tab_id=tab.id,
        outlet_id=tab.outlet_id,
        shift_session_id=tab.shift_session_id,
        payment_method=body.payment_method,
        amount_due=total_due,
        amount_paid=Decimal(str(body.amount_paid)),
        change_amount=change,
        status='paid' if body.payment_method == 'cash' else 'pending',
        idempotency_key=body.idempotency_key,
        is_partial=True,
        paid_at=_utc_now() if body.payment_method == 'cash' else None,
        processed_by=current_user.id,
    )
    db.add(payment)
    await db.flush()

    # Mark items paid (cash only — QRIS wait webhook update via xendit reconciliation)
    if body.payment_method == 'cash':
        now = _utc_now()
        affected_orders = set()
        for order, item in target_items:
            item.paid_at = now
            item.paid_payment_id = payment.id
            item.row_version = (item.row_version or 0) + 1
            affected_orders.add(id(order))

        # NOTE: SENGAJA gak increment tab.paid_amount di sini — items.paid_at
        # itu sendiri jadi source of truth untuk pay-items. tab_remaining_after_items
        # sum kedua kolom (tab.paid_amount + paid_via_items). Kalau increment dua-duanya
        # → double-count → tab close prematurely (bug ditemukan smoke test).
        # tab.paid_amount HANYA di-increment di pay_split / pay_full.

        # Auto-complete orders yg semua items paid
        completed_orders = []
        for order, _ in target_items:
            order_id_key = id(order)
            if order_id_key in affected_orders:
                # Process once per order
                affected_orders.discard(order_id_key)
                await _complete_order_if_fully_paid(db, order)
                if (order.status.value if hasattr(order.status, 'value') else str(order.status)) == 'completed':
                    completed_orders.append(order.id)

        # Close tab kalau semua sudah paid (via items + splits + tab.paid_amount)
        remaining = _tab_remaining_after_items(tab)
        if remaining <= Decimal('0.01'):  # tolerance
            tab.status = 'paid'
            tab.closed_by = current_user.id
            tab.closed_at = now
            for o in tab.orders:
                ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
                if ostatus not in ('completed', 'cancelled'):
                    o.status = 'completed'
                    o.row_version = (o.row_version or 0) + 1
            # Release table (Rule #15 guard sudah implicit — tab.status='paid' satisfies)
            if tab.table_id:
                tbl = await db.get(Table, tab.table_id)
                if tbl and tbl.status == 'occupied':
                    tbl.status = 'available'
                    tbl.row_version = (tbl.row_version or 0) + 1

    tab.row_version = (tab.row_version or 0) + 1

    _tab_event(db, tab, "tab.items_paid", {
        "item_ids": [str(it.id) for _, it in target_items],
        "item_count": len(target_items),
        "amount": float(total_due),
        "payment_method": body.payment_method,
        "payment_id": str(payment.id),
        "tab_closed": tab.status == 'paid',
    }, current_user.id)
    await log_audit(
        db=db, action="UPDATE", entity="tab", entity_id=tab.id,
        after_state={
            "action": "pay_items",
            "item_ids": [str(it.id) for _, it in target_items],
            "amount": float(total_due),
            "method": body.payment_method,
        },
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    tab = await _get_tab_or_404(db, tab.id)
    return StandardResponse(
        success=True, data=_tab_response(tab),
        request_id=request.state.request_id,
        message=f"{len(target_items)} item dibayar (Rp {int(total_due):,})".replace(',', '.')
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
        .options(
            selectinload(Tab.splits),
            selectinload(Tab.orders).selectinload(Order.items),
            selectinload(Tab.table),
        )
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
            "paid_at": i.paid_at.isoformat() if i.paid_at else None,
            "paid_payment_id": str(i.paid_payment_id) if i.paid_payment_id else None,
            "notes": i.notes,
        }
        for i in items
    ]
    return StandardResponse(success=True, data=data, request_id=request.state.request_id)


# ── GET SPLIT RECEIPT (struk per orang yg udah bayar split) ──

@router.get("/{tab_id}/splits/{split_id}/receipt", response_model=StandardResponse[dict])
async def get_split_receipt(
    request: Request,
    tab_id: UUID,
    split_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Return structured receipt data per split untuk dicetak ke 1 orang yg udah bayar.
    Mirror pattern get_order_receipt — Flutter konsumsi JSON ini lalu rebuild ESC/POS
    bytes via buildSplitReceipt().

    Banner struk: "BAYAR PATUNGAN" + "Tamu X dari N".
    Footer: status outstanding tab ("Bill belum lunas, X orang lagi" atau "Bill LUNAS").
    """
    tab = await _get_tab_or_404(db, tab_id)

    # Find split
    split = next((s for s in tab.splits if s.id == split_id), None)
    if not split:
        raise HTTPException(status_code=404, detail="Split tidak ditemukan")

    # Tenant scoping via outlet
    outlet = await db.get(Outlet, tab.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tab bukan milik tenant Anda")

    # Payment record (kalau split.payment_id ada)
    payment = None
    if split.payment_id:
        payment = await db.get(Payment, split.payment_id)

    # Tax config
    tax_cfg = (await db.execute(
        select(OutletTaxConfig).where(OutletTaxConfig.outlet_id == outlet.id)
    )).scalar_one_or_none()

    # Format tanggal WIB
    from datetime import timezone as tz, timedelta
    wib = tz(timedelta(hours=7))
    paid_at = split.paid_at or _utc_now()
    date_time = paid_at.astimezone(wib).strftime("%d/%m/%Y %H:%M")

    # Position "Tamu X dari N" — sort splits by created_at biar deterministic
    sorted_splits = sorted(tab.splits, key=lambda s: s.created_at)
    position = next((idx + 1 for idx, s in enumerate(sorted_splits) if s.id == split_id), 0)
    total_splits = len(sorted_splits)

    # Outstanding info
    paid_count = sum(1 for s in tab.splits if s.status == 'paid')
    unpaid_count = total_splits - paid_count
    outstanding = max(Decimal('0'), Decimal(str(tab.total_amount)) - Decimal(str(tab.paid_amount)))
    is_tab_paid = (tab.status == 'paid') or (unpaid_count == 0)

    # Payment method label
    method_label_map = {"cash": "Tunai", "qris": "QRIS", "card": "Kartu", "transfer": "Transfer"}
    payment_method_raw = payment.payment_method if payment else "cash"
    payment_method_label = method_label_map.get(payment_method_raw, payment_method_raw.upper())

    data = {
        "outlet_name": outlet.name or "Kasira",
        "outlet_address": outlet.address or "",
        "tax_number": tax_cfg.tax_number if tax_cfg else None,
        "custom_footer": tax_cfg.receipt_footer if tax_cfg else None,
        "date_time": date_time,
        "tab_number": tab.tab_number,
        "tab_total": float(tab.total_amount or 0),
        "split_label": split.label,
        "split_amount": float(split.amount or 0),
        "split_position": position,
        "split_total_count": total_splits,
        "payment_method": payment_method_label,
        "amount_paid": float(payment.amount_paid) if payment else float(split.amount or 0),
        "change_amount": float(payment.change_amount) if payment else 0.0,
        "is_tab_paid": is_tab_paid,
        "outstanding_amount": float(outstanding),
        "outstanding_count": unpaid_count,
    }

    return StandardResponse(
        success=True,
        data=data,
        request_id=request.state.request_id,
    )
