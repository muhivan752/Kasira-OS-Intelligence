"""payments

Revision ID: 026
Revises: 025
Create Date: 2026-03-20 10:26:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE payment_method AS ENUM ('cash', 'qris', 'card', 'transfer')")
    op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'partial', 'expired', 'cancelled', 'refunded', 'failed')")

    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payment_method', postgresql.ENUM('cash', 'qris', 'card', 'transfer', name='payment_method', create_type=False), nullable=False),
        sa.Column('amount_due', sa.Numeric(12, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(12, 2), nullable=False),
        sa.Column('change_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'paid', 'partial', 'expired', 'cancelled', 'refunded', 'failed', name='payment_status', create_type=False), server_default='pending', nullable=False),
        sa.Column('reference_id', sa.String(), nullable=True),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('qris_url', sa.String(), nullable=True),
        sa.Column('qris_expired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('midtrans_raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_payments_idempotency_key', 'payments', ['idempotency_key'], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))

def downgrade():
    op.drop_table('payments')
    op.execute("DROP TYPE payment_status")
    op.execute("DROP TYPE payment_method")
