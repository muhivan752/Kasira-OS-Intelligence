from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel

class Tenant(BaseModel):
    __tablename__ = "tenants"

    name = Column(String, nullable=False)
    schema_name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean(), default=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    brands = relationship("Brand", back_populates="tenant")
