"""Layar dapur: status dapur terpisah dari status order

Revision ID: 102
Revises: 101
Create Date: 2026-09-03 19:00:00.000000

Status order (pending/preparing/ready/completed) dikendalikan pembayaran dan
kasir: pesanan kasir yang dibayar langsung jadi `completed`, jadi dapur
nggak pernah melihatnya kalau antrean dapur dibaca dari status order. Kolom
`kitchen_status` (NULL = belum disentuh dapur, 'preparing', 'ready', 'done')
bikin dapur punya papan sendiri tanpa mengubah alur bayar.
"""
from alembic import op
import sqlalchemy as sa

revision = '102'
down_revision = '101'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('kitchen_status', sa.String(12), nullable=True))
    op.create_index(
        'ix_orders_kitchen_open', 'orders', ['outlet_id', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL AND (kitchen_status IS NULL OR kitchen_status <> 'done')"),
    )


def downgrade():
    op.drop_index('ix_orders_kitchen_open', table_name='orders')
    op.drop_column('orders', 'kitchen_status')
