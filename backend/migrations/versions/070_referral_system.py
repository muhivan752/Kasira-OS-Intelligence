"""Referral system: referrals table + tenant referral_code column

Revision ID: 070
Revises: 069
Create Date: 2026-04-12 23:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade():
    # Add referral_code to tenants
    op.add_column("tenants", sa.Column("referral_code", sa.String(20), unique=True, nullable=True, index=True))

    # Create referrals table
    op.create_table(
        "referrals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("referrer_tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("referred_tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("referral_code", sa.String(20), nullable=False, index=True),
        sa.Column("referrer_reward_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("referred_reward_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # RLS for referrals (referrer OR referred can see)
    op.execute("ALTER TABLE referrals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE referrals FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON referrals
        USING (
            current_setting('app.current_tenant_id', true) = ''
            OR referrer_tenant_id::text = current_setting('app.current_tenant_id', true)
            OR referred_tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON referrals")
    op.execute("ALTER TABLE referrals DISABLE ROW LEVEL SECURITY")
    op.drop_table("referrals")
    op.drop_column("tenants", "referral_code")
