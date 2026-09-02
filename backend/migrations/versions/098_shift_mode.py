"""Mode kas per outlet: ringan / standar / ketat

Revision ID: 098
Revises: 097
Create Date: 2026-09-03 00:10:00.000000

Gelombang dua shift otomatis. Satu mesin, tiga profil, nempel di OUTLET
(bukan tier): Business dengan lima outlet bisa punya kios yang Ringan dan
flagship yang Ketat dalam satu akun. Default-nya ikut tier waktu migrasi
jalan: Starter → ringan, Pro/Business/Enterprise → standar. Pemilik boleh
ganti kapan saja dari Pengaturan.

- ringan : sesi otomatis, hitung kas opsional, kasir lihat angka sistem
- standar: sesi otomatis, pengingat "kas belum dihitung", blind close
           (kasir mengetik hitungan tanpa lihat angka harapan; pemilik
           tetap lihat semua)
- ketat  : + buka manual dengan serah terima, laci per kasir (gelombang 3)
"""
from alembic import op
import sqlalchemy as sa

revision = '098'
down_revision = '097'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column('shift_mode', sa.String(length=12), server_default='ringan', nullable=False))
    op.execute("""
        UPDATE outlets o
           SET shift_mode = 'standar'
          FROM tenants t
         WHERE t.id = o.tenant_id
           AND t.subscription_tier::text IN ('pro', 'business', 'enterprise')
    """)


def downgrade():
    op.drop_column('outlets', 'shift_mode')
