"""Antar: toko memilih terima bayar di tempat (COD) atau wajib bayar dulu

Revision ID: 107
Revises: 106
Create Date: 2026-09-04 16:00:00.000000

Ivan 4 Sep malam: pilihan COD vs bayar dulu harus jelas buat pelanggan, dan
toko harus bisa mematikan COD (pesanan fiktif). delivery_cod_enabled default
true = perilaku sebelumnya. False = storefront menyembunyikan tunai untuk
antar, server menolak tunai+antar dengan 400.
"""
from alembic import op
import sqlalchemy as sa

revision = '107'
down_revision = '106'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column('delivery_cod_enabled', sa.Boolean(), server_default='true', nullable=False))


def downgrade():
    op.drop_column('outlets', 'delivery_cod_enabled')
