"""subscriptions

Revision ID: 046
Revises: 045
Create Date: 2026-03-20 10:46:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE subscription_billing_status AS ENUM ('active', 'past_due', 'canceled', 'unpaid', 'trialing')")
    op.execute("CREATE TYPE subscription_interval AS ENUM ('daily', 'weekly', 'monthly', 'yearly')")

    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_name', sa.String(), nullable=False),
        sa.Column('plan_tier', sa.String(), nullable=False), # Starter/Pro/Business
        sa.Column('outlet_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('amount_per_period', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'past_due', 'canceled', 'unpaid', 'trialing', name='subscription_billing_status', create_type=False), server_default='trialing', nullable=False),
        sa.Column('interval', postgresql.ENUM('daily', 'weekly', 'monthly', 'yearly', name='subscription_interval', create_type=False), nullable=False),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('grace_period_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False), # Wajib row_version
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('subscriptions')
    op.execute("DROP TYPE subscription_interval")
    op.execute("DROP TYPE subscription_billing_status")
