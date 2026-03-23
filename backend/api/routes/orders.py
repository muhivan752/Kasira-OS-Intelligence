from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.schemas.order import OrderCreate, OrderUpdateStatus, OrderResponse, OrderStatus
from backend.schemas.response import StandardResponse
from backend.models.audit_log import log_audit

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

    # 1. Create Order
    result = await db.execute(text("SELECT nextval('order_display_seq')"))
    display_number = result.scalar()
    order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{display_number}"
    
    order = Order(
        outlet_id=order_in.outlet_id,
        shift_session_id=order_in.shift_session_id,
        customer_id=order_in.customer_id,
        table_id=order_in.table_id,
        user_id=order_in.user_id or current_user.id,
        order_number=order_number,
        display_number=display_number,
        order_type=order_in.order_type,
        subtotal=order_in.subtotal,
        service_charge_amount=order_in.service_charge_amount,
        tax_amount=order_in.tax_amount,
        discount_amount=order_in.discount_amount,
        total_amount=order_in.total_amount,
        notes=order_in.notes,
        status=OrderStatus.pending
    )
    db.add(order)
    await db.flush() # To get order.id

    # 2. Process Order Items and Deduct Stock
    for item_in in order_in.items:
        # Fetch product to check stock
        product = await db.get(Product, item_in.product_id)
        if not product or product.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

        # Deduct stock if enabled
        if product.stock_enabled:
            if product.stock_qty < item_in.quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stok {product.name} tidak mencukupi. Tersedia: {product.stock_qty}"
                )
            
            new_stock = product.stock_qty - item_in.quantity
            is_active = product.is_active
            
            # Auto-hide if stock hits 0
            if new_stock <= 0 and product.stock_auto_hide:
                is_active = False
                
            # Update product stock
            stmt = (
                update(Product)
                .where(Product.id == product.id, Product.row_version == product.row_version)
                .values(
                    stock_qty=new_stock,
                    is_active=is_active,
                    row_version=Product.row_version + 1
                )
            )
            result = await db.execute(stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=409, detail="Konflik data produk, coba lagi")

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

    await db.commit()
    
    # Refresh to load items
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    result = await db.execute(query)
    order_loaded = result.scalar_one()

    # Audit log
    await log_audit(
        db=db,
        action="CREATE",
        entity="order",
        entity_id=order.id,
        after_state={"order_number": order.order_number, "total_amount": float(order.total_amount)},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        request_id=request.state.request_id
    )

    return StandardResponse(
        success=True,
        data=OrderResponse.model_validate(order_loaded),
        request_id=request.state.request_id,
        message="Order created successfully"
    )

@router.get("/", response_model=StandardResponse[List[OrderResponse]])
async def read_orders(
    request: Request,
    outlet_id: UUID,
    status: Optional[OrderStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve orders.
    """
    query = select(Order).options(selectinload(Order.items)).where(
        Order.outlet_id == outlet_id,
        Order.deleted_at.is_(None)
    )
    
    if status:
        query = query.where(Order.status == status)
        
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
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
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
            row_version=Order.row_version + 1
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
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data=OrderResponse.model_validate(updated_order_loaded),
        request_id=request.state.request_id,
        message="Order status updated successfully"
    )
