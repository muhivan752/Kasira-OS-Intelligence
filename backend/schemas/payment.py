from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum

class PaymentMethod(str, Enum):
    cash = 'cash'
    qris = 'qris'
    card = 'card'
    transfer = 'transfer'

class PaymentStatus(str, Enum):
    pending = 'pending'
    paid = 'paid'
    partial = 'partial'
    expired = 'expired'
    cancelled = 'cancelled'
    refunded = 'refunded'
    failed = 'failed'

class PaymentBase(BaseModel):
    order_id: Optional[UUID] = None
    outlet_id: UUID
    invoice_id: Optional[UUID] = None
    shift_session_id: Optional[UUID] = None
    payment_method: PaymentMethod
    amount_due: Decimal = Field(..., ge=0)
    amount_paid: Decimal = Field(..., ge=0)
    change_amount: Decimal = Field(0, ge=0)
    reference_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    is_partial: bool = False

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: UUID
    status: PaymentStatus
    qris_url: Optional[str] = None
    qris_expired_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    refund_amount: Optional[Decimal] = None
    xendit_raw: Optional[Dict[str, Any]] = None
    processed_by: Optional[UUID] = None
    reconciled_at: Optional[datetime] = None
    row_version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ── Refund Schemas ────────────────────────────────────────────────────────────

class RefundStatus(str, Enum):
    pending = 'pending'
    approved = 'approved'
    rejected = 'rejected'
    completed = 'completed'
    failed = 'failed'

class RefundRequest(BaseModel):
    payment_id: UUID
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=500)

class RefundApproval(BaseModel):
    row_version: int

class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    amount: Decimal
    reason: str
    status: RefundStatus
    requested_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reference_id: Optional[str] = None
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
