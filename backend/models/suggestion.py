from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.models.base import BaseModel


class Suggestion(BaseModel):
    """Saran proaktif Selaris. Aturan dan siklus hidupnya: services/suggestions.py."""
    __tablename__ = "suggestions"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(32), nullable=False)
    subject_type = Column(String(16), nullable=False)
    subject_id = Column(UUID(as_uuid=True), nullable=False)
    dedup_key = Column(String(120), nullable=False)
    data_hash = Column(String(64), nullable=False)
    facts = Column(JSONB, nullable=False)
    proposal = Column(JSONB, nullable=False)
    impact_rp = Column(Numeric(14, 2), nullable=False, server_default="0")
    urgent = Column(Boolean, nullable=False, server_default="false")
    visibility = Column(String(8), nullable=False)
    status = Column(String(12), nullable=False, server_default="open")
    edited = Column(Boolean, nullable=False, server_default="false")
    decided_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    skip_reason = Column(String(40), nullable=True)
    result = Column(JSONB, nullable=True)
    undo = Column(JSONB, nullable=True)
    hpp_session_id = Column(UUID(as_uuid=True), ForeignKey("hpp_setup_sessions.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    row_version = Column(Integer, nullable=False, server_default="0")
