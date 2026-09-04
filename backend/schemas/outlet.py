from typing import Literal, Optional, Any, List
from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class OutletBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    is_active: Optional[bool] = True
    tenant_id: UUID4
    brand_id: Optional[UUID4] = None

class OutletCreate(OutletBase):
    pass

class OutletUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    # Token Fonnte toko (promo WA dari nomor sendiri). Write-only — response cuma bilang terpasang/nggak.
    fonnte_token: Optional[str] = None
    is_open: Optional[bool] = None
    opening_hours: Optional[Any] = None
    cover_image_url: Optional[str] = None
    # Profil kas (mig 098). 'ketat' baru punya perilaku di gelombang 3.
    shift_mode: Optional[Literal['ringan', 'standar', 'ketat']] = None
    # Pesanan online (mig 101)
    online_orders_enabled: Optional[bool] = None
    online_notify_owner_wa: Optional[bool] = None
    online_auto_cancel_minutes: Optional[int] = Field(default=None, ge=3, le=60)
    kitchen_mode: Optional[Literal['off', 'display', 'print']] = None
    # Metode bayar (mig 103). Daftar dibersihkan server: tunai selalu ada,
    # yang nggak dikenal dibuang.
    payment_methods: Optional[List[str]] = None
    qris_static_image_url: Optional[str] = Field(default=None, max_length=500)
    bank_name: Optional[str] = Field(default=None, max_length=60)
    bank_account_number: Optional[str] = Field(default=None, max_length=40)
    bank_account_name: Optional[str] = Field(default=None, max_length=80)
    directory_listed: Optional[bool] = None
    # Delivery gelombang 1 (mig 106)
    delivery_enabled: Optional[bool] = None
    delivery_fee_base: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    delivery_fee_per_km: Optional[float] = Field(default=None, ge=0, le=100_000)
    delivery_free_km: Optional[float] = Field(default=None, ge=0, le=100)
    delivery_min_order: Optional[float] = Field(default=None, ge=0, le=100_000_000)
    delivery_radius_km: Optional[float] = Field(default=None, ge=0, le=200)
    business_hours: Optional[Any] = None
    hours_mode: Optional[Literal['manual', 'schedule']] = None

class OutletPaymentSetup(BaseModel):
    xendit_business_id: str

class OutletPaymentSetupOwn(BaseModel):
    xendit_api_key: str  # merchant's own Xendit secret key
    xendit_callback_token: Optional[str] = None  # webhook verify token (BYOK Phase 2 — store, actual per-merchant verify deferred sampai 1 BYOK merchant onboard)

class OutletPaymentStatus(BaseModel):
    is_connected: bool
    mode: str = "none"  # "own_key" | "xenplatform" | "none"
    xendit_business_id: Optional[str] = None
    connected_at: Optional[datetime] = None
    has_callback_token: bool = False  # info-only, gak expose token value

class OutletStockModeUpdate(BaseModel):
    stock_mode: str  # 'simple' | 'recipe'

class OutletLocationUpdate(BaseModel):
    latitude: float
    longitude: float


class OutletInDBBase(OutletBase):
    wa_connected: bool = False
    id: UUID4
    slug: Optional[str] = None
    is_open: Optional[bool] = True
    opening_hours: Optional[Any] = None
    cover_image_url: Optional[str] = None
    stock_mode: str = "simple"
    shift_mode: str = "ringan"
    online_orders_enabled: bool = True
    online_notify_owner_wa: bool = True
    online_auto_cancel_minutes: int = 10
    kitchen_mode: str = "off"
    payment_methods: List[str] = ["cash", "qris"]
    # 'xendit' kalau toko punya kunci Xendit, kalau nggak 'manual' (kasir
    # konfirmasi sendiri). Dihitung dari model, bukan disimpan.
    qris_channel: str = "manual"
    directory_listed: bool = True
    delivery_enabled: bool = True
    delivery_fee_base: float = 0
    delivery_fee_per_km: float = 0
    delivery_free_km: float = 0
    delivery_min_order: float = 0
    delivery_radius_km: Optional[float] = None
    business_hours: Optional[Any] = None
    hours_mode: str = "manual"
    qris_static_image_url: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
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
    tax_number: Optional[str] = None
    receipt_footer: Optional[str] = None
    row_version: int = 0

    class Config:
        from_attributes = True


class TaxConfigUpdate(BaseModel):
    pb1_enabled: Optional[bool] = None
    tax_pct: Optional[float] = None
    service_charge_enabled: Optional[bool] = None
    service_charge_pct: Optional[float] = None
    tax_inclusive: Optional[bool] = None
    tax_number: Optional[str] = Field(default=None, max_length=30)
    receipt_footer: Optional[str] = Field(default=None, max_length=200)
    # Optimistic lock (Golden Rule #29-30). Wajib kalau config sudah ada.
    expected_row_version: Optional[int] = None


class OutletWhatsAppSetup(BaseModel):
    """Token Fonnte toko. Kosong/None = putus."""
    fonnte_token: Optional[str] = None
