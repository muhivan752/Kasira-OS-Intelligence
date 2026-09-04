"""Toko bisa ditemukan: izin tampil di direktori publik & sitemap

Revision ID: 105
Revises: 104
Create Date: 2026-09-04 13:00:00.000000

Latar (4 Sep 2026): storefront cuma bisa ditemukan kalau pemilik nyebar
link-nya sendiri. `app/sitemap.ts` nembak `/outlets/public/list` yang nggak
pernah ada (404), jadi nol toko yang pernah dikasih tahu ke Google.

outlets.directory_listed = pemilik mengizinkan tokonya tampil di halaman
/jelajah dan sitemap. Default true (toko baru langsung bisa ditemukan),
tapi ini keputusan pemilik: ada usaha yang nggak mau dipajang di direktori
umum. Akun uji beban dan smoke test dimatikan di sini supaya nggak ikut
dipajang.
"""
from alembic import op
import sqlalchemy as sa

revision = '105'
down_revision = '104'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column('directory_listed', sa.Boolean(), server_default='true', nullable=False))
    # Akun uji jangan nongol di direktori publik.
    op.execute("""
        UPDATE outlets SET directory_listed = false
        WHERE slug LIKE 'loadtest-%' OR slug LIKE 'smoke-%'
    """)


def downgrade():
    op.drop_column('outlets', 'directory_listed')
