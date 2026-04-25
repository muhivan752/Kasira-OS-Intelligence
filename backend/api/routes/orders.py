from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text, func

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.product import Product
from backend.models.outlet import Outlet
from backend.models.outlet_tax_config import OutletTaxConfig
from backend.models.shift import Shift, ShiftStatus
from backend.models.tenant import Tenant
from backend.schemas.order import OrderCreate, OrderUpdateStatus, OrderResponse, OrderStatus, OrderType
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.models.reservation import Table
from backend.services.stock_service import deduct_stock, restore_stock_on_cancel
from backend.services.ingredient_stock_service import deduct_ingredients_for_product, restore_ingredients_on_cancel
from backend.models.event import Event

router = APIRouter()

@router.post("/", response_model=StandardResponse[OrderResponse])
async def create_order(
    request: Request,
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new order and deduct stock (Transaction-First Simple Stock).
    """
    if not order_in.items:
        raise HTTPException(status_code=400, detail="Order harus memiliki minimal 1 item")

    # Validasi outlet milik tenant user
    outlet = (await db.execute(
        select(Outlet).where(
            Outlet.id == order_in.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=403, detail="Outlet tidak ditemukan atau bukan milik tenant Anda")

    # Validasi table untuk dine_in
    # Pro: wajib pilih meja. Starter: boleh dine-in tanpa meja.
    tenant_stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant_check = (await db.execute(tenant_stmt)).scalar_one_or_none()
    is_pro = getattr(getattr(tenant_check, "subscription_tier", None), "value", "starter") in ("pro", "business", "enterprise")

    table = None
    if order_in.order_type == OrderType.dine_in:
        if not order_in.table_id and is_pro:
            raise HTTPException(status_code=400, detail="Dine-in order wajib pilih meja")
        table = (await db.execute(
            select(Table).where(
                Table.id == order_in.table_id,
                Table.outlet_id == order_in.outlet_id,
                Table.is_active == True,
                Table.deleted_at.is_(None),
            ).with_for_update()
        )).scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
        if table.status not in ("available", "occupied"):
            raise HTTPException(status_code=400, detail=f"Meja {table.name} sedang {table.status}, tidak bisa dipakai")
    elif order_in.table_id:
        # Takeaway/delivery should not have table
        order_in.table_id = None

    # Validasi shift terbuka
    if order_in.shift_session_id:
        shift = (await db.execute(
            select(Shift).where(
                Shift.id == order_in.shift_session_id,
                Shift.outlet_id == order_in.outlet_id,
                Shift.status == ShiftStatus.open,
                Shift.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=400, detail="Shift tidak ditemukan atau sudah ditutup. Buka shift terlebih dahulu.")
    else:
        # Cek ada shift terbuka untuk user ini
        open_shift = (await db.execute(
            select(Shift).where(
                Shift.outlet_id == order_in.outlet_id,
                Shift.user_id == current_user.id,
                Shift.status == ShiftStatus.open,
                Shift.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if not open_shift:
            raise HTTPException(status_code=400, detail="Belum ada shift terbuka. Silakan buka shift terlebih dahulu.")

    # 1. Create Order
    result = await db.execute(text("SELECT nextval('order_display_seq')"))
    display_number = result.scalar()
    order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{display_number}"

    # Calculate totals server-side from items (fallback if client sends 0)
    from decimal import Decimal as D
    from backend.models.outlet_tax_config import OutletTaxConfig

    calculated_subtotal = sum(item.total_price for item in order_in.items)
    subtotal = order_in.subtotal if order_in.subtotal > 0 else calculated_subtotal
    discount = order_in.discount_amount or D(0)

    # Discount override check: if discount > 20% of subtotal, require permission
    discount_approved_by = None
    if discount > 0 and subtotal > 0:
        discount_pct = (discount / subtotal) * 100
        if discount_pct > 20 and not current_user.is_superuser:
            from backend.models.role import Role
            role = await db.get(Role, current_user.role_id) if current_user.role_id else None
            if not role or not role.can_discount_override:
                raise HTTPException(
                    status_code=403,
                    detail=f"Diskon {discount_pct:.0f}% melebihi batas 20%. Perlu persetujuan supervisor."
                )
            discount_approved_by = current_user.id

    # Auto-calculate tax & service charge from outlet config
    tax_config = (await db.execute(
        select(OutletTaxConfig).where(
            OutletTaxConfig.outlet_id == order_in.outlet_id,
            OutletTaxConfig.deleted_at == None,
        )
    )).scalar_one_or_none()

    taxable_amount = subtotal - discount  # tax calculated after discount

    if tax_config and tax_config.pb1_enabled and tax_config.tax_pct > 0:
        if tax_config.tax_inclusive:
            # Harga sudah termasuk pajak — extract tax from subtotal
            tax = taxable_amount - (taxable_amount / D(str(1 + tax_config.tax_pct / 100)))
        else:
            tax = taxable_amount * D(str(tax_config.tax_pct / 100))
        tax = tax.quantize(D("1"))  # round to whole rupiah
    else:
        tax = order_in.tax_amount or D(0)

    if tax_config and tax_config.service_charge_enabled and tax_config.service_charge_pct > 0:
        service_charge = taxable_amount * D(str(tax_config.service_charge_pct / 100))
        service_charge = service_charge.quantize(D("1"))
    else:
        service_charge = order_in.service_charge_amount or D(0)

    if tax_config and tax_config.tax_inclusive:
        # Total = subtotal (sudah termasuk tax) + service charge - discount
        calculated_total = subtotal + service_charge - discount
    else:
        calculated_total = subtotal + service_charge + tax - discount

    total_amount = calculated_total if (tax_config and (tax_config.pb1_enabled or tax_config.service_charge_enabled)) else (order_in.total_amount if order_in.total_amount > 0 else calculated_total)

    order = Order(
        outlet_id=order_in.outlet_id,
        shift_session_id=order_in.shift_session_id,
        customer_id=order_in.customer_id,
        table_id=order_in.table_id,
        user_id=order_in.user_id or current_user.id,
        order_number=order_number,
        display_number=display_number,
        order_type=order_in.order_type,
        subtotal=subtotal,
        service_charge_amount=service_charge,
        tax_amount=tax,
        discount_amount=discount,
        total_amount=total_amount,
        notes=order_in.notes,
        discount_approved_by=discount_approved_by,
        status=OrderStatus.pending
    )
    db.add(order)
    await db.flush() # To get order.id

    # 2. Process Order Items and Deduct Stock — reuse tenant_check dari guard di atas
    raw_tier = getattr(tenant_check, "subscription_tier", "starter") or "starter" if tenant_check else "starter"
    tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)

    sm = getattr(outlet, 'stock_mode', 'simple')
    stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')

    # Sort items by product_id → konsisten lock order across concurrent orders → no deadlock.
    sorted_items = sorted(order_in.items, key=lambda i: str(i.product_id))

    for item_in in sorted_items:
        # Fetch product to check stock
        product = await db.get(Product, item_in.product_id)
        if not product or product.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

        # Deduct stock — branch by outlet stock_mode
        if product.stock_enabled:
            if stock_mode == "recipe":
                await deduct_ingredients_for_product(
                    db,
                    product_id=product.id,
                    quantity=item_in.quantity,
                    outlet_id=order_in.outlet_id,
                    order_id=order.id,
                    user_id=current_user.id,
                    tier=tier,
                    product_name=product.name,
                )
            else:
                await deduct_stock(
                    db,
                    product=product,
                    quantity=item_in.quantity,
                    outlet_id=order_in.outlet_id,
                    order_id=order.id,
                    user_id=current_user.id,
                    tier=tier,
                )

        # Create Order Item
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_in.product_id,
            product_variant_id=item_in.product_variant_id,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            discount_amount=item_in.discount_amount,
            total_price=item_in.total_price,
            modifiers=item_in.modifiers,
            notes=item_in.notes
        )
        db.add(order_item)

    # Set table status to occupied if dine-in
    if table and table.status == "available":
        await db.execute(
            update(Table).where(Table.id == table.id)
            .values(status="occupied", row_version=Table.row_version + 1)
        )

    # Append order.created event to event store
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type="order.created",
        event_data={
            "order_id": str(order.id),
            "outlet_id": str(order.outlet_id),
            "order_number": order_number,
            "display_number": display_number,
            "order_type": order_in.order_type,
            "subtotal": float(subtotal),
            "tax_amount": float(tax),
            "service_charge": float(service_charge),
            "discount_amount": float(discount),
            "total_amount": float(total_amount),
            "item_count": len(order_in.items),
            "items": [
                {"product_id": str(i.product_id), "qty": i.quantity, "unit_price": float(i.unit_price)}
                for i in order_in.items
            ],
            "customer_id": str(order_in.customer_id) if order_in.customer_id else None,
            "table_id": str(order_in.table_id) if order_in.table_id else None,
            "source": "pos",
        },
        event_metadata={
            "tier": tier,
            "user_id": str(current_user.id),
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    ))

    # 1. Pastikan commit sudah selesai
    await db.commit()

    # Re-set RLS tenant context: SET LOCAL resets after commit (new implicit tx).
    # Without this, selectinload query below gets blocked by RLS policy.
    await db.execute(text(f"SET LOCAL app.current_tenant_id = '{current_user.tenant_id}'"))

    # 2. Ambil ulang data Order — selectinload di semua level (wajib untuk async)
    query = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
        .where(Order.id == order.id)
    )

    result = await db.execute(query)
    order_loaded = result.scalar_one()

    # 3. Jalankan Audit Log
    await log_audit(
        db=db,
        action="CREATE",
        entity="order",
        entity_id=order_loaded.id,
        after_state={
            "order_number": order_loaded.order_number, 
            "total_amount": float(order_loaded.total_amount)
        },
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    # 4. Return Response
    return StandardResponse(
        success=True,
        message="Order created successfully",
        data=OrderResponse.model_validate(order_loaded),
        request_id=request.state.request_id
    )

@router.get("/", response_model=StandardResponse[List[OrderResponse]])
async def read_orders(
    request: Request,
    outlet_id: UUID,
    status: Optional[OrderStatus] = None,
    table_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve orders.
    """
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(
        Order.outlet_id == outlet_id,
        Order.deleted_at.is_(None)
    )

    if status:
        query = query.where(Order.status == status)
    if table_id:
        query = query.where(Order.table_id == table_id)
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at <= end_dt)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    # Fetch payment info for these orders in one query
    order_ids = [o.id for o in orders]
    payment_map: dict = {}
    if order_ids:
        pay_result = await db.execute(
            select(Payment.order_id, Payment.payment_method, Payment.status).where(
                Payment.order_id.in_(order_ids),
                Payment.deleted_at.is_(None),
            )
        )
        for row in pay_result.all():
            payment_map[row.order_id] = {
                "payment_method": row.payment_method,
                "payment_status": row.status,
            }

    order_responses = []
    for o in orders:
        resp = OrderResponse.model_validate(o)
        pay_info = payment_map.get(o.id)
        if pay_info:
            resp.payment_method = pay_info["payment_method"]
            resp.payment_status = pay_info["payment_status"]
        order_responses.append(resp)

    return StandardResponse(
        success=True,
        data=order_responses,
        request_id=request.state.request_id
    )

