"""ingredient_suppliers

Revision ID: 019
Revises: 018
Create Date: 2026-03-20 10:19:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE price_trend AS ENUM ('stable', 'rising', 'falling')")
    
    op.create_table(
        'ingredient_suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('typical_price_per_base_unit', sa.Numeric(12, 2), nullable=True),
        sa.Column('typical_lead_days', sa.Integer(), nullable=True),
        sa.Column('is_preferred', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('last_purchased_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_purchase_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('price_trend', postgresql.ENUM('stable', 'rising', 'falling', name='price_trend', create_type=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('ingredient_suppliers')
    op.execute("DROP TYPE price_trend")
