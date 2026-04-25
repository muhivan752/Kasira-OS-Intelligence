from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    pending = 'pending'
    preparing = 'preparing'
    ready = 'ready'
    served = 'served'
    completed = 'completed'
    cancelled = 'cancelled'

class OrderType(str, Enum):
    dine_in = 'dine_in'
    takeaway = 'takeaway'
    delivery = 'delivery'

class OrderItemBase(BaseModel):
    product_id: UUID
    product_variant_id: Optional[UUID] = None
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_amount: Decimal = Field(0, ge=0)
    total_price: Decimal = Field(..., ge=0)
    modifiers: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: UUID
    order_id: UUID
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    paid_payment_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

class OrderBase(BaseModel):
    outlet_id: UUID
    shift_session_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    table_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    order_type: OrderType = OrderType.dine_in
    subtotal: Decimal = Field(0, ge=0)
    service_charge_amount: Decimal = Field(0, ge=0)
    tax_amount: Decimal = Field(0, ge=0)
    discount_amount: Decimal = Field(0, ge=0)
    total_amount: Decimal = Field(0, ge=0)
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdateStatus(BaseModel):
    status: OrderStatus
    row_version: int

class OrderResponse(OrderBase):
    id: UUID
    order_number: str
    display_number: int
    status: OrderStatus
    row_version: int
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
