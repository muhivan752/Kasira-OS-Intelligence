import enum
from sqlalchemy import Column, String, Boolean, Integer, Date, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class SubscriptionTier(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    trial = "trial"
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"
    expired = "expired"


class Tenant(BaseModel):
    __tablename__ = "tenants"

    name = Column(String, nullable=False)
    login_username = Column(String(64), unique=True, nullable=True)
    schema_name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean(), default=True)
    subscription_tier = Column(
        Enum(SubscriptionTier, name="subscription_tier", create_type=False),
        server_default="starter", nullable=True
    )
    subscription_status = Column(
        Enum(SubscriptionStatus, name="subscription_status", create_type=False),
        server_default="active", nullable=True
    )
    row_version = Column(Integer, server_default='0', nullable=False)

    # Billing
    billing_day = Column(Integer, server_default='1', nullable=False)
    next_billing_date = Column(Date, nullable=True)
    billing_interval = Column(String, server_default='monthly', nullable=False)  # monthly or annual
    owner_email = Column(String, nullable=True)

    # Demo/test flag — excluded from cross-tenant intelligence
    is_demo = Column(Boolean(), server_default='false', nullable=False)

    # Referral
    referral_code = Column(String(20), unique=True, nullable=True, index=True)

    # Hapus akun pemilik: dijadwalkan, bukan langsung (services/account_deletion.py)
    deletion_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    deletion_requested_by = Column(UUID(as_uuid=True), nullable=True)

    brands = relationship("Brand", back_populates="tenant")
