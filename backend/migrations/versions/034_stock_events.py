"""stock_events

Revision ID: 034
Revises: 033
Create Date: 2026-03-20 10:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE stock_event_type AS ENUM ('receive', 'consume', 'waste', 'adjustment', 'transfer_in', 'transfer_out')")

    op.create_table(
        'stock_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', postgresql.ENUM('receive', 'consume', 'waste', 'adjustment', 'transfer_in', 'transfer_out', name='stock_event_type', create_type=False), nullable=False),
        sa.Column('quantity_change', sa.Numeric(12, 4), nullable=False),
        sa.Column('balance_after', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('reference_type', sa.String(), nullable=True), # e.g., 'purchase_order', 'order', 'manual'
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_stock_events_outlet_ingredient', 'stock_events', ['outlet_id', 'ingredient_id'])
    op.create_index('ix_stock_events_reference', 'stock_events', ['reference_type', 'reference_id'])

def downgrade():
    op.drop_table('stock_events')
    op.execute("DROP TYPE stock_event_type")
