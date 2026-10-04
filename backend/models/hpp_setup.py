from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.models.base import BaseModel


class HppSetupSession(BaseModel):
    __tablename__ = "hpp_setup_sessions"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    mode = Column(String, nullable=False, default="manual")
    status = Column(String, nullable=False, default="draft")
    revision = Column(Integer, nullable=False, default=0)
    draft = Column(JSONB, nullable=True)
    preview = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    pending_request = Column(UUID(as_uuid=True), nullable=True)
    pending_until = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)


class HppSetupTurn(BaseModel):
    __tablename__ = "hpp_setup_turns"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("hpp_setup_sessions.id"), nullable=False)
    request_id = Column(UUID(as_uuid=True), nullable=False)
    mode = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    reply = Column(Text, nullable=True)
    usage = Column(JSONB, nullable=True)
    __table_args__ = (UniqueConstraint("session_id", "request_id", name="uq_hpp_setup_request"),)
