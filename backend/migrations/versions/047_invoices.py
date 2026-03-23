"""invoices

Revision ID: 047
Revises: 046
Create Date: 2026-03-20 10:47:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '047'
down_revision = '046'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE invoice_status AS ENUM ('draft', 'open', 'paid', 'void', 'uncollectible')")

    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('draft', 'open', 'paid', 'void', 'uncollectible', name='invoice_status', create_type=False), server_default='draft', nullable=False),
        sa.Column('amount_due', sa.Numeric(12, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('amount_remaining', sa.Numeric(12, 2), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False), # Wajib row_version
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.UniqueConstraint('invoice_number', name='uq_invoice_number')
    )

def downgrade():
    op.drop_table('invoices')
    op.execute("DROP TYPE invoice_status")
