"""roles

Revision ID: 004
Revises: 003
Create Date: 2026-03-20 10:04:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE role_scope AS ENUM ('tenant', 'brand', 'outlet')")

    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('scope', postgresql.ENUM('tenant', 'brand', 'outlet', name='role_scope', create_type=False), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('can_view_hpp', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('can_view_revenue_detail', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('can_view_supplier_price', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('can_approve_hpp_update', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('can_scan_invoice', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('roles')
    op.execute("DROP TYPE role_scope")
