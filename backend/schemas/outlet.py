from typing import Optional, Any
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

class OutletUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_open: Optional[bool] = None
    opening_hours: Optional[Any] = None
    cover_image_url: Optional[str] = None

class OutletPaymentSetup(BaseModel):
    xendit_business_id: str

class OutletPaymentSetupOwn(BaseModel):
    xendit_api_key: str  # merchant's own Xendit secret key

class OutletPaymentStatus(BaseModel):
    is_connected: bool
    mode: str = "none"  # "own_key" | "xenplatform" | "none"
    xendit_business_id: Optional[str] = None
    connected_at: Optional[datetime] = None

class OutletStockModeUpdate(BaseModel):
    stock_mode: str  # 'simple' | 'recipe'


class OutletInDBBase(OutletBase):
    id: UUID4
    slug: Optional[str] = None
    is_open: Optional[bool] = True
    opening_hours: Optional[Any] = None
    cover_image_url: Optional[str] = None
    stock_mode: str = "simple"
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
