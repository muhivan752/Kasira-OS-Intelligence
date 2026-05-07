"""receipt idempotency on payment

Revision ID: 087
Revises: 086
Create Date: 2026-05-07

Tambah `payments.receipt_printed_at` TIMESTAMPTZ NULL untuk receipt
idempotency. Dipakai sama print path (Flutter autoprint via /orders/
{id}/receipt + tab variants) — sebelum print, check `receipt_printed_at
IS NULL`. Set timestamp setelah print sukses. Cegah double-print:
- Webhook double-deliver → autoprint fire 2x
- Cashier retry tap → autoprint fire 2x
- Background sync stale state → autoprint fire 2x

Manual reprint (cashier opens order detail, taps "Cetak Ulang") TETAP
allowed. Field ini cuma block AUTO-print path.

Backward compat: nullable, no default. Existing payments preserved.
"""

from alembic import op
import sqlalchemy as sa


revision = '087'
down_revision = '086'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'payments',
        sa.Column('receipt_printed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('payments', 'receipt_printed_at')
