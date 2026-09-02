"""Promo WhatsApp (campaign) — dikirim dari nomor toko sendiri

Revision ID: 096
Revises: 095
Create Date: 2026-09-02 17:30:00.000000

Gelombang 3 sisi kirim. Pemilik nulis satu pesan, milih target (semua yang
kasih izin / segmen / tag), Selaris ngirim satu-satu lewat token Fonnte
milik outlet (`outlets.fonnte_token`, mig 094). Tiap pesan dicatat di
`campaign_messages` supaya kelihatan kekirim / gagal / ditolak, dan supaya
"balik dalam 7 hari" bisa dihitung belakangan dari orders.

Hanya ke pelanggan `wa_marketing_consent = true` — UU PDP. Nomor disimpan
utuh di sini karena emang dipakai buat kirim; laporan ke UI pakai mask.

Catatan urutan: 095 dipakai sesi CRM (segmen/tag). Kalau 095 belum ada
waktu ini jalan, ubah down_revision ke '094'.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '096'
down_revision = '095'
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
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('template', sa.Text(), nullable=False),
        # all | segment:<key> | tag:<uuid> — string biar nggak kunci ke tabel segmen
        sa.Column('target', sa.String(80), nullable=False, server_default='all'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recipient_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_campaigns_tenant', 'campaigns', ['tenant_id', 'deleted_at', 'created_at'])
    _rls('campaigns')

    op.create_table(
        'campaign_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('error', sa.String(200), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('campaign_id', 'customer_id', name='uq_campaign_customer'),
    )
    op.create_index('ix_campaign_messages_campaign', 'campaign_messages', ['campaign_id', 'status'])
    _rls('campaign_messages')


def downgrade():
    op.drop_table('campaign_messages')
    op.drop_table('campaigns')
