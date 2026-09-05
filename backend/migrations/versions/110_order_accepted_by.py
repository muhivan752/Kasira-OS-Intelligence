"""Siapa kasir yang menerima pesanan online

Revision ID: 110
Revises: 109
Create Date: 2026-09-05 07:00:00.000000

Pertanyaan Ivan: kalau 3 kasir sama-sama pegang app dan satu pesanan online
masuk, bentrok nggak? Dua hal yang dibenerin bareng migrasi ini:

1. Race beneran: endpoint accept/reject/dispatch/delivered dulu baca order
   dengan SELECT biasa, jadi dua kasir bisa sama-sama lolos cek "masih
   pending" sebelum salah satunya commit. Sekarang barisnya dikunci
   (FOR UPDATE), jadi yang kedua nunggu lalu lihat status yang sudah berubah.
2. Kasir yang kalah cepat cuma dikasih "Pesanan ini sudah diproses" warna
   merah. `accepted_by` bikin pesannya jadi "sudah diterima Budi" dan kartu
   di semua HP nulis siapa yang pegang.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '110'
down_revision = '109'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('accepted_by', postgresql.UUID(as_uuid=True),
                                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))


def downgrade():
    op.drop_column('orders', 'accepted_by')
