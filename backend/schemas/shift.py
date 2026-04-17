from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from backend.models.shift import ShiftStatus, CashActivityType

class CashActivityBase(BaseModel):
    activity_type: CashActivityType
    amount: float
    description: str

class CashActivityCreate(CashActivityBase):
    pass

class CashActivityResponse(CashActivityBase):
    id: UUID
    shift_id: UUID
    row_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ShiftBase(BaseModel):
    starting_cash: float
    notes: Optional[str] = None

class ShiftCreate(ShiftBase):
    pass

class ShiftClose(BaseModel):
    ending_cash: float
    notes: Optional[str] = None

class ShiftResponse(ShiftBase):
    id: UUID
    outlet_id: UUID
    user_id: UUID
    status: ShiftStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    ending_cash: Optional[float] = None
    expected_ending_cash: Optional[float] = None
    row_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CashPaymentSummary(BaseModel):
    id: UUID
    order_id: Optional[UUID] = None
    display_number: Optional[int] = None
    amount: float
    change_amount: float = 0
    net_amount: float  # amount - change
    payment_method: str
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ShiftWithActivitiesResponse(ShiftResponse):
    activities: List[CashActivityResponse] = []
    cash_payments: List[CashPaymentSummary] = []
    total_cash_sales: float = 0
    total_qris_sales: float = 0
    variance: Optional[float] = None  # ending_cash - expected_ending_cash
    variance_status: Optional[str] = None  # 'balanced', 'surplus', 'deficit'
