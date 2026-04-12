from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.models.base import BaseModel


class SubscriptionInvoice(BaseModel):
    __tablename__ = "subscription_invoices"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    tier = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, server_default="pending", nullable=False)
    xendit_invoice_id = Column(String, nullable=True)
    xendit_invoice_url = Column(String, nullable=True)
    xendit_raw = Column(JSONB, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String, nullable=True)
    row_version = Column(Integer, server_default="0", nullable=False)

    __table_args__ = (
        Index("ix_sub_invoice_tenant_status", "tenant_id", "status"),
        Index("ix_sub_invoice_due_status", "due_date", "status"),
    )
