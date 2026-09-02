"""
CRM gelombang 3 — tag, timeline, voucher. Kolom segmen/RFM ada di `Customer`.
Lihat mig 095.
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, DateTime, Date, CheckConstraint, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.models.base import BaseModel


# Bahasa warung. Urutan = urutan chip di halaman Pelanggan.
SEGMENTS: list[tuple[str, str, str]] = [
    ("baru", "Baru", "1 kunjungan dalam 14 hari terakhir"),
    ("setia", "Setia", "≥ 4 kunjungan dalam 30 hari"),
    ("vip", "VIP", "10% teratas belanja 90 hari"),
    ("biasa", "Biasa", "Aktif, belum masuk kelompok lain"),
    ("mulai_jarang", "Mulai jarang", "Dulu rutin, sekarang > 21 hari absen"),
    ("hilang", "Hilang", "> 60 hari nggak datang"),
]
SEGMENT_KEYS = {k for k, _, _ in SEGMENTS}
TAG_COLORS = ("violet", "pink", "mint", "amber", "blue", "gray")
TIMELINE_KINDS = ("note", "complaint", "visit", "campaign_sent", "voucher_used", "consent", "system")


class CustomerTag(BaseModel):
    __tablename__ = "customer_tags"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(40), nullable=False)
    color = Column(String(20), nullable=False, server_default='violet')
    row_version = Column(Integer, nullable=False, server_default='0')


class CustomerTagLink(Base):
    __tablename__ = "customer_tag_links"
    __table_args__ = (UniqueConstraint('customer_id', 'tag_id', name='uq_customer_tag'),)

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey('customer_tags.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

    tag = relationship("CustomerTag")


class CustomerTimeline(Base):
    __tablename__ = "customer_timeline"

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    kind = Column(String(24), nullable=False, server_default='note')
    ref_id = Column(UUID(as_uuid=True), nullable=True)
    body = Column(String(500), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Voucher(BaseModel):
    __tablename__ = "vouchers"
    __table_args__ = (
        CheckConstraint("kind IN ('percent','amount')", name='chk_voucher_kind'),
        CheckConstraint('value > 0', name='chk_voucher_value'),
    )

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    code = Column(String(32), nullable=False)
    name = Column(String(80), nullable=True)
    kind = Column(String(12), nullable=False, server_default='percent')   # percent | amount
    value = Column(Numeric(12, 2), nullable=False)
    max_discount = Column(Numeric(12, 2), nullable=True)                   # cap buat percent
    min_purchase = Column(Numeric(12, 2), nullable=False, server_default='0')
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    quota_total = Column(Integer, nullable=True)
    quota_per_customer = Column(Integer, nullable=True)
    segment = Column(String(20), nullable=True)                             # cuma buat segmen ini
    is_active = Column(Boolean, nullable=False, server_default='true')
    row_version = Column(Integer, nullable=False, server_default='0')

    redemptions = relationship("VoucherRedemption", back_populates="voucher")


class VoucherRedemption(Base):
    __tablename__ = "voucher_redemptions"

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    voucher_id = Column(UUID(as_uuid=True), ForeignKey('vouchers.id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='SET NULL'), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='SET NULL'), nullable=True)
    discount_amount = Column(Numeric(12, 2), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

    voucher = relationship("Voucher", back_populates="redemptions")
