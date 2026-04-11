"""Add buy_price and buy_qty to ingredients for auto cost calculation

Revision ID: 066
Revises: 065
Create Date: 2026-04-11 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '066'
down_revision = '065'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('ingredients', sa.Column('buy_price', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('ingredients', sa.Column('buy_qty', sa.Float(), server_default='1', nullable=False))

    # Backfill: set buy_price = cost_per_base_unit, buy_qty = 1 for existing rows
    # so cost_per_base_unit = buy_price / buy_qty stays consistent
    op.execute("""
        UPDATE ingredients
        SET buy_price = cost_per_base_unit, buy_qty = 1
        WHERE cost_per_base_unit > 0
    """)


def downgrade() -> None:
    op.drop_column('ingredients', 'buy_qty')
    op.drop_column('ingredients', 'buy_price')
