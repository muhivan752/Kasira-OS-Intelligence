"""purchase_orders

Revision ID: 028
Revises: 027
Create Date: 2026-03-20 10:28:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE po_status AS ENUM ('draft', 'sent', 'partial', 'received', 'cancelled')")

    op.create_table(
        'purchase_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('po_number', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('draft', 'sent', 'partial', 'received', 'cancelled', name='po_status', create_type=False), server_default='draft', nullable=False),
        sa.Column('expected_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_purchase_orders_outlet_id_po_number', 'purchase_orders', ['outlet_id', 'po_number'], unique=True)

def downgrade():
    op.drop_table('purchase_orders')
    op.execute("DROP TYPE po_status")
