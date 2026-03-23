"""audit_log

Revision ID: 036
Revises: 035
Create Date: 2026-03-20 10:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True), # No FK to allow tracking deleted tenants
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True), # No FK to allow tracking deleted users
        sa.Column('action', sa.String(), nullable=False), # e.g., 'CREATE', 'UPDATE', 'DELETE'
        sa.Column('entity', sa.String(), nullable=False), # e.g., 'orders', 'products'
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('before_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('after_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        # Append only, no updated_at or deleted_at
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('ix_audit_log_entity', 'audit_log', ['entity', 'entity_id'])
    op.create_index('ix_audit_log_tenant', 'audit_log', ['tenant_id'])
    op.create_index('ix_audit_log_request', 'audit_log', ['request_id'])

def downgrade():
    op.drop_table('audit_log')
