import enum
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel, utc_now

class ShiftStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    # "Hitung nanti": laci dijeda buat dihitung belakangan, laci baru langsung
    # jalan. Nggak nerima transaksi baru, tapi masih bisa ditutup (dihitung).
    paused = "paused"

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

    # Shift otomatis (mig 097). Yang perlu dipegang:
    #  - opened_by: 'manual' (kasir tekan Buka Kasir) | 'auto' (transaksi pertama)
    #  - closed_reason: 'manual' | 'auto_cutoff' (04.00 waktu outlet) |
    #    'auto_migration' (bersih-bersih 097) | 'auto_stale' (>20 jam saat
    #    kasir buka baru)
    #  - counted_at: NULL = kasnya BELUM dihitung. Ini yang membedakan "ditutup
    #    sistem" dari "ditutup dan dihitung" — jangan pernah nulis
    #    ending_cash = 0 buat shift yang nggak dihitung, itu klaim palsu.
    opened_by = Column(String(16), default="manual", server_default="manual", nullable=False)
    closed_reason = Column(String(24), nullable=True)
    counted_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    # Profil Ketat (mig 099): laci dikunci ke kasir ini. NULL = laci bersama.
    locked_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    outlet = relationship("Outlet")
    user = relationship("User", foreign_keys=[user_id])
    activities = relationship("CashActivity", back_populates="shift", cascade="all, delete-orphan")

class CashActivity(BaseModel):
    __tablename__ = "cash_activities"

    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(Enum(CashActivityType, name="cash_activity_type", create_type=False), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255), nullable=False)
    row_version = Column(Integer, default=0, nullable=False)

    shift = relationship("Shift", back_populates="activities")
