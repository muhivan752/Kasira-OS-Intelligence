"""Bukti bayar, DP reservasi, dan koordinat alamat antar

Revision ID: 104
Revises: 103
Create Date: 2026-09-04 06:00:00.000000

- payments.proof_image_url / proof_uploaded_at: bukti bayar yang pelanggan
  unggah dari halaman lacak (QRIS statis toko, DP reservasi, transfer).
  Sistem nggak pernah tahu uang masuk untuk saluran manual; bukti ini yang
  dilihat kasir sebelum menekan Terima/Konfirmasi.
- orders.delivery_lat/lng/distance_km: titik alamat antar dari Google Maps
  (Places Autocomplete lewat proxy backend). Kasir dapat tautan peta, toko
  bisa menolak di luar radius antar.

DP reservasi memakai kolom yang sudah ada sejak awal tapi belum pernah
dipakai: reservations.deposit_amount + deposit_payment_id, dan
reservation_settings.require_deposit + deposit_amount.
"""
from alembic import op
import sqlalchemy as sa

revision = '104'
down_revision = '103'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payments', sa.Column('proof_image_url', sa.String(), nullable=True))
    op.add_column('payments', sa.Column('proof_uploaded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('delivery_lat', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('delivery_lng', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('delivery_distance_km', sa.Numeric(6, 2), nullable=True))


def downgrade():
    op.drop_column('orders', 'delivery_distance_km')
    op.drop_column('orders', 'delivery_lng')
    op.drop_column('orders', 'delivery_lat')
    op.drop_column('payments', 'proof_uploaded_at')
    op.drop_column('payments', 'proof_image_url')
