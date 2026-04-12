"""subscription invoices table and tenant billing fields

Revision ID: 068
Revises: 067
Create Date: 2026-04-12 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade():
    # Create subscription_invoices table (public schema)
    # Using String for status to avoid ENUM type conflicts
    op.create_table(
        "subscription_invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("billing_period_start", sa.Date(), nullable=False),
        sa.Column("billing_period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("xendit_invoice_id", sa.String(), nullable=True),
        sa.Column("xendit_invoice_url", sa.String(), nullable=True),
        sa.Column("xendit_raw", JSONB(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_index("ix_sub_invoice_tenant_status", "subscription_invoices", ["tenant_id", "status"])
    op.create_index("ix_sub_invoice_due_status", "subscription_invoices", ["due_date", "status"])

    # Add billing columns to tenants
    op.add_column("tenants", sa.Column("billing_day", sa.Integer(), server_default="1", nullable=False))
    op.add_column("tenants", sa.Column("next_billing_date", sa.Date(), nullable=True))
    op.add_column("tenants", sa.Column("owner_email", sa.String(), nullable=True))


def downgrade():
    op.drop_column("tenants", "owner_email")
    op.drop_column("tenants", "next_billing_date")
    op.drop_column("tenants", "billing_day")
    op.drop_index("ix_sub_invoice_due_status", table_name="subscription_invoices")
    op.drop_index("ix_sub_invoice_tenant_status", table_name="subscription_invoices")
    op.drop_table("subscription_invoices")
