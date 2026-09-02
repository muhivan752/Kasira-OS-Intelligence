"""Stok terjual melebihi tercatat: tanda + opname + selisih ke laba rugi

Revision ID: 100
Revises: 099
Create Date: 2026-09-03 02:00:00.000000

Dua HP offline bisa menjual "sisa 3" yang sama. Waktu keduanya sync, server
dulu diam-diam melewati pemotongan yang tidak cukup dan cuma nulis log.
Sekarang: sisa yang ada dipotong sampai 0, kekurangannya dicatat sebagai
event `stock.oversell` dan dimaterialisasi ke `products.oversell_qty` (sama
polanya dengan stock_qty: event = kebenaran, kolom = cache). Tanda itu hilang
lewat stok opname (`stock.count`), dan kalau hitung fisiknya lebih kecil dari
tercatat, selisihnya jadi beban `selisih_stok` di Keuangan.
"""
from alembic import op
import sqlalchemy as sa

revision = '100'
down_revision = '099'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('oversell_qty', sa.Integer(), server_default='0', nullable=False))


def downgrade():
    op.drop_column('products', 'oversell_qty')
