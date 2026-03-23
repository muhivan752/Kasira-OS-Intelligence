import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base
from backend.models.base import BaseModel

class Category(BaseModel):
    __tablename__ = "categories"

    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    brand = relationship("Brand", back_populates="categories")
    products = relationship("Product", back_populates="category")
