from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from backend.models.base import BaseModel


class Table(BaseModel):
    __tablename__ = "tables"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    capacity = Column(Integer, server_default='2', nullable=False)
    status = Column(
        ENUM('available', 'reserved', 'occupied', 'closed', name='table_status', create_type=False),
        server_default="'available'",
        nullable=False,
    )
    position_x = Column(String, nullable=True)
    position_y = Column(String, nullable=True)
    is_active = Column(String, server_default='true', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)


class Reservation(BaseModel):
    __tablename__ = "reservations"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    table_id = Column(UUID(as_uuid=True), ForeignKey('tables.id', ondelete='SET NULL'), nullable=True)
    reservation_time = Column(DateTime(timezone=True), nullable=False)
    guest_count = Column(Integer, nullable=False)
    status = Column(
        ENUM('pending', 'confirmed', 'cancelled', 'completed', name='reservation_status', create_type=False),
        server_default='pending',
        nullable=False,
    )
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)
