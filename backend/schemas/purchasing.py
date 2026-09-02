from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, model_validator


# ── Supplier ──

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    payment_terms_days: int = Field(0, ge=0, le=365)


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    payment_terms_days: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None
    row_version: int


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    payment_terms_days: int
    row_version: int
    created_at: datetime
    # Diisi list endpoint: berapa nota + total belanja ke supplier ini.
    purchase_count: int = 0
    purchase_total: Decimal = Decimal("0")
    outstanding_total: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


# ── Nota belanja ──

class NewIngredientIn(BaseModel):
    """Bahan yang belum ada di daftar — dibikin on the fly waktu nota disimpan (Pro)."""
    name: str = Field(..., min_length=1, max_length=120)
    # gram / ml / pcs / bungkus. Kalau kosong, diturunin dari satuan di baris
    # (kg → gram, liter → ml, dus → pcs).
    base_unit: Optional[str] = None


class NewProductIn(BaseModel):
    """Produk jadi yang belum ada — dibikin dengan tracking stok aktif."""
    name: str = Field(..., min_length=1, max_length=120)
    sell_price: Decimal = Field(..., ge=0)


class PurchaseLineIn(BaseModel):
    """
    Satu baris nota. Tepat satu target:
      - ingredient_id / product_id  → barang yang udah ada di daftar
      - new_ingredient / new_product → dibikin dulu, lalu diperlakukan sama
      - name (tanpa target)          → "lainnya": gas, plastik, tisu — gak
                                        nyentuh stok, cuma ikut total & utang
    """
    ingredient_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    new_ingredient: Optional[NewIngredientIn] = None
    new_product: Optional[NewProductIn] = None
    name: Optional[str] = Field(None, max_length=120)
    quantity: float = Field(..., gt=0)
    # Satuan di nota. Kosong = dianggap base_unit bahan (atau pcs buat produk).
    unit: Optional[str] = None
    unit_price: Decimal = Field(..., ge=0)
    # Kalau dikirim, ini yang dipakai (nota sering bulatin); kalau nggak,
    # quantity × unit_price.
    total_price: Optional[Decimal] = Field(None, ge=0)

    @model_validator(mode='after')
    def one_target(self):
        targets = sum(1 for t in (self.ingredient_id, self.product_id, self.new_ingredient, self.new_product) if t)
        if targets > 1:
            raise ValueError("Tiap baris cuma boleh satu target: bahan, produk, bahan baru, atau produk baru")
        if targets == 0 and not (self.name or "").strip():
            raise ValueError("Baris tanpa bahan/produk harus punya nama (mis. 'Gas 3kg', 'Kantong plastik')")
        return self

    @property
    def is_other(self) -> bool:
        return not any((self.ingredient_id, self.product_id, self.new_ingredient, self.new_product))


class PurchaseCreate(BaseModel):
    outlet_id: UUID
    supplier_id: Optional[UUID] = None
    # Tanpa supplier_id tapi ada nama → supplier baru dibikin otomatis.
    supplier_name: Optional[str] = Field(None, max_length=120)
    invoice_no: Optional[str] = Field(None, max_length=80)
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    received_at: Optional[datetime] = None
    # None = lunas (cash di tempat). Angka = yang udah dibayar, sisanya utang.
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    due_at: Optional[datetime] = None
    items: List[PurchaseLineIn] = Field(..., min_length=1)


class PurchaseLineResponse(BaseModel):
    id: UUID
    ingredient_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    is_other: bool = False
    name: str
    quantity: float
    unit: Optional[str] = None
    qty_base: Optional[float] = None
    unit_price: Decimal
    total_price: Decimal
    # Efek ke HPP — diisi service waktu create biar UI bisa nunjukin
    # "cost Susu: Rp 15 → Rp 15,8 /ml".
    cost_before: Optional[Decimal] = None
    cost_after: Optional[Decimal] = None


class PurchaseResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    po_number: str
    status: str
    invoice_no: Optional[str] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    received_at: Optional[datetime] = None
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    due_at: Optional[datetime] = None
    row_version: int
    created_at: datetime
    items: List[PurchaseLineResponse] = []


class PurchasePay(BaseModel):
    amount: Decimal = Field(..., gt=0)
    row_version: int


class PurchaseSummary(BaseModel):
    month_total: Decimal
    month_count: int
    outstanding_total: Decimal
    outstanding_count: int
    # Nota utang yang paling dekat jatuh tempo (buat kartu peringatan).
    next_due_at: Optional[datetime] = None
    next_due_supplier: Optional[str] = None
    next_due_amount: Optional[Decimal] = None
