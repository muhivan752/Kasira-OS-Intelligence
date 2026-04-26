from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel
from backend.utils.encryption import EncryptedString

class Outlet(BaseModel):
    __tablename__ = "outlets"

    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean(), default=True)
    is_open = Column(Boolean(), default=True)
    opening_hours = Column(JSONB, nullable=True)
    cover_image_url = Column(String, nullable=True)

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True, index=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Location (from migration 003)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    province = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    geocoded_at = Column(DateTime(timezone=True), nullable=True)
    geocode_source = Column(ENUM('gps', 'manual', 'gmaps', name='geocode_source', create_type=False), nullable=True)
    location_verified = Column(Boolean, server_default='false', nullable=False)
    delivery_radius_km = Column(Float, server_default='5.0', nullable=False)

    xendit_business_id = Column(String, nullable=True) # sub-account id (xenPlatform Phase 2)
    xendit_connected_at = Column(DateTime(timezone=True), nullable=True)
    xendit_api_key = Column(EncryptedString, nullable=True)  # AES-256-GCM at rest (TypeDecorator transparent encrypt/decrypt)
    xendit_callback_token = Column(EncryptedString, nullable=True)  # BYOK Phase 2 — per-merchant webhook verify (DEFERRED actual wire-up)

    stock_mode = Column(ENUM('simple', 'recipe', name='stock_mode_type', create_type=False), server_default='simple', nullable=False)

    brand = relationship("Brand", back_populates="outlets")
    orders = relationship("Order", back_populates="outlet")

