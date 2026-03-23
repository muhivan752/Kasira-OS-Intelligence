"""payments_update

Revision ID: 049
Revises: 048
Create Date: 2026-03-20 10:49:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '049'
down_revision = '048'
branch_labels = None
depends_on = None

def upgrade():
    # Make order_id nullable because payments can now be for invoices/subscriptions
    op.alter_column('payments', 'order_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    
    # Add invoice_id
    op.add_column('payments', sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id', ondelete='SET NULL'), nullable=True))
    
    # Add is_partial
    op.add_column('payments', sa.Column('is_partial', sa.Boolean(), server_default='false', nullable=False))

def downgrade():
    op.drop_column('payments', 'is_partial')
    op.drop_constraint('payments_invoice_id_fkey', 'payments', type_='foreignkey')
    op.drop_column('payments', 'invoice_id')
    
    # This might fail if there are null order_ids, but it's a downgrade
    op.alter_column('payments', 'order_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)
