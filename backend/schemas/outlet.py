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
    midtrans_server_key: str
    midtrans_client_key: str
    midtrans_is_production: bool = False

class OutletPaymentStatus(BaseModel):
    is_connected: bool
    midtrans_client_key: Optional[str] = None
    midtrans_is_production: bool = False
    connected_at: Optional[datetime] = None

class OutletInDBBase(OutletBase):
    id: UUID4
    row_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    midtrans_client_key: Optional[str] = None
    midtrans_is_production: bool = False
    midtrans_connected_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Outlet(OutletInDBBase):
    pass
