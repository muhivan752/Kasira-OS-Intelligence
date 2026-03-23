"""connect_orders

Revision ID: 039
Revises: 038
Create Date: 2026-03-20 10:39:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '039'
down_revision = '038'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE connect_order_status AS ENUM ('pending', 'accepted', 'rejected', 'processing', 'ready', 'completed', 'cancelled', 'failed')")

    op.create_table(
        'connect_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('connect_outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connect_outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('external_order_id', sa.String(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'accepted', 'rejected', 'processing', 'ready', 'completed', 'cancelled', 'failed', name='connect_order_status', create_type=False), server_default='pending', nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.UniqueConstraint('idempotency_key', name='uq_connect_order_idempotency')
    )
    
    op.create_index('ix_connect_orders_external_id', 'connect_orders', ['external_order_id'])

def downgrade():
    op.drop_table('connect_orders')
    op.execute("DROP TYPE connect_order_status")
