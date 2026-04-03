from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import BaseModel


class CustomerPoints(BaseModel):
    __tablename__ = "customer_points"
    __table_args__ = (
        UniqueConstraint('customer_id', 'outlet_id', name='uq_customer_points_customer_outlet'),
        CheckConstraint('balance >= 0', name='chk_customer_points_balance'),
        CheckConstraint('lifetime_earned >= 0', name='chk_customer_points_lifetime'),
    )

    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    balance = Column(Integer, server_default='0', nullable=False)
    lifetime_earned = Column(Integer, server_default='0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)


class PointTransaction(BaseModel):
    __tablename__ = "point_transactions"
    __table_args__ = (
        UniqueConstraint('order_id', 'type', name='uq_point_transactions_order_type'),
        CheckConstraint("type IN ('earn', 'redeem')", name='chk_point_transactions_type'),
        CheckConstraint('points > 0', name='chk_point_transactions_points'),
    )

    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='SET NULL'), nullable=True)
    type = Column(String(20), nullable=False)  # earn / redeem
    points = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
