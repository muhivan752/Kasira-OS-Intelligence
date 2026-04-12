"""Referral commission: drop reward_days, add commission_pct + referral_commissions table

Revision ID: 071
Revises: 070
Create Date: 2026-04-12 23:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade():
    # Modify referrals: drop reward columns, add commission_pct
    op.drop_column("referrals", "referrer_reward_days")
    op.drop_column("referrals", "referred_reward_days")
    op.add_column("referrals", sa.Column("commission_pct", sa.Integer, nullable=False, server_default="20"))

    # Create referral_commissions table
    op.create_table(
        "referral_commissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("referral_id", UUID(as_uuid=True), sa.ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("subscription_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("referrer_tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_amount", sa.Integer, nullable=False),
        sa.Column("commission_pct", sa.Integer, nullable=False),
        sa.Column("commission_amount", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Unique: 1 commission per invoice
    op.create_index("uix_commission_invoice", "referral_commissions", ["invoice_id"], unique=True)
    op.create_index("ix_commission_referrer", "referral_commissions", ["referrer_tenant_id"])

    # RLS for referral_commissions
    op.execute("ALTER TABLE referral_commissions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE referral_commissions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON referral_commissions
        USING (
            current_setting('app.current_tenant_id', true) = ''
            OR referrer_tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON referral_commissions")
    op.execute("ALTER TABLE referral_commissions DISABLE ROW LEVEL SECURITY")
    op.drop_table("referral_commissions")
    op.drop_column("referrals", "commission_pct")
    op.add_column("referrals", sa.Column("referrer_reward_days", sa.Integer, server_default="30", nullable=False))
    op.add_column("referrals", sa.Column("referred_reward_days", sa.Integer, server_default="7", nullable=False))
