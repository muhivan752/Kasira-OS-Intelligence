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

class OutletLocationUpdate(BaseModel):
    latitude: float
    longitude: float


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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None

    class Config:
        from_attributes = True

class Outlet(OutletInDBBase):
    pass


# ── Tax Config ──────────────────────────────────────────

class TaxConfigResponse(BaseModel):
    pb1_enabled: bool = False
    tax_pct: float = 10.0
    service_charge_enabled: bool = False
    service_charge_pct: float = 0.0
    tax_inclusive: bool = False

    class Config:
        from_attributes = True


class TaxConfigUpdate(BaseModel):
    pb1_enabled: Optional[bool] = None
    tax_pct: Optional[float] = None
    service_charge_enabled: Optional[bool] = None
    service_charge_pct: Optional[float] = None
    tax_inclusive: Optional[bool] = None
