"""Metode pembayaran per toko + saluran QRIS (Xendit atau manual)

Revision ID: 103
Revises: 102
Create Date: 2026-09-04 04:00:00.000000

4415 pembayaran lunas di produksi, SEMUANYA tunai. Bukan karena pelanggan
warung nggak pakai QRIS: QRIS di app cuma jalan lewat Xendit BYOK dan nol
toko yang punya kuncinya, jadi QRIS statis dari bank/GoPay/DANA (mayoritas
UMKM) nggak punya tempat dicatat. Dicatat sebagai tunai atau nggak dicatat,
kas laci selisih tiap tutup shift.

- outlets.payment_methods: daftar metode yang toko aktifkan. Tunai selalu ada.
  App kasir dan storefront cuma nampilin yang aktif.
- outlets.qris_static_image_url: gambar QRIS milik toko, ditampilkan ke
  pelanggan, kasir konfirmasi sendiri sesudah lihat notifikasi bank.
- outlets.bank_*: rekening buat metode transfer.
- payments.channel: 'xendit' (QR dinamis, settle lewat webhook) atau 'manual'
  (kasir konfirmasi sendiri, settle langsung seperti tunai). NULL untuk baris
  lama = tunai/kartu/transfer yang memang manual.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '103'
down_revision = '102'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column(
        'payment_methods', postgresql.JSONB(astext_type=sa.Text()),
        nullable=False, server_default=sa.text("""'["cash", "qris"]'::jsonb"""),
    ))
    op.add_column('outlets', sa.Column('qris_static_image_url', sa.String(), nullable=True))
    op.add_column('outlets', sa.Column('bank_name', sa.String(60), nullable=True))
    op.add_column('outlets', sa.Column('bank_account_number', sa.String(40), nullable=True))
    op.add_column('outlets', sa.Column('bank_account_name', sa.String(80), nullable=True))
    op.add_column('payments', sa.Column('channel', sa.String(16), nullable=True))
    # Baris QRIS lama semuanya lewat Xendit (nggak ada jalur lain waktu itu).
    op.execute("UPDATE payments SET channel = 'xendit' WHERE payment_method = 'qris' AND channel IS NULL")


def downgrade():
    op.drop_column('payments', 'channel')
    op.drop_column('outlets', 'bank_account_name')
    op.drop_column('outlets', 'bank_account_number')
    op.drop_column('outlets', 'bank_name')
    op.drop_column('outlets', 'qris_static_image_url')
    op.drop_column('outlets', 'payment_methods')
