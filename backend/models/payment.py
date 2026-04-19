import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class Payment(BaseModel):
    __tablename__ = "payments"

    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='CASCADE'), nullable=True)
    tab_id = Column(UUID(as_uuid=True), ForeignKey('tabs.id', ondelete='SET NULL'), nullable=True)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=True)  # FK to invoices (billing Pro feature, not mapped)
    shift_session_id = Column(UUID(as_uuid=True), ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True)
    
    payment_method = Column(ENUM('cash', 'qris', 'card', 'transfer', name='payment_method', create_type=False), nullable=False)
    
    amount_due = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), nullable=False)
    change_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    
    status = Column(ENUM('pending', 'paid', 'partial', 'expired', 'cancelled', 'refunded', 'failed', 'pending_manual_check', name='payment_status', create_type=False), server_default='pending', nullable=False)
    
    reference_id = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True)
    
    qris_url = Column(String, nullable=True)
    qris_expired_at = Column(DateTime(timezone=True), nullable=True)
    
    paid_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refund_amount = Column(Numeric(12, 2), nullable=True)
    
    xendit_raw = Column(JSONB(astext_type=Text()), nullable=True)
    processed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    
    is_partial = Column(Boolean, server_default='false', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    order = relationship("Order", back_populates="payments")
    tab = relationship("Tab")
    outlet = relationship("Outlet")
    # user = relationship("User")
