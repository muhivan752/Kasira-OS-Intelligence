"""connect_outlets

Revision ID: 038
Revises: 037
Create Date: 2026-03-20 10:38:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE connect_channel AS ENUM ('whatsapp', 'gofood', 'grabfood', 'shopeefood', 'tiktok', 'instagram', 'other')")

    op.create_table(
        'connect_outlets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', postgresql.ENUM('whatsapp', 'gofood', 'grabfood', 'shopeefood', 'tiktok', 'instagram', 'other', name='connect_channel', create_type=False), nullable=False),
        sa.Column('external_store_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.UniqueConstraint('outlet_id', 'channel', name='uq_connect_outlet_channel')
    )

def downgrade():
    op.drop_table('connect_outlets')
    op.execute("DROP TYPE connect_channel")
