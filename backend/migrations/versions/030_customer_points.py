"""customer_points

Revision ID: 030
Revises: 029
Create Date: 2026-03-20 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None

def upgrade():
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

def downgrade():
    op.drop_table('customer_points')
