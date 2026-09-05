import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Device(BaseModel):
    """HP/tablet yang dipasangi app, buat notifikasi FCM (mig 007, dihidupkan
    5 Sep 2026).

    Tabelnya lahir bareng migrasi awal lalu nganggur bertahun-tahun: nol
    model, nol route, nol baris. Sama persis kasusnya dengan
    `product_variants` dan tabel purchasing. Jangan bikin tabel kedua.

    Identitasnya `fcm_token`, BUKAN pasangan user+outlet. Satu HP bisa dipakai
    kasir yang gantian login, dan tokennya tetap satu; makanya daftar ulang
    itu upsert by token yang menimpa `user_id`/`outlet_id`. Sebaliknya satu
    akun bisa pegang tiga HP, dan ketiganya harus dapat kabar.

    `outlet_id` WAJIB diisi walau kolomnya nullable: policy RLS `devices`
    nyaring lewat outlet_id, jadi baris tanpa outlet nggak akan pernah
    kelihatan lagi sesudah disimpan.
    """
    __tablename__ = "devices"

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True)

    device_name = Column(String, nullable=False)
    # kasir | dapur | owner — ENUM `device_type` dari mig 007.
    device_type = Column(Enum('kasir', 'dapur', 'owner', name='device_type', create_type=False), nullable=False)

    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, server_default='false', nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    fcm_token = Column(String, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    outlet = relationship("Outlet")
