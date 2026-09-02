"""Nomor WhatsApp toko (storefront) + token Fonnte per outlet (promo WA)

Revision ID: 094
Revises: 093
Create Date: 2026-09-02 16:30:00.000000

- `whatsapp_number`: tombol "Hubungi via WhatsApp" di storefront dulu pakai
  `outlet.phone` yang di-MASK di API publik ("0852***220") → link wa.me-nya
  rusak sejak lahir. Sekarang nomor WA toko kolom sendiri, dikirim utuh ke
  storefront (memang buat dihubungi), diisi pemilik di Pengaturan.
- `fonnte_token`: promo/campaign WA (gelombang 3) dikirim dari NOMOR TOKO
  SENDIRI (keputusan Ivan: "pakai no user masing-masing"), mirror BYOK
  Xendit. Terenkripsi at rest (EncryptedString). OTP + struk tetap token
  platform.
"""
from alembic import op
import sqlalchemy as sa

revision = '094'
down_revision = '093'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column('whatsapp_number', sa.String(20), nullable=True))
    op.add_column('outlets', sa.Column('fonnte_token', sa.String(), nullable=True))


def downgrade():
    op.drop_column('outlets', 'fonnte_token')
    op.drop_column('outlets', 'whatsapp_number')
