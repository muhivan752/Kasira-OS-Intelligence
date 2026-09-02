"""CRM gelombang 3 (sisi data): segmen RFM, tag, timeline, voucher

Revision ID: 095
Revises: 094
Create Date: 2026-09-02 17:00:00.000000

`customers` selama ini cuma daftar nomor WA + angka belanja. Halaman
Pelanggan udah bisa nyaring "lapse / repeat / top" tapi dihitung ulang
tiap request dari total_visits/last_visit_at — nggak ada ingatan, nggak
ada aksi. Gelombang 3 sisi data:

- Segmen RFM DISIMPAN di `customers` (segment + angka RFM-nya), diisi
  `crm_service.refresh_segments` — dipanggil dari refresh-stats dan
  lazy waktu halaman dibuka kalau udah > 6 jam. Bahasa warung:
  baru / setia / vip / biasa / mulai_jarang / hilang.
- `customer_tags` + `customer_tag_links`: label bebas ("gak pakai gula",
  "kantor sebelah").
- `customer_timeline`: ingatan per pelanggan — catatan kasir, komplain,
  campaign terkirim, voucher dipakai. Sebagian diisi manual, sebagian sistem.
- `vouchers` + `voucher_redemptions`: diskon yang nyantol ke order dan
  ketahuan siapa yang pakai. Sekarang diskon cuma chip ad-hoc di POS.

Semua tabel baru bawa tenant_id langsung → RLS pola mig 069.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '095'
down_revision = '094'
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


def _base_cols():
    return [
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade():
    # ── customers: segmen + RFM + profil ──
    op.add_column('customers', sa.Column('segment', sa.String(20), nullable=True))
    op.add_column('customers', sa.Column('segment_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('customers', sa.Column('rfm_recency_days', sa.Integer(), nullable=True))
    op.add_column('customers', sa.Column('rfm_frequency_90d', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('customers', sa.Column('rfm_monetary_90d', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('customers', sa.Column('birthday', sa.Date(), nullable=True))
    op.add_column('customers', sa.Column('favorite_product_id', postgresql.UUID(as_uuid=True),
                                         sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_customers_tenant_segment', 'customers', ['tenant_id', 'segment'])

    # ── tags ──
    op.create_table(
        'customer_tags',
        *_base_cols(),
        sa.Column('name', sa.String(40), nullable=False),
        sa.Column('color', sa.String(20), nullable=False, server_default='violet'),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_customer_tags_tenant', 'customer_tags', ['tenant_id', 'deleted_at'])
    _rls('customer_tags')

    op.create_table(
        'customer_tag_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customer_tags.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('customer_id', 'tag_id', name='uq_customer_tag'),
    )
    op.create_index('ix_customer_tag_links_customer', 'customer_tag_links', ['customer_id'])
    _rls('customer_tag_links')

    # ── timeline ──
    op.create_table(
        'customer_timeline',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False, server_default='note'),
        sa.Column('ref_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('body', sa.String(500), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_customer_timeline_customer', 'customer_timeline', ['customer_id', 'created_at'])
    _rls('customer_timeline')

    # ── vouchers ──
    op.create_table(
        'vouchers',
        *_base_cols(),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('name', sa.String(80), nullable=True),
        sa.Column('kind', sa.String(12), nullable=False, server_default='percent'),
        sa.Column('value', sa.Numeric(12, 2), nullable=False),
        sa.Column('max_discount', sa.Numeric(12, 2), nullable=True),
        sa.Column('min_purchase', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('quota_total', sa.Integer(), nullable=True),
        sa.Column('quota_per_customer', sa.Integer(), nullable=True),
        sa.Column('segment', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='0'),
        sa.CheckConstraint("kind IN ('percent','amount')", name='chk_voucher_kind'),
        sa.CheckConstraint('value > 0', name='chk_voucher_value'),
    )
    op.create_index('uq_vouchers_tenant_code', 'vouchers', ['tenant_id', sa.text('upper(code)')], unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))
    _rls('vouchers')

    op.create_table(
        'voucher_redemptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('voucher_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vouchers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('discount_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_voucher_redemptions_voucher', 'voucher_redemptions', ['voucher_id', 'customer_id'])
    op.create_index('uq_voucher_redemptions_order', 'voucher_redemptions', ['voucher_id', 'order_id'], unique=True,
                    postgresql_where=sa.text('order_id IS NOT NULL'))
    _rls('voucher_redemptions')


def downgrade():
    op.drop_table('voucher_redemptions')
    op.drop_table('vouchers')
    op.drop_table('customer_timeline')
    op.drop_table('customer_tag_links')
    op.drop_table('customer_tags')
    op.drop_index('ix_customers_tenant_segment', table_name='customers')
    for c in ['favorite_product_id', 'birthday', 'rfm_monetary_90d', 'rfm_frequency_90d', 'rfm_recency_days', 'segment_updated_at', 'segment']:
        op.drop_column('customers', c)
