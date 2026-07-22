from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=0)
    buy_price: Optional[Decimal] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_active: bool = True
    stock_enabled: bool = False
    stock_qty: int = Field(0, ge=0)
    stock_low_threshold: int = Field(5, ge=0)
    stock_auto_hide: bool = True
    sku: Optional[str] = None
    barcode: Optional[str] = None
    is_subscription: bool = False

class ProductVariantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    # SELISIH dari base_price, bukan harga akhir. Boleh negatif (size kecil
    # lebih murah) — makanya sengaja TIDAK ada ge=0 di sini.
    price_adjustment: Decimal = Decimal(0)
    is_active: bool = True
    sort_order: int = 0


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=40)
    price_adjustment: Optional[Decimal] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    row_version: int


class ProductVariantResponse(ProductVariantBase):
    id: UUID
    product_id: UUID
    row_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductVariantBulkSet(BaseModel):
    """Ganti seluruh daftar varian satu produk dalam sekali kirim.

    Form produk di dashboard itu satu tombol Simpan — pemilik nambah "Dingin",
    hapus "Large", ubah harga "Panas", lalu simpan. Kalau tiap baris dikirim
    sebagai request POST/PUT/DELETE sendiri-sendiri, gagal di tengah bikin
    daftar varian setengah jadi dan pemiliknya nggak tahu yang mana yang masuk.
    Satu endpoint = satu transaksi.
    """
    variants: list[ProductVariantCreate] = []


class ProductCreate(ProductBase):
    brand_id: UUID
    category_id: Optional[UUID] = None
    # Varian boleh langsung ikut pas produk dibikin — pemilik yang nambah
    # "Kopi Susu" biasanya udah tahu mau ada Panas & Dingin saat itu juga.
    variants: list[ProductVariantCreate] = []

class ProductUpdate(BaseModel):
    category_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=0)
    buy_price: Optional[Decimal] = Field(None, ge=0)
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
    # Selalu ada (list kosong kalau produknya nggak bervarian) supaya klien
    # nggak perlu bedain "belum di-load" vs "nggak punya varian".
    variants: list[ProductVariantResponse] = []

    @computed_field
    @property
    def has_variants(self) -> bool:
        """Klien pakai ini buat mutusin tap produk → langsung masuk keranjang
        atau buka pemilih varian dulu. Varian nonaktif nggak dihitung: kalau
        semua variannya lagi mati, produknya jadi produk polos lagi, bukan
        produk yang bikin kasir mentok di sheet kosong."""
        return any(v.is_active for v in self.variants)

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
