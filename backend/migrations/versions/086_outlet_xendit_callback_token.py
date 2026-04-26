"""outlet xendit callback token (BYOK Phase 2)

Revision ID: 086
Revises: 085
Create Date: 2026-04-26

Per-outlet callback token utk verify webhook BYOK merchant. Disimpan
encrypted via EncryptedString TypeDecorator (mirror xendit_api_key
Migration 080 pattern). Nullable — outlet sub-account / belum konfigurasi
BYOK fall back ke master settings.XENDIT_WEBHOOK_TOKEN.

Phase 2 wire-up (per-merchant webhook verify) DEFERRED — sampai 1 BYOK
merchant beneran onboard. Sekarang field dipakai cuma untuk store di UI
Settings; webhook handler tetap pakai master token.
"""
from alembic import op
import sqlalchemy as sa


revision = '086'
down_revision = '085'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('outlets')]
    # Idempotent — gak duplicate kalau migration jalan ulang.
    # String type plain (bukan EncryptedString custom type) di migration —
    # encryption transparent via TypeDecorator di model layer (sama pattern
    # xendit_api_key Migration 080).
    if 'xendit_callback_token' not in columns:
        op.add_column('outlets', sa.Column('xendit_callback_token', sa.String(), nullable=True))


def downgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('outlets')]
    if 'xendit_callback_token' in columns:
        op.drop_column('outlets', 'xendit_callback_token')
