"""Profil Ketat: laci dikunci ke satu kasir (lockdown)

Revision ID: 099
Revises: 098
Create Date: 2026-09-03 01:00:00.000000

Gelombang tiga shift otomatis. Rujukan "cash drawer lockdown" Toast: laci
dikunci ke karyawan yang membukanya; hanya dia yang bisa bertransaksi di
situ, pemilik bisa menerobos. Serah terima = jeda (hitung nanti) atau tutup,
lalu kasir berikutnya membuka dengan modal awal. Di profil Ketat sesi TIDAK
terbuka sendiri — itu memang intinya.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '099'
down_revision = '098'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shifts', sa.Column('locked_user_id', postgresql.UUID(as_uuid=True),
                                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))


def downgrade():
    op.drop_column('shifts', 'locked_user_id')
