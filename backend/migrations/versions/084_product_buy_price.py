"""Add buy_price to products for Starter margin tracking

Revision ID: 084
Revises: 083
Create Date: 2026-04-24

Tambah `products.buy_price` (Numeric(12,2) NULL) untuk enable margin
tracking di Starter tier + Pro outlet `stock_mode='simple'`.

Pattern mirror dari `ingredients.buy_price` (migration 066) — snapshot
harga beli terakhir, bukan moving average. Kalau outlet Pro pakai
`stock_mode='recipe'`, field ini di-ignore (margin tetap dihitung dari
recipe HPP via `unit_utils.py`).

Backward compat: nullable, no default — produk existing tetap valid.
APK lama (v1.0.38) yang belum kenal field ini akan skip waktu sync.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '084'
down_revision = '083'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'products',
        sa.Column('buy_price', sa.Numeric(12, 2), nullable=True),
    )


def downgrade():
    op.drop_column('products', 'buy_price')
