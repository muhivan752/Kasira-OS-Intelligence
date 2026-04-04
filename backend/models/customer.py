import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import BaseModel

class Customer(BaseModel):
    __tablename__ = "customers"

    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_hmac = Column(String, nullable=False, default='')
    row_version = Column(
        __import__('sqlalchemy').Integer,
        server_default='0',
        nullable=False
    )
