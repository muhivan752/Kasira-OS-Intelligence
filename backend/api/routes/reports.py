from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, date, time, timedelta
from uuid import UUID
from typing import Any, Optional

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.shift import Shift, ShiftStatus
from backend.models.product import Product
from backend.schemas.response import StandardResponse

router = APIRouter()

@router.get("/daily", response_model=StandardResponse)
async def get_daily_report(
    request: Request,
    outlet_id: UUID,
    report_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    target_date = report_date or datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
    end_of_day = datetime.combine(target_date + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)

    # 1. Order stats (revenue, count, avg)
    # Filter: orders today, status != cancelled, paid
    order_query = select(
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue_today"),
        func.count(Order.id).label("order_count")
    ).where(
        Order.outlet_id == outlet_id,
        Order.created_at >= start_of_day,
        Order.created_at < end_of_day,
        Order.deleted_at.is_(None),
        Order.status != "cancelled",
        Order.id.in_(
            select(Payment.order_id).where(
                Payment.status == "paid",
                Payment.deleted_at.is_(None),
            )
        )
    )
    
    order_result = await db.execute(order_query)
    order_stats = order_result.first()
    
    revenue_today = float(order_stats.revenue_today) if order_stats else 0.0
    order_count = int(order_stats.order_count) if order_stats else 0
    avg_order_value = revenue_today / order_count if order_count > 0 else 0.0
    
    # 2. Top products
    top_products_query = select(
        Product.name,
        func.sum(OrderItem.quantity).label("sold"),
        func.sum(OrderItem.total_price).label("revenue")
    ).select_from(OrderItem).join(
        Order, OrderItem.order_id == Order.id
    ).join(
        Product, OrderItem.product_id == Product.id
    ).where(
        Order.outlet_id == outlet_id,
        Order.created_at >= start_of_day,
        Order.created_at < end_of_day,
        Order.deleted_at.is_(None),
        Product.deleted_at.is_(None),
        Order.status != "cancelled",
        Order.id.in_(
            select(Payment.order_id).where(
                Payment.status == "paid",
                Payment.deleted_at.is_(None),
            )
        )
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5)
    
    top_products_result = await db.execute(top_products_query)
    top_products = [
        {
            "name": row.name,
            "sold": int(row.sold),
            "revenue": float(row.revenue)
        }
        for row in top_products_result.all()
    ]
    
    # 3. Payment breakdown
    payment_query = select(
        Payment.payment_method,
        func.sum(Payment.amount_paid).label("total")
    ).select_from(Payment).join(
        Order, Payment.order_id == Order.id
    ).where(
        Order.outlet_id == outlet_id,
        Order.created_at >= start_of_day,
        Order.created_at < end_of_day,
        Order.deleted_at.is_(None),
        Payment.deleted_at.is_(None),
        Order.status != "cancelled",
        Payment.status == "paid"
    ).group_by(
        Payment.payment_method
    )
    
    payment_result = await db.execute(payment_query)
    payment_breakdown = {"cash": 0.0, "qris": 0.0}
    for row in payment_result.all():
        method = row.payment_method.lower() if row.payment_method else "unknown"
        if method in payment_breakdown:
            payment_breakdown[method] = float(row.total)
        else:
            payment_breakdown[method] = float(row.total)
            
    # 4. Shift status
    shift_query = select(Shift).where(
        Shift.outlet_id == outlet_id,
        Shift.status == ShiftStatus.open
    ).limit(1)
    
    shift_result = await db.execute(shift_query)
    active_shift = shift_result.scalar_one_or_none()
    shift_status = "open" if active_shift else "closed"
    
    data = {
        "revenue_today": revenue_today,
        "order_count": order_count,
        "avg_order_value": avg_order_value,
        "top_products": top_products,
        "payment_breakdown": payment_breakdown,
        "shift_status": shift_status
    }
    
    return StandardResponse(
        success=True,
        message="Daily report retrieved successfully",
        data=data,
        request_id=request.state.request_id,
    )
