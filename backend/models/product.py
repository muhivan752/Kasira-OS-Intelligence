import uuid
from typing import Optional
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Float, Numeric, Text, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base
from backend.models.base import BaseModel
from pgvector.sqlalchemy import Vector

class Product(BaseModel):
    __tablename__ = "products"

    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(12, 2), nullable=False)
    buy_price = Column(Numeric(12, 2), nullable=True)
    image_url = Column(String, nullable=True)
    order_count = Column(Integer, server_default='0', nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)
    stock_enabled = Column(Boolean, server_default='false', nullable=False)
    stock_qty = Column(Integer, server_default='0', nullable=False)
    stock_low_threshold = Column(Integer, server_default='5', nullable=False)
    stock_auto_hide = Column(Boolean, server_default='true', nullable=False)
    sold_today = Column(Integer, server_default='0', nullable=False)
    sold_total = Column(Integer, server_default='0', nullable=False)
    last_restock_at = Column(DateTime(timezone=True), nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)
    
    # From 045_products_update.py
    sku = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    is_subscription = Column(Boolean, server_default='false', nullable=False)

    # Vector column
    embedding = Column(Vector(512), nullable=True)  # voyage-3-lite

    __table_args__ = (
        CheckConstraint('stock_qty >= 0', name='chk_products_stock_qty'),
    )

    # Relationships
    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")
    recipes = relationship("Recipe", back_populates="product")
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        # Urutan yang sama persis dipakai POS, storefront, dan dashboard —
        # kalau tiap layer nyortir sendiri, urutannya beda-beda dan kasir
        # bingung.
        order_by="ProductVariant.sort_order, ProductVariant.created_at",
        # Varian yang udah dihapus TIDAK PERNAH ikut ke mana-mana. Disaring di
        # relasi, bukan di tiap query: ProductResponse dibangun dari belasan
        # tempat (list, detail, low-stock, best-seller, restock, storefront) dan
        # satu yang lupa nyaring = varian hantu muncul lagi di POS.
        primaryjoin=(
            "and_(Product.id == ProductVariant.product_id, "
            "ProductVariant.deleted_at.is_(None))"
        ),
        # lazy="selectin" = SELALU ke-load, tanpa perlu selectinload() manual di
        # tiap call site. Ini disengaja: `ProductResponse.variants` dibaca di
        # semua endpoint produk, dan relasi lazy default bakal meledak
        # MissingGreenlet di async begitu ada satu endpoint yang kelewat
        # (pola bug yang udah kegigit berkali-kali di repo ini). Biayanya satu
        # query tambahan per query produk — murah dibanding 500 senyap.
        lazy="selectin",
    )

    @property
    def category_name(self) -> Optional[str]:
        return self.category.name if self.category else None

class ProductVariant(BaseModel):
    """Varian produk — Hot/Ice, size R/L, level gula.

    `price_adjustment` itu SELISIH dari `product.base_price`, bukan harga akhir.
    Ice +2000 ditulis 2000, bukan 27000. Alasannya: kalau harga pokok naik,
    pemilik cukup ubah satu angka di produk dan semua varian ikut — kalau
    absolut, dia harus ngedit satu-satu dan pasti ada yang kelewat. Boleh
    negatif (size kecil -3000), jadi jangan dikasih CHECK >= 0.

    Harga jual final = `product.base_price + variant.price_adjustment`, dihitung
    di `variant_price()` (`backend/services/variant_utils.py`) — SATU tempat,
    dipakai POS, storefront, dan validasi order biar nggak ada yang beda hitung.
    """
    __tablename__ = "product_variants"

    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    price_adjustment = Column(Numeric(12, 2), server_default='0', nullable=False)
    # Varian bisa dimatikan sementara (es batu habis) tanpa dihapus — order
    # lama tetap boleh nunjuk varian ini, jadi hard delete dilarang (Rule #7).
    is_active = Column(Boolean, server_default='true', nullable=False)
    sort_order = Column(Integer, server_default='0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    product = relationship("Product", back_populates="variants")

class OutletStock(BaseModel):
    __tablename__ = "outlet_stock"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)

    from sqlalchemy.dialects.postgresql import JSONB
    crdt_positive = Column(JSONB, server_default='{}', nullable=False)
    crdt_negative = Column(JSONB, server_default='{}', nullable=False)
    computed_stock = Column(Float, server_default='0.0', nullable=False)
    min_stock_base = Column(Float, server_default='0.0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    __table_args__ = (
        CheckConstraint('computed_stock >= 0', name='chk_outlet_stock_computed'),
    )

    # Relationships
    ingredient = relationship("Ingredient", back_populates="outlet_stocks")
