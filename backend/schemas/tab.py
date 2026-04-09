from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TabStatus(str, Enum):
    open = 'open'
    asking_bill = 'asking_bill'
    splitting = 'splitting'
    paid = 'paid'
    cancelled = 'cancelled'


class SplitMethod(str, Enum):
    full = 'full'
    equal = 'equal'
    per_item = 'per_item'
    custom = 'custom'


class TabSplitStatus(str, Enum):
    unpaid = 'unpaid'
    pending = 'pending'
    paid = 'paid'


# ── Tab CRUD ──

class TabCreate(BaseModel):
    outlet_id: UUID
    table_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    guest_count: int = Field(1, ge=1, le=50)
    notes: Optional[str] = None


class TabAddOrder(BaseModel):
    """Link an existing order to this tab."""
    order_id: UUID


class TabSplitResponse(BaseModel):
    id: UUID
    tab_id: UUID
    payment_id: Optional[UUID] = None
    label: str
    amount: Decimal
    status: TabSplitStatus
    item_ids: Optional[List[UUID]] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    row_version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TabResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    table_id: Optional[UUID] = None
    tab_number: str
    customer_name: Optional[str] = None
    guest_count: int
    subtotal: Decimal
    tax_amount: Decimal
    service_charge_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal = Decimal('0')
    split_method: Optional[SplitMethod] = None
    status: TabStatus
    opened_by: Optional[UUID] = None
    closed_by: Optional[UUID] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    notes: Optional[str] = None
    row_version: int
    created_at: datetime
    updated_at: datetime
    splits: List[TabSplitResponse] = []
    order_ids: List[UUID] = []

    model_config = ConfigDict(from_attributes=True)


# ── Split Bill ──

class SplitEqualRequest(BaseModel):
    """Split total rata per jumlah orang."""
    num_people: int = Field(..., ge=2, le=50)
    row_version: int


class SplitItemAssignment(BaseModel):
    """Assign item(s) ke satu orang."""
    label: str  # Nama tamu, e.g. "Andi"
    item_ids: List[UUID]  # order_item IDs


class SplitPerItemRequest(BaseModel):
    """Split per item — assign setiap item ke orang tertentu."""
    assignments: List[SplitItemAssignment]
    row_version: int


class SplitCustomAmount(BaseModel):
    """Custom amount per orang."""
    label: str
    amount: Decimal = Field(..., gt=0)


class SplitCustomRequest(BaseModel):
    """Split custom — kasir tentukan nominal per orang."""
    splits: List[SplitCustomAmount]
    row_version: int


# ── Pay Split ──

class PaySplitRequest(BaseModel):
    """Bayar 1 split (1 orang)."""
    payment_method: str = Field(..., pattern='^(cash|qris|card|transfer)$')
    amount_paid: Decimal = Field(..., gt=0)
    idempotency_key: Optional[str] = None
    row_version: int
