"""product_variants dihidupkan — is_active + sort_order + index

Revision ID: 090
Revises: 089
Create Date: 2026-07-22 13:10:00.000000

Tabel `product_variants` dibikin di migration 014 lalu **ditinggal**: nggak
pernah ada route CRUD, schema, sync, maupun UI. Nol baris di produksi. Efeknya
merchant nggak bisa nawarin Hot/Ice, size, atau level gula sama sekali —
kepaksa bikin dua produk terpisah "Kopi Hot" + "Kopi Ice" yang bikin resep dan
stok kembar dua.

Migration ini nyiapin tabelnya buat dipakai beneran:

- `is_active` — varian bisa dinonaktifkan sementara (es batu habis) tanpa
  dihapus. Beda dari `deleted_at`: order lama tetap boleh nunjuk varian yang
  udah nggak dijual, jadi hard delete nggak boleh (Rule #7).
- `sort_order` — urutan tampil di POS ditentukan pemilik, bukan alfabet.
  "Panas" biasanya pengin di kiri walau "Dingin" lebih dulu secara abjad.
- Index `(product_id, deleted_at)` — POS narik varian per produk tiap kali
  kartu produk di-tap.

`row_version` sudah ditambahkan migration 052, jadi nggak diulang di sini.
"""
from alembic import op
import sqlalchemy as sa

revision = '090'
down_revision = '089'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'product_variants',
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    )
    op.add_column(
        'product_variants',
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_index(
        'ix_product_variants_product',
        'product_variants',
        ['product_id', 'deleted_at'],
    )


def downgrade():
    op.drop_index('ix_product_variants_product', table_name='product_variants')
    op.drop_column('product_variants', 'sort_order')
    op.drop_column('product_variants', 'is_active')
