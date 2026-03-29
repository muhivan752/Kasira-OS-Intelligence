from typing import Optional
from pydantic import BaseModel, UUID4
from datetime import datetime

class OutletBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = True
    tenant_id: UUID4
    brand_id: Optional[UUID4] = None

class OutletCreate(OutletBase):
    pass

class OutletUpdate(OutletBase):
    name: Optional[str] = None
    tenant_id: Optional[UUID4] = None

class OutletPaymentSetup(BaseModel):
    xendit_business_id: str

class OutletPaymentStatus(BaseModel):
    is_connected: bool
    xendit_business_id: Optional[str] = None
    connected_at: Optional[datetime] = None

class OutletInDBBase(OutletBase):
    id: UUID4
    row_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    xendit_business_id: Optional[str] = None
    xendit_connected_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Outlet(OutletInDBBase):
    pass