@router.get("/{order_id}", response_model=StandardResponse[OrderResponse])
async def read_order(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get order by ID.
    """
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order or order.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
        
    return StandardResponse(
        success=True,
        data=OrderResponse.model_validate(order),
        request_id=request.state.request_id
    )

@router.put("/{order_id}/status", response_model=StandardResponse[OrderResponse])
async def update_order_status(
    request: Request,
    order_id: UUID,
    status_in: OrderUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update order status with optimistic locking.
    """
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order or order.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    # Use client row_version if provided and matches, otherwise use server's current version
    current_rv = order.row_version
    if status_in.row_version > 0 and status_in.row_version != current_rv:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order telah diubah, silakan refresh"
        )

    before_state = {"status": order.status}

    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.row_version == current_rv)
        .values(
            status=status_in.status,
            row_version=Order.row_version + 1,
            updated_at=datetime.now(timezone.utc)
        )
        .returning(Order)
    )
    
    result = await db.execute(stmt)
    updated_order = result.scalar_one_or_none()
    
    if not updated_order:
        raise HTTPException(status_code=409, detail="Concurrent update detected.")

    # Restore stock when order cancelled
    if status_in.status == OrderStatus.cancelled:
        # Get tenant tier and outlet stock_mode
        outlet = await db.get(Outlet, order.outlet_id)
        tier = "starter"
        stock_mode = "simple"
        if outlet:
            sm = getattr(outlet, 'stock_mode', 'simple')
            stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')
            if outlet.tenant_id:
                tenant = await db.get(Tenant, outlet.tenant_id)
                if tenant:
                    tier = getattr(tenant, 'subscription_tier', None) or "starter"
                    if hasattr(tier, 'value'):
                        tier = tier.value
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

    # Recalculate tab totals when order cancelled (tab excludes cancelled orders)
    if status_in.status == OrderStatus.cancelled and order.tab_id:
        from backend.models.tab import Tab
        tab_q = select(Tab).where(Tab.id == order.tab_id, Tab.deleted_at.is_(None))
        tab_result = await db.execute(tab_q)
        linked_tab = tab_result.scalar_one_or_none()
        if linked_tab and linked_tab.status not in ('paid', 'cancelled'):
            # Recalculate from remaining non-cancelled orders
            remaining_q = select(Order).where(
                Order.tab_id == linked_tab.id,
                Order.deleted_at.is_(None),
                Order.status != 'cancelled',
            )
            remaining_result = await db.execute(remaining_q)
            remaining_orders = remaining_result.scalars().all()
            linked_tab.subtotal = sum(o.subtotal for o in remaining_orders)
            linked_tab.tax_amount = sum(o.tax_amount for o in remaining_orders)
            linked_tab.service_charge_amount = sum(o.service_charge_amount for o in remaining_orders)
            linked_tab.discount_amount = sum(o.discount_amount for o in remaining_orders)
            linked_tab.total_amount = sum(o.total_amount for o in remaining_orders)
            linked_tab.row_version += 1

    # Release table when order completed/cancelled (if no other active orders on same table).
    # GUARD: kalau order belongs to active tab (open/asking_bill/splitting), JANGAN
    # release table — tab era "order completed" = kitchen done, BUKAN "all paid".
    # Table harus tetap occupied sampai tab.status = paid/cancelled. Tanpa guard ini,
    # split-bill scenario release table prematurely saat kitchen mark order done.
    if status_in.status in (OrderStatus.completed, OrderStatus.cancelled) and order.table_id:
        skip_release = False
        if order.tab_id:
            from backend.models.tab import Tab
            tab_check = await db.execute(
                select(Tab.status).where(
                    Tab.id == order.tab_id,
                    Tab.deleted_at.is_(None),
                )
            )
            tab_status_val = tab_check.scalar_one_or_none()
            if tab_status_val is not None:
                tab_status_str = tab_status_val.value if hasattr(tab_status_val, 'value') else str(tab_status_val)
                if tab_status_str not in ('paid', 'cancelled'):
                    skip_release = True

        if not skip_release:
            active_orders = (await db.execute(
                select(func.count(Order.id)).where(
                    Order.table_id == order.table_id,
                    Order.id != order.id,
                    Order.status.notin_(["completed", "cancelled"]),
                    Order.deleted_at.is_(None),
                )
            )).scalar() or 0
            if active_orders == 0:
                await db.execute(
                    update(Table).where(Table.id == order.table_id)
                    .values(status="available", row_version=Table.row_version + 1)
                )

    # Append order lifecycle event to event store
    status_val = status_in.status.value if hasattr(status_in.status, 'value') else str(status_in.status)
    event_type = f"order.{status_val}"
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type=event_type,
        event_data={
            "order_id": str(order.id),
            "outlet_id": str(order.outlet_id),
            "order_number": order.order_number,
            "from_status": before_state["status"].value if hasattr(before_state["status"], 'value') else str(before_state["status"]),
            "to_status": status_val,
            "total_amount": float(order.total_amount),
            "order_type": order.order_type,
            "item_count": len(order.items),
            "table_id": str(order.table_id) if order.table_id else None,
            "customer_id": str(order.customer_id) if order.customer_id else None,
        },
        event_metadata={
            "user_id": str(current_user.id),
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    ))

    await db.commit()

    # Reload items for response (selectinload product to avoid MissingGreenlet on product_name)
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(Order.id == order_id)
    result = await db.execute(query)
    updated_order_loaded = result.scalar_one()

    # Audit log
    await log_audit(
        db=db,
        action="UPDATE_STATUS",
        entity="order",
        entity_id=updated_order.id,
        before_state=before_state,
        after_state={"status": updated_order.status},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    
    return StandardResponse(
        success=True,
        data=OrderResponse.model_validate(updated_order_loaded),
        request_id=request.state.request_id,
        message="Order status updated successfully"
    )


@router.get("/{order_id}/receipt", response_model=StandardResponse[dict])
async def get_order_receipt(
    request: Request,
    order_id: UUID,
    payment_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Return structured receipt data untuk reprint di mobile/POS.
    Flutter konsumsi JSON ini lalu rebuild ESC/POS bytes via buildReceipt().
    Offline fallback: Flutter bisa rebuild dari drift DB lokal.

    Optional ?payment_id=... — kalau diset, return SUBSET receipt:
    cuma items yg `paid_payment_id == payment_id` (untuk struk per ad-hoc payment).
    Subset totals di-recompute dari items yg ke-include + payment record yg match.
    Tanpa param → existing full-receipt behavior (backward compat).
    """
    # Load order + items (+ product untuk fallback nama item)
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(Order.id == order_id, Order.deleted_at.is_(None))
    order = (await db.execute(query)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    # Tenant scoping via outlet
    outlet = await db.get(Outlet, order.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Order bukan milik tenant Anda")

    # Determine target payment + items subset
    if payment_id:
        payment = await db.get(Payment, payment_id)
        if not payment or payment.outlet_id != outlet.id:
            raise HTTPException(status_code=404, detail="Payment tidak ditemukan")
        filtered_items = [i for i in order.items if i.paid_payment_id == payment_id]
        if not filtered_items:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada item terkait payment ini di order"
            )
        is_subset = True
    else:
        # Latest payment untuk method, amount_paid, change
        payment = (await db.execute(
            select(Payment)
            .where(Payment.order_id == order.id, Payment.deleted_at.is_(None))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        filtered_items = list(order.items)
        is_subset = False

    # Tax config (NPWP + custom receipt footer)
    tax_cfg = (await db.execute(
        select(OutletTaxConfig).where(OutletTaxConfig.outlet_id == outlet.id)
    )).scalar_one_or_none()

    # Format tanggal WIB (sama seperti WhatsApp receipt)
    from datetime import timezone as tz, timedelta
    wib = tz(timedelta(hours=7))
    date_time = order.created_at.astimezone(wib).strftime("%d/%m/%Y %H:%M") if order.created_at else "-"

    # Payment method label human-readable (match WA receipt labels)
    method_label_map = {"cash": "Tunai", "qris": "QRIS", "card": "Kartu", "transfer": "Transfer"}
    payment_method_raw = payment.payment_method if payment else "cash"
    payment_method_label = method_label_map.get(payment_method_raw, payment_method_raw.upper())

    items = [
        {
            "name": item.product_name or (item.product.name if item.product else "Item"),
            "qty": item.quantity,
            "price": float(item.unit_price or 0),
            "notes": item.notes,
        }
        for item in filtered_items
    ]

    if is_subset:
        # Subset totals: re-compute dari filtered items
        subset_subtotal = sum((Decimal(str(it.total_price or 0)) for it in filtered_items), Decimal('0'))
        # Tax/service share proportional
        order_subtotal = Decimal(str(order.subtotal or 0)) or Decimal('1')
        tax_share = (Decimal(str(order.tax_amount or 0)) * subset_subtotal / order_subtotal).quantize(Decimal('0.01')) if order_subtotal > 0 else Decimal('0')
        service_share = (Decimal(str(order.service_charge_amount or 0)) * subset_subtotal / order_subtotal).quantize(Decimal('0.01')) if order_subtotal > 0 else Decimal('0')
        total_val = float(payment.amount_due) if payment else float(subset_subtotal + tax_share + service_share)
        subtotal_val = float(subset_subtotal)
        tax_val = float(tax_share)
        service_val = float(service_share)
        discount_val = 0.0
    else:
        total_val = float(order.total_amount or 0)
        subtotal_val = float(order.subtotal or 0)
        tax_val = float(order.tax_amount or 0)
        service_val = float(order.service_charge_amount or 0)
        discount_val = float(order.discount_amount or 0)

    data = {
        "outlet_name": outlet.name or "Kasira",
        "outlet_address": outlet.address or "",
        "order_number": str(order.display_number),
        "date_time": date_time,
        "items": items,
        "subtotal": subtotal_val,
        "service_charge": service_val,
        "tax": tax_val,
        "discount": discount_val,
        "total": total_val,
        "payment_method": payment_method_label,
        "amount_paid": float(payment.amount_paid or total_val) if payment else total_val,
        "change_amount": float(payment.change_amount or 0) if payment else 0.0,
        "tax_number": tax_cfg.tax_number if tax_cfg else None,
        "custom_footer": tax_cfg.receipt_footer if tax_cfg else None,
        "is_subset": is_subset,
    }

    return StandardResponse(
        success=True,
        data=data,
        request_id=request.state.request_id,
    )
