"""
Keuangan ringan (gelombang 2): pengeluaran + akun kas. Lihat mig 093.
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from backend.models.base import BaseModel


# Kategori tetap. Nol setup buat pemilik warung; custom category nanti kalau
# ada yang minta. Urutan = urutan tampil di UI.
EXPENSE_CATEGORIES: list[tuple[str, str]] = [
    ("sewa", "Sewa tempat"),
    ("listrik_air", "Listrik & air"),
    ("gaji", "Gaji & lembur"),
    ("bahan", "Bahan & stok"),
    ("gas", "Gas & bahan bakar"),
    ("perlengkapan", "Perlengkapan (plastik, tisu, sabun)"),
    ("marketing", "Promosi & iklan"),
    ("peralatan", "Peralatan & perbaikan"),
    ("transport", "Transport & ongkir"),
    ("langganan", "Langganan & aplikasi"),
    ("lainnya", "Lainnya"),
]
EXPENSE_CATEGORY_KEYS = {k for k, _ in EXPENSE_CATEGORIES}

CASH_ACCOUNT_KINDS = ("cash_drawer", "bank", "ewallet", "settlement")
PAYMENT_METHODS = ("cash", "transfer", "qris", "card", "ewallet")


class CashAccount(BaseModel):
    __tablename__ = "cash_accounts"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True)
    name = Column(String(80), nullable=False)
    kind = Column(String(20), nullable=False, server_default='cash_drawer')
    # Metode bayar yang otomatis masuk ke akun ini: ['cash'] / ['transfer','card'] / ['qris']
    default_for = Column(ARRAY(String), nullable=False, server_default='{}')
    opening_balance = Column(Numeric(12, 2), nullable=False, server_default='0')
    is_active = Column(Boolean, nullable=False, server_default='true')
    sort_order = Column(Integer, nullable=False, server_default='0')
    row_version = Column(Integer, nullable=False, server_default='0')


class Expense(BaseModel):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint('amount > 0', name='chk_expenses_amount_positive'),
    )

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True)
    category = Column(String(40), nullable=False, server_default='lainnya')
    amount = Column(Numeric(12, 2), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=False)
    payment_method = Column(String(20), nullable=False, server_default='cash')
    cash_account_id = Column(UUID(as_uuid=True), ForeignKey('cash_accounts.id', ondelete='SET NULL'), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True)
    # Keisi kalau lahir dari baris "Lainnya" di nota belanja. Arus kas ambil
    # pembayaran NOTA-nya, bukan baris ini — biar nggak dobel.
    purchase_id = Column(UUID(as_uuid=True), ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=True)
    note = Column(String(200), nullable=True)
    photo_url = Column(String, nullable=True)
    # 'none' | 'monthly' — monthly = template, disalin lewat "Salin bulan lalu".
    recurring = Column(String(10), nullable=False, server_default='none')
    recorded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    row_version = Column(Integer, nullable=False, server_default='0')

    cash_account = relationship("CashAccount")
    supplier = relationship("Supplier")
