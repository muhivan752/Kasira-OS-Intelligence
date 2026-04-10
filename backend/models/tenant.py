import enum
from sqlalchemy import Column, String, Boolean, Integer, Enum
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

    brands = relationship("Brand", back_populates="tenant")
