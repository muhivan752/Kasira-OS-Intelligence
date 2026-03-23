import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, Text, DateTime, CheckConstraint
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
    embedding = Column(Vector(1536), nullable=True)

    __table_args__ = (
        CheckConstraint('stock_qty >= 0', name='chk_products_stock_qty'),
    )

    # Relationships
    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")

class OutletStock(BaseModel):
    __tablename__ = "outlet_stock"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    
    from sqlalchemy.dialects.postgresql import JSONB
    crdt_positive = Column(JSONB, server_default='{}', nullable=False)
    crdt_negative = Column(JSONB, server_default='{}', nullable=False)
    computed_stock = Column(Integer, server_default='0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    __table_args__ = (
        CheckConstraint('computed_stock >= 0', name='chk_outlet_stock_computed'),
    )
