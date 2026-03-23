"""connect_behavior_log

Revision ID: 042
Revises: 041
Create Date: 2026-03-20 10:42:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '042'
down_revision = '041'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'connect_behavior_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('connect_customer_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connect_customer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(), nullable=False), # e.g., 'clicked_menu', 'asked_promo', 'viewed_product'
        sa.Column('metadata_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Append only, no updated_at or deleted_at
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('ix_connect_behavior_profile_action', 'connect_behavior_log', ['connect_customer_profile_id', 'action'])

def downgrade():
    op.drop_table('connect_behavior_log')
