"""add missing row versions

Revision ID: 052_missing_row_versions
Revises: 051_payment_refunds
Create Date: 2026-03-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '052_missing_row_versions'
down_revision = '051_payment_refunds'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add row_version to categories
    op.add_column('categories', sa.Column('row_version', sa.Integer(), server_default='0', nullable=False))
    
    # Add row_version to product_variants
    op.add_column('product_variants', sa.Column('row_version', sa.Integer(), server_default='0', nullable=False))
    
    # Add row_version to customers
    op.add_column('customers', sa.Column('row_version', sa.Integer(), server_default='0', nullable=False))
    
    # Add row_version to shifts
    op.add_column('shifts', sa.Column('row_version', sa.Integer(), server_default='0', nullable=False))
    
    # Add row_version to order_items
    op.add_column('order_items', sa.Column('row_version', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('order_items', 'row_version')
    op.drop_column('shifts', 'row_version')
    op.drop_column('customers', 'row_version')
    op.drop_column('product_variants', 'row_version')
    op.drop_column('categories', 'row_version')
