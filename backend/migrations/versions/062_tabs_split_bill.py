"""tabs and tab_splits for split bill feature

Revision ID: 062
Revises: 061
Create Date: 2026-04-09 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '062'
down_revision = '061'
branch_labels = None
depends_on = None


def upgrade():
    # --- ENUM types ---
    op.execute("CREATE TYPE tab_status AS ENUM ('open', 'asking_bill', 'splitting', 'paid', 'cancelled')")
    op.execute("CREATE TYPE split_method AS ENUM ('full', 'equal', 'per_item', 'custom')")
    op.execute("CREATE TYPE tab_split_status AS ENUM ('unpaid', 'pending', 'paid')")

    # --- tabs table ---
    op.create_table(
        'tabs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='SET NULL'), nullable=True),
        sa.Column('shift_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True),

        sa.Column('tab_number', sa.String(), nullable=False),
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('guest_count', sa.Integer(), server_default='1', nullable=False),

        sa.Column('subtotal', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('service_charge_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('discount_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('paid_amount', sa.Numeric(12, 2), server_default='0', nullable=False),

        sa.Column('split_method', postgresql.ENUM('full', 'equal', 'per_item', 'custom', name='split_method', create_type=False), nullable=True),
        sa.Column('status', postgresql.ENUM('open', 'asking_bill', 'splitting', 'paid', 'cancelled', name='tab_status', create_type=False), server_default='open', nullable=False),

        sa.Column('opened_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('closed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- tab_splits table (1 row per person in split bill) ---
    op.create_table(
        'tab_splits',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tab_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tabs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),

        sa.Column('label', sa.String(), nullable=False),  # "Tamu 1", "Tamu 2", or person name
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', postgresql.ENUM('unpaid', 'pending', 'paid', name='tab_split_status', create_type=False), server_default='unpaid', nullable=False),

        # Items assigned to this split (for per_item split) — array of order_item IDs
        sa.Column('item_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # --- Add tab_id FK to orders table ---
    op.add_column('orders', sa.Column('tab_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tabs.id', ondelete='SET NULL'), nullable=True))


def downgrade():
    op.drop_column('orders', 'tab_id')
    op.drop_table('tab_splits')
    op.drop_table('tabs')
    op.execute("DROP TYPE tab_split_status")
    op.execute("DROP TYPE split_method")
    op.execute("DROP TYPE tab_status")
