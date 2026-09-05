"""Delivery gelombang 2b: link tugas kurir tanpa app

Revision ID: 109
Revises: 108
Create Date: 2026-09-05 06:00:00.000000

Pertanyaan Ivan sesudah tes sebagai konsumen: "kalau kurirnya nggak ada
APK-nya, gimana dia mau foto?" Kurir orang toko nggak selalu punya app kasir
dan memang nggak boleh dipaksa punya. Jawabannya: waktu kasir menyerahkan
pesanan, kurir dapat WA berisi LINK tugas (alamat, peta, chat pelanggan,
tagihan COD, tombol Sampai dengan foto dari kamera HP lewat browser, tombol
Gagal antar). Halaman itu publik, dikunci `orders.delivery_token` acak
(bukan cuma UUID order, karena UUID order sudah beredar di link lacak
pelanggan dan pelanggan nggak boleh bisa menandai pesanannya sendiri sampai).
"""
from alembic import op
import sqlalchemy as sa

revision = '109'
down_revision = '108'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('delivery_token', sa.String(48), nullable=True))


def downgrade():
    op.drop_column('orders', 'delivery_token')
