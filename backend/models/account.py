from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import BaseModel


class LoginSession(BaseModel):
    __tablename__ = "sessions"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id"))
    device_id = Column(UUID(as_uuid=True))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    token_hash = Column(String, nullable=False)
    credential_version = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    row_version = Column(Integer, nullable=False, default=1)


class AccountChallenge(BaseModel):
    __tablename__ = "account_challenges"
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    purpose = Column(String(20), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    credential_version = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True))
    row_version = Column(Integer, default=1, nullable=False)
