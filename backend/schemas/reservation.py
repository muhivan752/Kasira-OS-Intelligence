from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import date, time, datetime
from decimal import Decimal
from enum import Enum


class ReservationStatus(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    seated = 'seated'
    completed = 'completed'
    cancelled = 'cancelled'
    no_show = 'no_show'


class ReservationSource(str, Enum):
    storefront = 'storefront'
    manual = 'manual'
    whatsapp = 'whatsapp'
    pos = 'pos'


# --- Table schemas ---

class TableCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    capacity: int = Field(2, ge=1, le=50)
    floor_section: Optional[str] = None
    is_active: bool = True


class TableUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1, le=50)
    floor_section: Optional[str] = None
    is_active: Optional[bool] = None


class TableResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    capacity: int
    floor_section: Optional[str] = None
    status: str
    is_active: bool
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Reservation schemas ---

class ReservationCreate(BaseModel):
    reservation_date: date
    start_time: time
    guest_count: int = Field(..., ge=1, le=100)
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    table_id: Optional[UUID] = None
    notes: Optional[str] = None
    source: ReservationSource = ReservationSource.manual


class StorefrontReservationCreate(BaseModel):
    reservation_date: date
    start_time: time
    guest_count: int = Field(..., ge=1, le=100)
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    notes: Optional[str] = None


class ReservationResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    table_id: Optional[UUID] = None
    table_name: Optional[str] = None
    table_floor_section: Optional[str] = None
    reservation_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    guest_count: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: ReservationStatus
    deposit_amount: Optional[Decimal] = None
    source: str
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlotInfo(BaseModel):
    time: time
    available: bool
    remaining_capacity: int
    tables_available: int


class AvailableSlotsResponse(BaseModel):
    date: date
    slots: List[SlotInfo]


# --- Reservation Settings schemas ---

class ReservationSettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    slot_duration_minutes: Optional[int] = Field(None, ge=30, le=480)
    max_advance_days: Optional[int] = Field(None, ge=1, le=365)
    min_advance_hours: Optional[int] = Field(None, ge=0, le=72)
    require_deposit: Optional[bool] = None
    deposit_amount: Optional[Decimal] = Field(None, ge=0)
    auto_confirm: Optional[bool] = None
    opening_hour: Optional[time] = None
    closing_hour: Optional[time] = None
    max_reservations_per_slot: Optional[int] = Field(None, ge=1, le=100)
    reminder_hours_before: Optional[int] = Field(None, ge=1, le=48)


class ReservationSettingsResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    is_enabled: bool
    slot_duration_minutes: int
    max_advance_days: int
    min_advance_hours: int
    require_deposit: bool
    deposit_amount: Decimal
    auto_confirm: bool
    opening_hour: time
    closing_hour: time
    max_reservations_per_slot: int
    reminder_hours_before: int

    model_config = ConfigDict(from_attributes=True)
