from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class ConnectOutlet(BaseModel):
    __tablename__ = "connect_outlets"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    channel = Column(ENUM('whatsapp', 'gofood', 'grabfood', 'shopeefood', 'tiktok', 'instagram', 'other', name='connect_channel', create_type=False), nullable=False)
    external_store_id = Column(String, nullable=False)
    is_active = Column(Boolean(), server_default='true', nullable=False)
    config = Column(JSONB(astext_type=Text()), nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

class ConnectOrder(BaseModel):
    __tablename__ = "connect_orders"

    connect_outlet_id = Column(UUID(as_uuid=True), ForeignKey('connect_outlets.id', ondelete='CASCADE'), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='SET NULL'), nullable=True)
    external_order_id = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False, unique=True)
    status = Column(ENUM('pending', 'accepted', 'rejected', 'processing', 'ready', 'completed', 'cancelled', 'failed', name='connect_order_status', create_type=False), server_default='pending', nullable=False)
    raw_payload = Column(JSONB(astext_type=Text()), nullable=False)
    error_message = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    order = relationship("Order")
