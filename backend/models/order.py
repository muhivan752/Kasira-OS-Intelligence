import uuid
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class Order(BaseModel):
    __tablename__ = "orders"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    shift_session_id = Column(UUID(as_uuid=True), ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='SET NULL'), nullable=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey('tables.id', ondelete='SET NULL'), nullable=True)
    tab_id = Column(UUID(as_uuid=True), ForeignKey('tabs.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    order_number = Column(String, nullable=False)
    display_number = Column(Integer, nullable=False) # Sequence handled by DB
    
    status = Column(ENUM('pending', 'preparing', 'ready', 'served', 'completed', 'cancelled', name='order_status', create_type=False), server_default='pending', nullable=False)
    order_type = Column(ENUM('dine_in', 'takeaway', 'delivery', name='order_type', create_type=False), server_default='dine_in', nullable=False)
    
    subtotal = Column(Numeric(12, 2), server_default='0', nullable=False)
    service_charge_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    tax_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    discount_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    total_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    
    notes = Column(Text, nullable=True)
    discount_approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    discount_reason = Column(String(200), nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    outlet = relationship("Outlet", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    tab = relationship("Tab", back_populates="orders")

class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id = Column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), server_default='0', nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    
    from sqlalchemy.dialects.postgresql import JSONB
    modifiers = Column(JSONB(astext_type=Text()), nullable=True)
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Per-item ad-hoc payment (Migration 085) — warkop pattern
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    @property
    def product_name(self) -> str:
        """Nama item LENGKAP dengan variannya: "Kopi Susu (Dingin)".

        Varian sengaja digabung DI SINI, bukan di tiap pemakai. Property ini
        dibaca layar dapur, label split bill, struk WA, dan dashboard — dan
        yang paling gawat kalau kelewat justru dapur: barista cuma lihat teks
        ini, jadi tanpa varian dia bikin yang panas padahal pesanannya dingin.
        Satu tempat = nggak ada konsumen yang bisa ketinggalan.

        Nama varian dibaca dari snapshot di `modifiers`, BUKAN dari relasi ke
        product_variants. Varian bisa dihapus pemilik kapan saja, dan struk
        atau riwayat bulan lalu tetap harus nulis apa yang beneran dibeli.
        """
        base = self.product.name if self.product else ''
        variant_name = None
        if isinstance(self.modifiers, dict):
            variant_name = self.modifiers.get("variant_name")
        return f"{base} ({variant_name})" if variant_name and base else base
