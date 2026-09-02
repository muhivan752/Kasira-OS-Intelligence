from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.models.finance import EXPENSE_CATEGORY_KEYS, PAYMENT_METHODS


# ── Akun kas ──

class CashAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    opening_balance: Optional[Decimal] = None
    default_for: Optional[List[str]] = None
    is_active: Optional[bool] = None
    row_version: int


class CashAccountResponse(BaseModel):
    id: UUID
    name: str
    kind: str
    default_for: List[str]
    opening_balance: Decimal
    is_active: bool
    sort_order: int
    row_version: int

    model_config = ConfigDict(from_attributes=True)


# ── Pengeluaran ──

class ExpenseCreate(BaseModel):
    outlet_id: Optional[UUID] = None
    category: str = "lainnya"
    amount: Decimal = Field(..., gt=0)
    paid_at: Optional[datetime] = None
    payment_method: str = "cash"
    cash_account_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    note: Optional[str] = Field(None, max_length=200)
    photo_url: Optional[str] = None
    recurring: str = "none"

    @field_validator("category")
    @classmethod
    def _cat(cls, v):
        v = (v or "lainnya").strip().lower()
        if v not in EXPENSE_CATEGORY_KEYS:
            raise ValueError(f"Kategori tidak dikenal: {v}")
        return v

    @field_validator("payment_method")
    @classmethod
    def _pm(cls, v):
        v = (v or "cash").strip().lower()
        if v not in PAYMENT_METHODS:
            raise ValueError(f"Metode bayar tidak dikenal: {v}")
        return v

    @field_validator("recurring")
    @classmethod
    def _rec(cls, v):
        v = (v or "none").strip().lower()
        if v not in ("none", "monthly"):
            raise ValueError("recurring harus 'none' atau 'monthly'")
        return v


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    cash_account_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    note: Optional[str] = Field(None, max_length=200)
    photo_url: Optional[str] = None
    recurring: Optional[str] = None
    row_version: int


class ExpenseResponse(BaseModel):
    id: UUID
    outlet_id: Optional[UUID] = None
    category: str
    category_label: str = ""
    amount: Decimal
    paid_at: datetime
    payment_method: str
    cash_account_id: Optional[UUID] = None
    cash_account_name: Optional[str] = None
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    purchase_id: Optional[UUID] = None
    note: Optional[str] = None
    photo_url: Optional[str] = None
    recurring: str
    row_version: int
    created_at: datetime


# ── Ringkasan bulan ──

class CategoryAmount(BaseModel):
    key: str
    label: str
    amount: Decimal
    count: int = 0


class AccountFlow(BaseModel):
    id: Optional[UUID] = None
    name: str
    kind: str
    inflow: Decimal
    outflow: Decimal
    net: Decimal


class MonthPoint(BaseModel):
    month: str            # "2026-09"
    label: str            # "Sep"
    revenue: Decimal
    cogs: Decimal
    expenses: Decimal
    net: Decimal


class FinanceSummary(BaseModel):
    month: str
    outlet_id: UUID

    # Laba rugi (akrual: order lunas di bulan itu)
    revenue: Decimal            # total order lunas (sesudah diskon, termasuk pajak/service)
    refunds: Decimal
    net_revenue: Decimal
    cogs: Decimal               # HPP barang terjual
    cogs_coverage: float        # 0..1 — porsi item terjual yang punya HPP
    gross_profit: Decimal
    gross_margin_pct: float
    expenses_total: Decimal
    expenses_by_category: List[CategoryAmount]
    petty_cash_out: Decimal     # kas kecil shift (cash_activities expense) — ikut beban
    net_profit: Decimal
    net_margin_pct: float
    orders_count: int

    # Arus kas (kas beneran keluar-masuk di bulan itu)
    cash_in: Decimal
    cash_out: Decimal
    cash_net: Decimal
    accounts: List[AccountFlow]
    purchases_paid: Decimal     # uang yang keluar buat nota belanja
    payables_outstanding: Decimal

    trend: List[MonthPoint]
    recurring_pending: int      # template bulanan yang belum disalin ke bulan ini
