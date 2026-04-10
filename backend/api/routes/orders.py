from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone, date
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.outlet import Outlet
from backend.models.shift import Shift, ShiftStatus
from backend.models.tenant import Tenant
from backend.schemas.order import OrderCreate, OrderUpdateStatus, OrderResponse, OrderStatus
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.stock_service import deduct_stock

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
    calculated_subtotal = sum(item.total_price for item in order_in.items)
    subtotal = order_in.subtotal if order_in.subtotal > 0 else calculated_subtotal
    service_charge = order_in.service_charge_amount or D(0)
    tax = order_in.tax_amount or D(0)
    discount = order_in.discount_amount or D(0)
    calculated_total = subtotal + service_charge + tax - discount
    total_amount = order_in.total_amount if order_in.total_amount > 0 else calculated_total

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
        status=OrderStatus.pending
    )
    db.add(order)
    await db.flush() # To get order.id

    # 2. Process Order Items and Deduct Stock
    # Fetch tenant once (bukan per item)
    tenant_stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()
    tier = str(getattr(tenant, "subscription_tier", "starter") or "starter").lower()

    for item_in in order_in.items:
        # Fetch product to check stock
        product = await db.get(Product, item_in.product_id)
        if not product or product.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

        # Deduct stock via event-sourced stock service (Starter: transaction-first)
        if product.stock_enabled:
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

    # 1. Pastikan commit sudah selesai
    await db.commit()

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
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at <= end_dt)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return StandardResponse(
        success=True,
        data=[OrderResponse.model_validate(o) for o in orders],
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
        
    if order.row_version != status_in.row_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order telah diubah, silakan refresh"
        )
        
    before_state = {"status": order.status}
    
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.row_version == status_in.row_version)
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
        
    await db.commit()
    
    # Reload items for response
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
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
