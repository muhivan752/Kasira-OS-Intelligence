import uuid
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import BaseModel


class Customer(BaseModel):
    __tablename__ = "customers"

    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_hmac = Column(String, nullable=False, default='')

    # Agregat belanja. Kolomnya udah ada di DB sejak migrasi 009 tapi TIDAK
    # pernah dipetakan di model ini — makanya nggak ada satu pun kode yang bisa
    # ngisinya, dan semua nilainya nol. Dipetakan sekarang; yang ngisi
    # `backend/services/customer_stats.py` (dihitung ulang dari orders, bukan
    # di-increment, biar nggak melenceng).
    total_visits = Column(Integer, server_default='0', nullable=False)
    total_spent = Column(Numeric(12, 2), server_default='0', nullable=False)
    first_visit_at = Column(DateTime(timezone=True), nullable=True)
    last_visit_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Persetujuan kirim promo. Dipakai sebagai gerbang kalau nanti ada fitur
    # broadcast — kirim ke yang belum setuju itu spam + masalah UU PDP.
    wa_marketing_consent = Column(Boolean, server_default='false', nullable=False)
    consent_given_at = Column(DateTime(timezone=True), nullable=True)
    data_retention_until = Column(DateTime(timezone=True), nullable=True)

    row_version = Column(Integer, server_default='0', nullable=False)
