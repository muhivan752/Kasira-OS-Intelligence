import enum
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel, utc_now

class ShiftStatus(str, enum.Enum):
    open = "open"
    closed = "closed"

class CashActivityType(str, enum.Enum):
    income = "income"
    expense = "expense"

class Shift(BaseModel):
    __tablename__ = "shifts"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(ShiftStatus, name="shift_status", create_type=False), default=ShiftStatus.open, nullable=False)
    start_time = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    starting_cash = Column(Numeric(12, 2), default=0, nullable=False)
    ending_cash = Column(Numeric(12, 2), nullable=True)
    expected_ending_cash = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, default=0, nullable=False)

    outlet = relationship("Outlet")
    user = relationship("User")
    activities = relationship("CashActivity", back_populates="shift", cascade="all, delete-orphan")

class CashActivity(BaseModel):
    __tablename__ = "cash_activities"

    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(Enum(CashActivityType, name="cash_activity_type", create_type=False), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255), nullable=False)
    row_version = Column(Integer, default=0, nullable=False)

    shift = relationship("Shift", back_populates="activities")
