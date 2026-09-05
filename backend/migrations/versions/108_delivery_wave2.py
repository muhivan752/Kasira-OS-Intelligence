"""Delivery gelombang 2: kurir toko, status antar, bukti serah terima

Revision ID: 108
Revises: 107
Create Date: 2026-09-05 05:00:00.000000

Latar (5 Sep 2026, keputusan Ivan): kurir di Selaris itu ORANG TOKO, bukan
armada agregator. Toko punya daftar kurirnya sendiri (anak, karyawan,
pemiliknya), pelanggan tahu siapa yang datang dan bisa chat langsung. Itu
pembedanya dari GrabFood/GoFood, sekaligus alasan tabelnya sesederhana ini:
nggak ada akun kurir, nggak ada aplikasi kurir, nggak ada bagi hasil.

- `couriers`: daftar kurir per outlet. `user_id` opsional buat kurir yang
  kebetulan punya akun kasir. RLS pola mig 069/093 lewat tenant_id.
- `orders.delivery_status`: NULL | assigned | on_the_way | delivered | failed.
  SENGAJA terpisah dari `orders.status`, alasan yang sama dengan
  `kitchen_status` (mig 102): `ready` itu "makanannya jadi", bukan "lagi di
  jalan", dan pesanan yang dibayar di muka bisa langsung `completed` tanpa
  dapur atau kurir pernah menyentuhnya.
- `orders.courier_name` di-SNAPSHOT waktu ditugaskan, bukan dibaca dari
  relasi. Kurir bisa berhenti kerja dan dihapus pemilik; riwayat bulan lalu
  tetap harus nulis siapa yang nganter (pelajaran nama varian, CLAUDE.md #26).
- `delivery_proof_url` + `delivery_received_by`: bukti serah terima. Opsional
  by design, kurir lagi hujan-hujanan nggak boleh kejebak wajib foto.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '108'
down_revision = '107'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'couriers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('vehicle', sa.String(20), nullable=False, server_default='motor'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_couriers_outlet', 'couriers', ['outlet_id', 'deleted_at'])
    op.create_index('ix_couriers_tenant', 'couriers', ['tenant_id', 'deleted_at'])
    op.execute("ALTER TABLE couriers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE couriers FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON couriers
        USING (
            current_setting('app.current_tenant_id', true) = ''
            OR tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    """)

    op.add_column('orders', sa.Column('courier_id', postgresql.UUID(as_uuid=True),
                                      sa.ForeignKey('couriers.id', ondelete='SET NULL'), nullable=True))
    op.add_column('orders', sa.Column('courier_name', sa.String(80), nullable=True))
    op.add_column('orders', sa.Column('delivery_status', sa.String(16), nullable=True))
    op.add_column('orders', sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('delivery_proof_url', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('delivery_received_by', sa.String(80), nullable=True))
    op.add_column('orders', sa.Column('delivery_failed_reason', sa.String(200), nullable=True))

    # Papan "yang lagi diantar" dibaca tiap beberapa detik dari app kasir.
    # Partial index: pesanan antar itu sebagian kecil dari seluruh orders.
    op.create_index(
        'ix_orders_delivery_active', 'orders', ['outlet_id', 'delivery_status'],
        postgresql_where=sa.text("delivery_status IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade():
    op.drop_index('ix_orders_delivery_active', table_name='orders')
    for c in ('delivery_failed_reason', 'delivery_received_by', 'delivery_proof_url', 'delivered_at',
              'dispatched_at', 'delivery_status', 'courier_name', 'courier_id'):
        op.drop_column('orders', c)
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON couriers")
    op.drop_index('ix_couriers_tenant', table_name='couriers')
    op.drop_index('ix_couriers_outlet', table_name='couriers')
    op.drop_table('couriers')
