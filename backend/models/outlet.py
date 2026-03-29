from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class Outlet(BaseModel):
    __tablename__ = "outlets"

    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean(), default=True)
    is_open = Column(Boolean(), default=True)
    opening_hours = Column(String, nullable=True) # JSONB in DB
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True, index=True)
    row_version = Column(Integer, server_default='0', nullable=False)
    
    xendit_business_id = Column(String, nullable=True) # sub-account id
    xendit_connected_at = Column(DateTime(timezone=True), nullable=True)

    brand = relationship("Brand", back_populates="outlets")
    orders = relationship("Order", back_populates="outlet")

