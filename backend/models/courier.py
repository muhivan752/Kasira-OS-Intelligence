import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Courier(BaseModel):
    """Kurir milik toko (delivery gelombang 2, mig 108).

    Keputusan Ivan 5 Sep 2026: yang nganter itu ORANG TOKO, bukan armada
    agregator. Makanya nggak ada akun kurir, nggak ada aplikasi kurir, nggak
    ada bagi hasil. Toko cuma nyatet siapa saja yang biasa nganter, dan
    pelanggan lihat nama plus nomornya di halaman lacak.

    `user_id` opsional: kalau yang nganter kebetulan kasir yang punya akun,
    boleh disambungin, tapi bukan syarat.
    """
    __tablename__ = "couriers"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    name = Column(String(80), nullable=False)
    phone = Column(String(20), nullable=True)
    # motor | mobil | sepeda | jalan_kaki. String, bukan ENUM: nambah pilihan
    # nggak boleh butuh migrasi.
    vehicle = Column(String(20), server_default='motor', nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)
    sort_order = Column(Integer, server_default='0', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    outlet = relationship("Outlet")
