"""tenants

Revision ID: 001
Revises: 
Create Date: 2026-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create ENUMs
    op.execute("CREATE TYPE subscription_tier AS ENUM ('starter', 'pro', 'business', 'enterprise')")
    op.execute("CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired')")

    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_email', sa.String(), nullable=False, unique=True),
        sa.Column('subscription_tier', postgresql.ENUM('starter', 'pro', 'business', 'enterprise', name='subscription_tier', create_type=False), nullable=False),
        sa.Column('subscription_status', postgresql.ENUM('trial', 'active', 'suspended', 'cancelled', 'expired', name='subscription_status', create_type=False), nullable=False),
        sa.Column('outlet_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('data_retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('export_requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tos_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tos_version', sa.String(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('tenants')
    op.execute("DROP TYPE subscription_status")
    op.execute("DROP TYPE subscription_tier")
