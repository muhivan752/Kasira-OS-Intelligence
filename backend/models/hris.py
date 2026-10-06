from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from backend.models.base import BaseModel


class HrEmployee(BaseModel):
    __tablename__ = "hr_employees"
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    code = Column(String(30), nullable=False)
    name = Column(String(120), nullable=False)
    position = Column(String(100), nullable=False)
    phone = Column(String(40))
    started_on = Column(Date, nullable=False)
    ended_on = Column(Date)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text)
    row_version = Column(Integer, nullable=False, default=1)
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_hr_employee_tenant_id"),
        UniqueConstraint("tenant_id", "code", name="uq_hr_employee_code"),
        CheckConstraint("ended_on IS NULL OR ended_on >= started_on", name="ck_hr_employment_dates"),
        Index("ix_hr_employee_outlet", "tenant_id", "outlet_id"),
        Index("uq_hr_employee_user", "tenant_id", "user_id", unique=True,
              postgresql_where=text("user_id IS NOT NULL AND deleted_at IS NULL")),
    )


class HrSchedule(BaseModel):
    __tablename__ = "hr_schedules"
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id"), nullable=False)
    work_date = Column(Date, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)
    row_version = Column(Integer, nullable=False, default=1)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "employee_id"], ["hr_employees.tenant_id", "hr_employees.id"]),
        CheckConstraint("ends_at > starts_at AND ends_at <= starts_at + interval '24 hours'", name="ck_hr_schedule_window"),
        Index("ix_hr_schedule_period", "tenant_id", "outlet_id", "work_date"),
        Index("uq_hr_schedule_day", "tenant_id", "employee_id", "work_date", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )


class HrAttendance(BaseModel):
    __tablename__ = "hr_attendance"
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id"), nullable=False)
    work_date = Column(Date, nullable=False)
    status = Column(String(10), nullable=False)
    clock_in = Column(DateTime(timezone=True))
    clock_out = Column(DateTime(timezone=True))
    reason = Column(Text)
    source = Column(String(10), nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    row_version = Column(Integer, nullable=False, default=1)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "employee_id"], ["hr_employees.tenant_id", "hr_employees.id"]),
        CheckConstraint("(status = 'hadir' AND clock_in IS NOT NULL AND (clock_out IS NULL OR clock_out >= clock_in)) OR (status IN ('izin','sakit','cuti','libur') AND clock_in IS NULL AND clock_out IS NULL)", name="ck_hr_attendance_times"),
        CheckConstraint("source IN ('manual','self')", name="ck_hr_attendance_source"),
        Index("ix_hr_attendance_period", "tenant_id", "outlet_id", "work_date"),
        Index("uq_hr_attendance_day", "tenant_id", "employee_id", "work_date", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        Index("uq_hr_attendance_open", "tenant_id", "employee_id", unique=True,
              postgresql_where=text("deleted_at IS NULL AND status = 'hadir' AND clock_out IS NULL")),
    )
