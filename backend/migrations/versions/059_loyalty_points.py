"""loyalty points

Revision ID: 059
Revises: 058
Create Date: 2026-04-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '059'
down_revision = '058'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old tables from migrations 030/031 — redesigned with outlet_id + Integer types
    op.drop_table('point_transactions')
    op.execute("DROP TYPE IF EXISTS point_transaction_type")
    op.drop_index('ix_customer_points_customer_id', table_name='customer_points')
    op.drop_table('customer_points')

    op.create_table(
        'customer_points',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('balance', sa.Integer(), server_default='0', nullable=False),
        sa.Column('lifetime_earned', sa.Integer(), server_default='0', nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint('uq_customer_points_customer_outlet', 'customer_points', ['customer_id', 'outlet_id'])
    op.create_check_constraint('chk_customer_points_balance', 'customer_points', 'balance >= 0')
    op.create_check_constraint('chk_customer_points_lifetime', 'customer_points', 'lifetime_earned >= 0')

    op.create_table(
        'point_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String(20), nullable=False),  # earn / redeem
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Rule #35: UNIQUE(order_id, type) — double points = trust hancur
    op.create_unique_constraint('uq_point_transactions_order_type', 'point_transactions', ['order_id', 'type'])
    op.create_check_constraint('chk_point_transactions_type', 'point_transactions', "type IN ('earn', 'redeem')")
    op.create_check_constraint('chk_point_transactions_points', 'point_transactions', 'points > 0')


def downgrade():
    op.drop_table('point_transactions')
    op.drop_table('customer_points')
    # Restore old schema from migrations 030/031
    op.execute("CREATE TYPE point_transaction_type AS ENUM ('earn', 'redeem', 'adjustment', 'refund')")
    op.create_table(
        'customer_points',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('balance', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('lifetime_earned', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('lifetime_redeemed', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_customer_points_customer_id', 'customer_points', ['customer_id'], unique=True)
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
        sa.UniqueConstraint('order_id', 'type', name='uq_point_txn_order_type')
    )
