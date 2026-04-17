from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class PaymentRefund(BaseModel):
    __tablename__ = "payment_refunds"

    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=False)

    status = Column(
        ENUM('pending', 'approved', 'rejected', 'completed', 'failed',
             name='refund_status', create_type=False),
        server_default='pending',
        nullable=False,
    )

    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reference_id = Column(String, nullable=True)
    metadata_payload = Column(JSONB(astext_type=Text()), nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    payment = relationship("Payment")
