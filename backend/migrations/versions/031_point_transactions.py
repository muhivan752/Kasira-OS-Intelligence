"""point_transactions

Revision ID: 031
Revises: 030
Create Date: 2026-03-20 10:31:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE point_transaction_type AS ENUM ('earn', 'redeem', 'adjustment', 'refund')")

    op.create_table(
        'point_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', postgresql.ENUM('earn', 'redeem', 'adjustment', 'refund', name='point_transaction_type', create_type=False), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('balance_after', sa.Numeric(12, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        # Golden Rule #35: UNIQUE constraint pada (order_id, type)
        sa.UniqueConstraint('order_id', 'type', name='uq_point_txn_order_type')
    )

def downgrade():
    op.drop_table('point_transactions')
    op.execute("DROP TYPE point_transaction_type")
