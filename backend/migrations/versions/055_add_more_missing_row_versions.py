"""add more missing row versions

Revision ID: 055_more_missing_row_versions
Revises: 054_add_shift_session_id_to_payments
Create Date: 2026-03-22 10:36:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '055_more_missing_row_versions'
down_revision = '054_add_shift_session_id_to_payments'
branch_labels = None
depends_on = None

def upgrade() -> None:
    tables_to_add = [
        'roles',
        'sessions',
        'devices',
        'suppliers',
        'outlet_tax_config',
        'modifiers',
        'outlet_product_overrides',
        'ingredients',
        'ingredient_units',
        'ingredient_suppliers',
        'recipes',
        'recipe_ingredients',
        'pricing_rules',
        'purchase_order_items',
        'stock_snapshots',
        'events',
        'outlet_location_detail',
        'subscription_payments',
        'partial_payments',
        'payment_refunds'
    ]
    
    for table in tables_to_add:
        op.add_column(table, sa.Column('row_version', sa.Integer(), server_default='0', nullable=False))

def downgrade() -> None:
    tables_to_add = [
        'roles',
        'sessions',
        'devices',
        'suppliers',
        'outlet_tax_config',
        'modifiers',
        'outlet_product_overrides',
        'ingredients',
        'ingredient_units',
        'ingredient_suppliers',
        'recipes',
        'recipe_ingredients',
        'pricing_rules',
        'purchase_order_items',
        'stock_snapshots',
        'events',
        'outlet_location_detail',
        'subscription_payments',
        'partial_payments',
        'payment_refunds'
    ]
    
    for table in tables_to_add:
        op.drop_column(table, 'row_version')
