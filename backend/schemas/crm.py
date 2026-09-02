from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.models.crm import SEGMENT_KEYS, TAG_COLORS


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    color: str = "violet"

    @field_validator("color")
    @classmethod
    def _c(cls, v):
        return v if v in TAG_COLORS else "violet"


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=40)
    color: Optional[str] = None
    row_version: int


class TagResponse(BaseModel):
    id: UUID
    name: str
    color: str
    row_version: int
    customer_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CustomerTagsSet(BaseModel):
    tag_ids: List[UUID] = []


class NoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)
    kind: str = "note"   # note | complaint

    @field_validator("kind")
    @classmethod
    def _k(cls, v):
        return v if v in ("note", "complaint") else "note"


class TimelineItem(BaseModel):
    id: UUID
    kind: str
    body: str
    ref_id: Optional[UUID] = None
    created_at: datetime
    created_by_name: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    birthday: Optional[date] = None
    wa_marketing_consent: Optional[bool] = None
    row_version: int


class SegmentCount(BaseModel):
    key: str
    label: str
    hint: str
    count: int


class SegmentSummary(BaseModel):
    segments: List[SegmentCount]
    updated_at: Optional[datetime] = None
    total_customers: int


# ── voucher ──

class VoucherCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=32)
    name: Optional[str] = Field(None, max_length=80)
    kind: str = "percent"
    value: Decimal = Field(..., gt=0)
    max_discount: Optional[Decimal] = Field(None, gt=0)
    min_purchase: Decimal = Field(Decimal("0"), ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    quota_total: Optional[int] = Field(None, ge=1)
    quota_per_customer: Optional[int] = Field(None, ge=1)
    segment: Optional[str] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _code(cls, v):
        v = "".join(ch for ch in v.strip().upper() if ch.isalnum() or ch in "-_")
        if len(v) < 2:
            raise ValueError("Kode voucher minimal 2 huruf/angka")
        return v

    @field_validator("kind")
    @classmethod
    def _kind(cls, v):
        if v not in ("percent", "amount"):
            raise ValueError("kind harus percent atau amount")
        return v

    @field_validator("segment")
    @classmethod
    def _seg(cls, v):
        if v in (None, ""):
            return None
        if v not in SEGMENT_KEYS:
            raise ValueError("Segmen tidak dikenal")
        return v


class VoucherUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=80)
    value: Optional[Decimal] = Field(None, gt=0)
    max_discount: Optional[Decimal] = None
    min_purchase: Optional[Decimal] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    quota_total: Optional[int] = None
    quota_per_customer: Optional[int] = None
    segment: Optional[str] = None
    is_active: Optional[bool] = None
    row_version: int


class VoucherResponse(BaseModel):
    id: UUID
    code: str
    name: Optional[str] = None
    kind: str
    value: Decimal
    max_discount: Optional[Decimal] = None
    min_purchase: Decimal
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    quota_total: Optional[int] = None
    quota_per_customer: Optional[int] = None
    segment: Optional[str] = None
    is_active: bool
    row_version: int
    created_at: datetime
    used_count: int = 0
    used_amount: Decimal = Decimal("0")


class VoucherValidate(BaseModel):
    code: str
    subtotal: Decimal = Field(..., ge=0)
    customer_id: Optional[UUID] = None


class VoucherValidateResult(BaseModel):
    valid: bool
    reason: Optional[str] = None
    voucher_id: Optional[UUID] = None
    code: Optional[str] = None
    name: Optional[str] = None
    discount_amount: Decimal = Decimal("0")


class VoucherRedeem(BaseModel):
    code: str
    order_id: UUID
    subtotal: Decimal = Field(..., ge=0)
    customer_id: Optional[UUID] = None
