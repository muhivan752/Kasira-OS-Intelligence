from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=0)
    image_url: Optional[str] = None
    is_active: bool = True
    stock_enabled: bool = False
    stock_qty: int = Field(0, ge=0)
    stock_low_threshold: int = Field(5, ge=0)
    stock_auto_hide: bool = True
    sku: Optional[str] = None
    barcode: Optional[str] = None
    is_subscription: bool = False

class ProductCreate(ProductBase):
    brand_id: UUID
    category_id: Optional[UUID] = None

class ProductUpdate(BaseModel):
    category_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    stock_enabled: Optional[bool] = None
    stock_qty: Optional[int] = Field(None, ge=0)
    stock_low_threshold: Optional[int] = Field(None, ge=0)
    stock_auto_hide: Optional[bool] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    is_subscription: Optional[bool] = None
    row_version: int

class ProductResponse(ProductBase):
    id: UUID
    brand_id: UUID
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    order_count: int
    sold_today: int
    sold_total: int
    last_restock_at: Optional[datetime] = None
    row_version: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def price(self) -> Decimal:
        """Alias base_price → price untuk kompatibilitas Flutter & storefront."""
        return self.base_price

    @computed_field
    @property
    def stock(self) -> int:
        """Alias stock_qty → stock untuk kompatibilitas storefront."""
        return self.stock_qty

    model_config = ConfigDict(from_attributes=True)
