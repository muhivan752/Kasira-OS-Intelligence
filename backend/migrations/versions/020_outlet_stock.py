"""outlet_stock

Revision ID: 020
Revises: 019
Create Date: 2026-03-20 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'outlet_stock',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('crdt_positive', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('crdt_negative', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('computed_stock', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('min_stock_base', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_check_constraint('chk_outlet_stock_computed', 'outlet_stock', 'computed_stock >= 0')

def downgrade():
    op.drop_table('outlet_stock')
