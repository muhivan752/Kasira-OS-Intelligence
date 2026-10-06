from sqlalchemy import Column, String, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    phone = Column(String, unique=True, index=True, nullable=True)
    login_username = Column(String(64), nullable=True)
    password_hash = Column(String, nullable=True)
    credential_version = Column(Integer, server_default='0', default=0, nullable=False)
    full_name = Column(String, nullable=False)
    google_project_id = Column(String(128), nullable=True)
    google_uid = Column(String(128), nullable=True)
    google_email = Column(String(320), nullable=True)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    
    # PIN for POS access
    pin_hash = Column(String, nullable=True)
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    
    # For critical tables
    row_version = Column(Integer, default=1, nullable=False)
