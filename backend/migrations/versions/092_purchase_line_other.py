"""Baris nota tanpa target stok — gas, plastik, tisu ikut kecatat

Revision ID: 092
Revises: 091
Create Date: 2026-09-02 14:30:00.000000

Nota pasar hampir selalu nyampur: bahan resep (susu, kopi) + barang yang
bukan stok (gas, kantong plastik, tisu, parkir). Mig 091 maksa tiap baris
nunjuk ingredient ATAU product, jadi baris "lainnya" gak bisa dicatat dan
total nota jadi bohong (utang supplier kurang dari yang sebenarnya).

Sekarang baris boleh berdiri sendiri dengan `name_snapshot` saja: gak
nyentuh stok, tetap masuk total + utang, dan jadi bahan "pengeluaran" di
gelombang 2 (ledger). CHECK diganti jadi salah satu dari tiga.
"""
from alembic import op

revision = '092'
down_revision = '091'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('chk_poi_target', 'purchase_order_items', type_='check')
    op.create_check_constraint(
        'chk_poi_target',
        'purchase_order_items',
        'ingredient_id IS NOT NULL OR product_id IS NOT NULL OR name_snapshot IS NOT NULL',
    )


def downgrade():
    op.drop_constraint('chk_poi_target', 'purchase_order_items', type_='check')
    op.create_check_constraint(
        'chk_poi_target',
        'purchase_order_items',
        'ingredient_id IS NOT NULL OR product_id IS NOT NULL',
    )
