"""supplier_price_history

Revision ID: 044
Revises: 043
Create Date: 2026-03-20 10:44:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '044'
down_revision = '043'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'supplier_price_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('new_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        # Append only
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('ix_supplier_price_history_supplier_ingredient', 'supplier_price_history', ['supplier_id', 'ingredient_id'])

def downgrade():
    op.drop_table('supplier_price_history')
