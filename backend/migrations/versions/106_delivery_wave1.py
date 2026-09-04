"""Delivery gelombang 1: ongkir + jam buka beneran

Revision ID: 106
Revises: 105
Create Date: 2026-09-04 14:00:00.000000

Latar (4 Sep 2026): pelanggan bisa isi alamat antar, jaraknya dihitung,
di luar radius ditolak, tapi ongkirnya nol dan nggak ada yang nagih. Jam
buka cuma teks bebas yang dipajang, toko nggak pernah tutup sendiri.

- outlets.delivery_*: tarif antar milik toko. fee = base + per_km × km
  di atas free_km, dibulatkan ke atas ke Rp 500 (services/delivery_service).
  min_order = subtotal minimal supaya boleh diantar.
- orders.delivery_fee: ongkir TERPISAH dari total_amount. total_amount tetap
  = penjualan (belasan modul laporan membacanya begitu). Yang ditagih ke
  pelanggan = total_amount + delivery_fee (Payment.amount_due).
- outlets.business_hours + hours_mode: jadwal mingguan
  {mon: [["08:00","22:00"]], ...}. 'schedule' = buka/tutup ikut jadwal
  (is_open tetap saklar induk buat tutup mendadak). opening_hours teks lama
  tetap ada buat tampilan.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column('delivery_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('outlets', sa.Column('delivery_fee_base', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('outlets', sa.Column('delivery_fee_per_km', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('outlets', sa.Column('delivery_free_km', sa.Numeric(5, 1), server_default='0', nullable=False))
    op.add_column('outlets', sa.Column('delivery_min_order', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('outlets', sa.Column('business_hours', JSONB(), nullable=True))
    op.add_column('outlets', sa.Column('hours_mode', sa.String(10), server_default='manual', nullable=False))
    op.add_column('orders', sa.Column('delivery_fee', sa.Numeric(12, 2), server_default='0', nullable=False))


def downgrade():
    op.drop_column('orders', 'delivery_fee')
    for c in ('hours_mode', 'business_hours', 'delivery_min_order', 'delivery_free_km',
              'delivery_fee_per_km', 'delivery_fee_base', 'delivery_enabled'):
        op.drop_column('outlets', c)
