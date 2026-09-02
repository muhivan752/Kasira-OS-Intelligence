"""
Purchasing — supplier, nota belanja, histori harga.

Tabel-tabelnya udah ada sejak mig 008/019/028/044 tapi nggak pernah punya
model (lihat mig 091). "Nota belanja" = `PurchaseOrder` berstatus `received`
yang dibuat langsung; PO formal (draft → sent → received) tinggal pakai
status yang sama kalau nanti dibutuhin.
"""
from sqlalchemy import (
    Column, String, Boolean, ForeignKey, Integer, Numeric, Float, Text,
    DateTime, CheckConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.models.base import BaseModel


class Supplier(BaseModel):
    __tablename__ = "suppliers"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, server_default='true', nullable=False)
    # Default jatuh tempo utang: nota yang belum lunas dapet due_at =
    # received_at + N hari. 0 = kebiasaan bayar cash.
    payment_terms_days = Column(Integer, server_default='0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    ingredient_links = relationship("IngredientSupplier", back_populates="supplier")


class IngredientSupplier(BaseModel):
    """Bahan X biasa dibeli dari supplier Y — diisi otomatis tiap nota."""
    __tablename__ = "ingredient_suppliers"

    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False)
    typical_price_per_base_unit = Column(Numeric(12, 2), nullable=True)
    typical_lead_days = Column(Integer, nullable=True)
    is_preferred = Column(Boolean, server_default='false', nullable=False)
    last_purchased_at = Column(DateTime(timezone=True), nullable=True)
    last_purchase_price = Column(Numeric(12, 2), nullable=True)
    price_trend = Column(
        ENUM('stable', 'rising', 'falling', name='price_trend', create_type=False),
        nullable=True,
    )
    row_version = Column(Integer, server_default='0', nullable=False)

    supplier = relationship("Supplier", back_populates="ingredient_links")
    ingredient = relationship("Ingredient")


class PurchaseOrder(BaseModel):
    __tablename__ = "purchase_orders"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    # NULL = "beli di pasar" / supplier nggak dicatat.
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=True)
    po_number = Column(String, nullable=False)
    status = Column(
        ENUM('draft', 'sent', 'partial', 'received', 'cancelled', name='po_status', create_type=False),
        server_default='draft', nullable=False,
    )
    expected_date = Column(DateTime(timezone=True), nullable=True)
    total_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    notes = Column(Text, nullable=True)

    # ── kolom nota (mig 091) ──
    received_at = Column(DateTime(timezone=True), nullable=True)
    invoice_no = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    paid_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    received_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    row_version = Column(Integer, server_default='0', nullable=False)

    supplier = relationship("Supplier")
    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderItem.created_at",
    )

    @property
    def outstanding_amount(self):
        return max((self.total_amount or 0) - (self.paid_amount or 0), 0)


class PurchaseOrderItem(BaseModel):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint('ingredient_id IS NOT NULL OR product_id IS NOT NULL OR name_snapshot IS NOT NULL', name='chk_poi_target'),
    )

    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    # Nama pas nota dicatat — bahan/produk bisa di-rename atau dihapus,
    # nota bulan lalu tetap harus kebaca.
    name_snapshot = Column(String, nullable=True)
    quantity = Column(Float, nullable=False)
    # Satuan di nota ("kg", "dus"); qty_base = hasil konversi ke base_unit bahan.
    unit = Column(String, nullable=True)
    qty_base = Column(Float, nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    received_quantity = Column(Float, server_default='0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    ingredient = relationship("Ingredient")
    product = relationship("Product")

    @property
    def is_other(self) -> bool:
        """Baris tanpa target stok (gas, plastik, tisu) — cuma ikut total."""
        return self.ingredient_id is None and self.product_id is None

    @property
    def display_name(self) -> str:
        if self.name_snapshot:
            return self.name_snapshot
        if self.ingredient is not None:
            return self.ingredient.name
        if self.product is not None:
            return self.product.name
        return "Item"


class SupplierPriceHistory(Base):
    """
    Tabel lama (mig 044) tanpa updated_at/deleted_at, jadi nggak lewat
    BaseModel — kalau lewat, INSERT-nya bakal nyebut kolom yang nggak ada.
    """
    __tablename__ = "supplier_price_history"

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    old_price = Column(Numeric(12, 2), nullable=True)
    new_price = Column(Numeric(12, 2), nullable=False)
    effective_date = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
