import uuid
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Tab(BaseModel):
    __tablename__ = "tabs"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    table_id = Column(UUID(as_uuid=True), ForeignKey('tables.id', ondelete='SET NULL'), nullable=True)
    shift_session_id = Column(UUID(as_uuid=True), ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True)

    tab_number = Column(String, nullable=False)
    customer_name = Column(String, nullable=True)
    guest_count = Column(Integer, server_default='1', nullable=False)

    subtotal = Column(Numeric(12, 2), server_default='0', nullable=False)
    tax_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    service_charge_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    discount_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    total_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    paid_amount = Column(Numeric(12, 2), server_default='0', nullable=False)

    split_method = Column(ENUM('full', 'equal', 'per_item', 'custom', name='split_method', create_type=False), nullable=True)
    status = Column(ENUM('open', 'asking_bill', 'splitting', 'paid', 'cancelled', name='tab_status', create_type=False), server_default='open', nullable=False)

    opened_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    closed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="tab")
    splits = relationship("TabSplit", back_populates="tab", cascade="all, delete-orphan")
    outlet = relationship("Outlet")
    table = relationship("Table")


class TabSplit(BaseModel):
    __tablename__ = "tab_splits"

    tab_id = Column(UUID(as_uuid=True), ForeignKey('tabs.id', ondelete='CASCADE'), nullable=False)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='SET NULL'), nullable=True)

    label = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(ENUM('unpaid', 'pending', 'paid', name='tab_split_status', create_type=False), server_default='unpaid', nullable=False)

    item_ids = Column(JSONB(astext_type=Text()), nullable=True)

    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    tab = relationship("Tab", back_populates="splits")
    payment = relationship("Payment")
