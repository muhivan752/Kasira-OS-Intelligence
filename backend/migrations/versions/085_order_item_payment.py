"""Add per-item payment tracking to order_items (warkop ad-hoc pattern)

Revision ID: 085
Revises: 084
Create Date: 2026-04-25

Tambah `order_items.paid_at` TIMESTAMPTZ NULL + `paid_payment_id` UUID NULL
FK→payments untuk enable per-item ad-hoc payment (Indonesian warkop pattern).

Mental model: 1 meja = pool of items, customer bayar items yg dia sebut tanpa
pre-defined split. Beda dari existing TabSplit (patungan-style) — ini per-item
payment standalone tanpa person attribution.

Backward compat:
- Nullable, no default — items existing tetap valid
- CHECK constraint: kalau paid_at terisi, paid_payment_id WAJIB ada (consistency)
- Existing completed orders: paid_at NULL preserved. Order.status='completed' tetap
  jadi source of truth untuk historical analytics. Ad-hoc payment cuma di-trigger
  pada items dari order yang masih hidup di tab aktif (post-migration usage).
- Existing active tabs (saat migrate live): items.paid_at NULL → tetap pakai
  tab+split mechanism existing → transition smooth. Ad-hoc payment available
  for new tabs going forward.

Refund flow: refund hook di payments revert paid_at NULL + recalc tab. Item
balik ke "unpaid pool" — kasir bisa rebill.
"""

from alembic import op
import sqlalchemy as sa


revision = '085'
down_revision = '084'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'order_items',
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'order_items',
        sa.Column(
            'paid_payment_id',
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey('payments.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        'ck_order_items_paid_consistency',
        'order_items',
        '(paid_at IS NULL) OR (paid_payment_id IS NOT NULL)',
    )
    op.create_index(
        'idx_order_items_paid_payment',
        'order_items',
        ['paid_payment_id'],
        postgresql_where=sa.text('paid_payment_id IS NOT NULL'),
    )


def downgrade():
    op.drop_index('idx_order_items_paid_payment', table_name='order_items')
    op.drop_constraint('ck_order_items_paid_consistency', 'order_items', type_='check')
    op.drop_column('order_items', 'paid_payment_id')
    op.drop_column('order_items', 'paid_at')
