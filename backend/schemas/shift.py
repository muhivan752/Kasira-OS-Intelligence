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

class ShiftWithActivitiesResponse(ShiftResponse):
    activities: List[CashActivityResponse] = []
