from sqlalchemy import Column, String, ForeignKey, Integer, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Referral(BaseModel):
    __tablename__ = "referrals"

    referrer_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    referred_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True)
    referral_code = Column(String(20), nullable=False, index=True)
    commission_pct = Column(Integer, nullable=False, default=20)  # 20%
    status = Column(String(20), nullable=False, default="active")  # active, revoked
    row_version = Column(Integer, server_default='0', nullable=False)

    referrer = relationship("Tenant", foreign_keys=[referrer_tenant_id])
    referred = relationship("Tenant", foreign_keys=[referred_tenant_id])


class ReferralCommission(BaseModel):
    __tablename__ = "referral_commissions"

    referral_id = Column(UUID(as_uuid=True), ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("subscription_invoices.id", ondelete="CASCADE"), nullable=False)
    referrer_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    invoice_amount = Column(Integer, nullable=False)  # total invoice
    commission_pct = Column(Integer, nullable=False)   # 20
    commission_amount = Column(Integer, nullable=False) # calculated
    status = Column(String(20), nullable=False, default="pending")  # pending, paid, cancelled
    row_version = Column(Integer, server_default='0', nullable=False)

    referral = relationship("Referral")
