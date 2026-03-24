import uuid
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class Order(BaseModel):
    __tablename__ = "orders"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    shift_session_id = Column(UUID(as_uuid=True), ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='SET NULL'), nullable=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey('tables.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    order_number = Column(String, nullable=False)
    display_number = Column(Integer, nullable=False) # Sequence handled by DB
    
    status = Column(ENUM('pending', 'preparing', 'ready', 'served', 'completed', 'cancelled', name='order_status', create_type=False), server_default='pending', nullable=False)
    order_type = Column(ENUM('dine_in', 'takeaway', 'delivery', name='order_type', create_type=False), server_default='dine_in', nullable=False)
    
    subtotal = Column(Numeric(12, 2), server_default='0', nullable=False)
    service_charge_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    tax_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    discount_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    total_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    outlet = relationship("Outlet", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    # user, customer, table, shift relationships can be added later if needed

class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id = Column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    
    from sqlalchemy.dialects.postgresql import JSONB
    modifiers = Column(JSONB(astext_type=Text()), nullable=True)
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
