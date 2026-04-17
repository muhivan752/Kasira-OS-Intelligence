from sqlalchemy import (
    Column, String, Integer, Boolean, Float,
    ForeignKey,
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
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    is_active = Column(Boolean, server_default='true', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    reservations = relationship("Reservation", back_populates="table")
