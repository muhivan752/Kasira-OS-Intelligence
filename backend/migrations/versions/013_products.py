"""products

Revision ID: 013
Revises: 012
Create Date: 2026-03-20 10:13:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None

def upgrade():
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('order_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('stock_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('stock_qty', sa.Integer(), server_default='0', nullable=False),
        sa.Column('stock_low_threshold', sa.Integer(), server_default='5', nullable=False),
        sa.Column('stock_auto_hide', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('sold_today', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sold_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_restock_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_check_constraint('chk_products_stock_qty', 'products', 'stock_qty >= 0')
    
    # Add vector column for semantic search
    op.execute("ALTER TABLE products ADD COLUMN embedding vector(1536)")

def downgrade():
    op.drop_table('products')
    op.execute("DROP EXTENSION IF EXISTS vector")
