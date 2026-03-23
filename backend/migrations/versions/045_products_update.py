"""products_update

Revision ID: 045
Revises: 044
Create Date: 2026-03-20 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '045'
down_revision = '044'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('products', sa.Column('sku', sa.String(), nullable=True))
    op.add_column('products', sa.Column('barcode', sa.String(), nullable=True))
    op.add_column('products', sa.Column('is_subscription', sa.Boolean(), server_default='false', nullable=False))
    
    op.create_index('ix_products_sku', 'products', ['sku'], unique=True, postgresql_where=sa.text("sku IS NOT NULL AND deleted_at IS NULL"))
    op.create_index('ix_products_barcode', 'products', ['barcode'], unique=True, postgresql_where=sa.text("barcode IS NOT NULL AND deleted_at IS NULL"))

def downgrade():
    op.drop_index('ix_products_barcode', table_name='products')
    op.drop_index('ix_products_sku', table_name='products')
    op.drop_column('products', 'is_subscription')
    op.drop_column('products', 'barcode')
    op.drop_column('products', 'sku')
