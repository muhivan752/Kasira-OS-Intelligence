"""Keuangan ringan — pengeluaran + akun kas (gelombang 2)

Revision ID: 093
Revises: 092
Create Date: 2026-09-02 15:00:00.000000

Sebelum ini "keuangan" Kasira = shifts + cash_activities (kas kecil per
shift kasir). Sewa, listrik, gaji, gas — beban tenant-level — nggak punya
tempat, jadi laba rugi nggak pernah bisa dihitung; pemilik cuma lihat omzet.

Dua tabel, dua-duanya `tenant_id` langsung (RLS pola mig 069):
- `expenses`   — satu baris per pengeluaran. Kategori string tetap (bukan
                 tabel) biar nol setup: sewa, listrik_air, gaji, bahan, gas,
                 perlengkapan, marketing, peralatan, lainnya. `purchase_id`
                 keisi kalau barisnya lahir dari nota belanja ("Lainnya") —
                 supaya arus kas nggak dobel hitung sama pembayaran nota.
                 `recurring='monthly'` = template yang bisa disalin tiap bulan.
- `cash_accounts` — "uangnya ada di mana": Kas Laci, Rekening Bank,
                 QRIS/Xendit. `default_for` = metode bayar yang otomatis
                 masuk ke akun ini (cash / transfer,card / qris).

SENGAJA nggak bikin tabel ledger/journal: arus kas & laba rugi dihitung
langsung dari payments, payment_refunds, purchase_orders, expenses,
cash_activities di `finance_service`. Satu sumber, nol drift, nol background
task RLS (gotcha #16). Materialisasi nanti kalau query-nya mulai lambat.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '093'
down_revision = '092'
branch_labels = None
depends_on = None


def _rls(table: str):
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (
            current_setting('app.current_tenant_id', true) = ''
            OR tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    """)


def upgrade():
    op.create_table(
        'cash_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False, server_default='cash_drawer'),
        sa.Column('default_for', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('opening_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_cash_accounts_tenant', 'cash_accounts', ['tenant_id', 'deleted_at'])
    _rls('cash_accounts')

    op.create_table(
        'expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True),
        sa.Column('category', sa.String(40), nullable=False, server_default='lainnya'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payment_method', sa.String(20), nullable=False, server_default='cash'),
        sa.Column('cash_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cash_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('purchase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=True),
        sa.Column('note', sa.String(200), nullable=True),
        sa.Column('photo_url', sa.String(), nullable=True),
        sa.Column('recurring', sa.String(10), nullable=False, server_default='none'),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('amount > 0', name='chk_expenses_amount_positive'),
    )
    op.create_index('ix_expenses_tenant_paid', 'expenses', ['tenant_id', 'deleted_at', 'paid_at'])
    op.create_index('ix_expenses_purchase', 'expenses', ['purchase_id'])
    _rls('expenses')


def downgrade():
    op.drop_table('expenses')
    op.drop_table('cash_accounts')
