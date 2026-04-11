from sqlalchemy import (
    Column, String, Integer, DateTime, Date, Time, Text,
    ForeignKey, Boolean, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Table(BaseModel):
    __tablename__ = "tables"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    capacity = Column(Integer, server_default='2', nullable=False)
    floor_section = Column(String(50), nullable=True)
    status = Column(
        ENUM('available', 'reserved', 'occupied', 'closed', name='table_status', create_type=False),
        server_default="'available'",
        nullable=False,
    )
    position_x = Column(String, nullable=True)
    position_y = Column(String, nullable=True)
    is_active = Column(Boolean, server_default='true', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    reservations = relationship("Reservation", back_populates="table")


class Reservation(BaseModel):
    __tablename__ = "reservations"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey('tables.id', ondelete='SET NULL'), nullable=True)

    # Booking details
    reservation_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    reservation_time = Column(DateTime(timezone=True), nullable=True)  # legacy
    guest_count = Column(Integer, nullable=False)

    # Customer info (denormalized)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)

    # Status
    status = Column(
        ENUM('pending', 'confirmed', 'seated', 'completed', 'cancelled', 'no_show',
             name='reservation_status', create_type=False),
        server_default='pending',
        nullable=False,
    )

    # Deposit
    deposit_amount = Column(Numeric(15, 2), nullable=True)
    deposit_payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='SET NULL'), nullable=True)

    # Meta
    source = Column(String(20), server_default='manual', nullable=False)
    notes = Column(Text, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    table = relationship("Table", back_populates="reservations")


class ReservationSettings(BaseModel):
    __tablename__ = "reservation_settings"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False, unique=True)
    is_enabled = Column(Boolean, server_default='false', nullable=False)
    slot_duration_minutes = Column(Integer, server_default='120', nullable=False)
    max_advance_days = Column(Integer, server_default='30', nullable=False)
    min_advance_hours = Column(Integer, server_default='2', nullable=False)
    require_deposit = Column(Boolean, server_default='false', nullable=False)
    deposit_amount = Column(Numeric(15, 2), server_default='0', nullable=False)
    auto_confirm = Column(Boolean, server_default='true', nullable=False)
    opening_hour = Column(Time, nullable=False)
    closing_hour = Column(Time, nullable=False)
    max_reservations_per_slot = Column(Integer, server_default='10', nullable=False)
    reminder_hours_before = Column(Integer, server_default='2', nullable=False)
