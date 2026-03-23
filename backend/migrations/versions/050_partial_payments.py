"""partial_payments

Revision ID: 050
Revises: 049
Create Date: 2026-03-20 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '050'
down_revision = '049'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE partial_payment_method AS ENUM ('cash', 'card', 'qris', 'transfer', 'ewallet')")
    op.execute("CREATE TYPE partial_payment_status AS ENUM ('paid', 'refunded')")

    op.create_table(
        'partial_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_method', postgresql.ENUM('cash', 'card', 'qris', 'transfer', 'ewallet', name='partial_payment_method', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('paid', 'refunded', name='partial_payment_status', create_type=False), server_default='paid', nullable=False),
        sa.Column('reference_id', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('partial_payments')
    op.execute("DROP TYPE partial_payment_status")
    op.execute("DROP TYPE partial_payment_method")
