"""orders

Revision ID: 024
Revises: 023b
Create Date: 2026-03-20 10:24:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '024'
down_revision = '023b'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE order_status AS ENUM ('pending', 'preparing', 'ready', 'served', 'completed', 'cancelled')")
    op.execute("CREATE TYPE order_type AS ENUM ('dine_in', 'takeaway', 'delivery')")
    op.execute("CREATE SEQUENCE order_display_seq")

    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('shift_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_number', sa.String(), nullable=False),
        sa.Column('display_number', sa.Integer(), server_default=sa.text("nextval('order_display_seq')"), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'preparing', 'ready', 'served', 'completed', 'cancelled', name='order_status', create_type=False), server_default='pending', nullable=False),
        sa.Column('order_type', postgresql.ENUM('dine_in', 'takeaway', 'delivery', name='order_type', create_type=False), server_default='dine_in', nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('service_charge_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('discount_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_orders_outlet_id_order_number', 'orders', ['outlet_id', 'order_number'], unique=True)

def downgrade():
    op.drop_table('orders')
    op.execute("DROP SEQUENCE order_display_seq")
    op.execute("DROP TYPE order_status")
    op.execute("DROP TYPE order_type")
