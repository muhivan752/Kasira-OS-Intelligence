"""connect_customer_profiles

Revision ID: 040
Revises: 039
Create Date: 2026-03-20 10:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '040'
down_revision = '039'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'connect_customer_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('channel', postgresql.ENUM('whatsapp', 'gofood', 'grabfood', 'shopeefood', 'tiktok', 'instagram', 'other', name='connect_channel', create_type=False), nullable=False),
        sa.Column('external_customer_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('profile_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.UniqueConstraint('channel', 'external_customer_id', name='uq_connect_customer_channel_ext_id')
    )

def downgrade():
    op.drop_table('connect_customer_profiles')
