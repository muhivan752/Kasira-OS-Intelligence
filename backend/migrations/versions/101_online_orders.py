"""Pesanan online: sumber order, konfirmasi toko, auto-batal, toggle per outlet

Revision ID: 101
Revises: 100
Create Date: 2026-09-03 10:00:00.000000

Sebelum ini order dari storefront nggak bisa dibedakan dari order kasir
(sumbernya cuma ada di payload event), langsung lompat ke `preparing` tanpa
ada yang nerima, dan merchant nggak dikabari sama sekali. Sekarang:

- `orders.source` ('pos' | 'storefront'): dasar badge, filter, notifikasi.
- `orders.accepted_at` + `eta_minutes`: toko mengonfirmasi dan memberi
  perkiraan. `ready_at`: kapan ditandai siap. `cancel_reason`: alasan yang
  dibaca pelanggan di halaman lacak.
- `orders.delivery_address`: dulu diselipkan ke `notes` sebagai teks
  "Delivery Address: ..." dan catatan pelanggan sendiri hilang.
- `outlets.online_orders_enabled` (tutup sementara pesanan online tanpa
  menutup toko), `online_notify_owner_wa` (WA cadangan ke pemilik),
  `online_auto_cancel_minutes` (batas konfirmasi, default 10).
- `outlets.kitchen_mode` sudah ada di DB sejak mig 003 tapi nggak pernah
  dipetakan ke model. Dipetakan sekarang, tanpa perubahan skema.
"""
from alembic import op
import sqlalchemy as sa

revision = '101'
down_revision = '100'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('source', sa.String(16), server_default='pos', nullable=False))
    op.add_column('orders', sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('eta_minutes', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('cancel_reason', sa.String(200), nullable=True))
    op.add_column('orders', sa.Column('delivery_address', sa.Text(), nullable=True))
    op.execute("""
        UPDATE orders SET source = 'storefront'
        WHERE id IN (SELECT order_id FROM connect_orders WHERE order_id IS NOT NULL)
    """)
    op.execute("""
        UPDATE orders
        SET delivery_address = substr(notes, length('Delivery Address: ') + 1),
            notes = NULL
        WHERE source = 'storefront' AND notes LIKE 'Delivery Address: %'
    """)
    op.create_index(
        'ix_orders_outlet_source_status', 'orders', ['outlet_id', 'source', 'status'],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.add_column('outlets', sa.Column('online_orders_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('outlets', sa.Column('online_notify_owner_wa', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('outlets', sa.Column('online_auto_cancel_minutes', sa.Integer(), server_default='10', nullable=False))


def downgrade():
    op.drop_column('outlets', 'online_auto_cancel_minutes')
    op.drop_column('outlets', 'online_notify_owner_wa')
    op.drop_column('outlets', 'online_orders_enabled')
    op.drop_index('ix_orders_outlet_source_status', table_name='orders')
    op.drop_column('orders', 'delivery_address')
    op.drop_column('orders', 'cancel_reason')
    op.drop_column('orders', 'ready_at')
    op.drop_column('orders', 'eta_minutes')
    op.drop_column('orders', 'accepted_at')
    op.drop_column('orders', 'source')
