from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from backend.schemas.customer_workspace import normalize_phone
from backend.schemas.account import EmployeeLoginSetup


class Write(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    client_request_id: UUID
    row_version: int | None = Field(default=None, ge=1)


class EmployeeSave(Write):
    name: str = Field(min_length=1, max_length=120)
    position: str = Field(min_length=1, max_length=100)
    outlet_id: UUID
    user_id: UUID | None = None
    phone: str | None = Field(default=None, max_length=40)
    started_on: date
    ended_on: date | None = None
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=2000)
    account: EmployeeLoginSetup | None = None

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value):
        return normalize_phone(value)

    @model_validator(mode="after")
    def dates(self):
        if self.ended_on and self.ended_on < self.started_on:
            raise ValueError("Tanggal selesai kerja harus sesudah tanggal mulai")
        return self


class ScheduleSave(Write):
    employee_id: UUID
    outlet_id: UUID
    starts_at: datetime
    ends_at: datetime
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Waktu harus menyertakan zona waktu outlet")
        return value


class AttendanceSave(Write):
    employee_id: UUID
    outlet_id: UUID
    work_date: date
    status: Literal["hadir", "izin", "sakit", "cuti", "libur"]
    clock_in: datetime | None = None
    clock_out: datetime | None = None
    reason: str | None = Field(default=None, max_length=1000)
    correction_reason: str | None = Field(default=None, max_length=500)

    @field_validator("clock_in", "clock_out")
    @classmethod
    def timezone_required(cls, value):
        if value and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Waktu harus menyertakan zona waktu outlet")
        return value


class RemoveEmployee(Write):
    row_version: int = Field(ge=1)


class VoidRecord(Write):
    reason: str = Field(min_length=1, max_length=500)


class Punch(Write):
    outlet_id: UUID
    action: Literal["in", "out"]
