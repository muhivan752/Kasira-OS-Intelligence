"""Promo WhatsApp dari nomor toko sendiri (mig 096)."""
from sqlalchemy import Column, String, ForeignKey, Integer, Text, DateTime, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.models.base import BaseModel


class Campaign(BaseModel):
    __tablename__ = "campaigns"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(120), nullable=False)
    # Variabel: {nama}, {toko}. Selalu ditutup baris "Balas STOP untuk berhenti".
    template = Column(Text, nullable=False)
    # 'all' | 'segment:<key>' | 'tag:<uuid>'
    target = Column(String(80), nullable=False, server_default='all')
    # draft | sending | done | failed
    status = Column(String(20), nullable=False, server_default='draft')
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    recipient_count = Column(Integer, nullable=False, server_default='0')
    sent_count = Column(Integer, nullable=False, server_default='0')
    failed_count = Column(Integer, nullable=False, server_default='0')
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    row_version = Column(Integer, nullable=False, server_default='0')

    messages = relationship("CampaignMessage", back_populates="campaign", cascade="all, delete-orphan")


class CampaignMessage(Base):
    """Satu baris per penerima. Tanpa updated_at/deleted_at (append-only)."""
    __tablename__ = "campaign_messages"
    __table_args__ = (UniqueConstraint('campaign_id', 'customer_id', name='uq_campaign_customer'),)

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    phone = Column(String(20), nullable=False)
    # queued | sent | failed | skipped
    status = Column(String(20), nullable=False, server_default='queued')
    error = Column(String(200), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

    campaign = relationship("Campaign", back_populates="messages")
