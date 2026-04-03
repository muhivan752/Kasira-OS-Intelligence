from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from backend.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    scope = Column(ENUM("tenant", "brand", "outlet", name="role_scope", create_type=False), nullable=False)
    permissions = Column(JSONB, nullable=True)
    is_system = Column(Boolean, server_default="false", nullable=False)
    can_view_hpp = Column(Boolean, server_default="false", nullable=False)
    can_view_revenue_detail = Column(Boolean, server_default="false", nullable=False)
    can_view_supplier_price = Column(Boolean, server_default="false", nullable=False)
    can_approve_hpp_update = Column(Boolean, server_default="false", nullable=False)
    can_scan_invoice = Column(Boolean, server_default="true", nullable=False)
