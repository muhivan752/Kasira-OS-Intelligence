import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class Brand(BaseModel):
    __tablename__ = "brands"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(ENUM('warung', 'cafe', 'resto', 'other', name='brand_type', create_type=False), nullable=False)
    logo_url = Column(String, nullable=True)
    is_active = Column(Boolean, server_default='true', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="brands")
    outlets = relationship("Outlet", back_populates="brand")
    categories = relationship("Category", back_populates="brand")
    products = relationship("Product", back_populates="brand")
