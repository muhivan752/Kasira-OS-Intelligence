"""encrypt existing xendit_api_key values (AES-256-GCM)

Revision ID: 080
Revises: 079
Create Date: 2026-04-19

Security audit CRITICAL #1 fix: `outlets.xendit_api_key` saat ini disimpan
plaintext. Migration ini backfill encrypt existing values pakai AES-256-GCM
helper dari `backend/utils/encryption.py`.

Idempotent: skip values yang sudah punya `v1:` prefix (already encrypted).
Skip juga legacy Fernet format (`gAAAA` prefix) — decrypt path support.

Setelah migration ini apply, `models/outlet.py` pakai `EncryptedString`
TypeDecorator — write/read transparent. Zero change di `outlets.py` /
`connect.py` route files.

Per production state per 2026-04-19: 0 outlet punya xendit_api_key.
Migration jadi no-op sekarang, tapi defensive untuk future deploys.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '080'
down_revision = '079'
branch_labels = None
depends_on = None


def upgrade():
    """Encrypt existing plaintext xendit_api_key values."""
    from backend.utils.encryption import encrypt_field, _VERSION_PREFIX, _LEGACY_FERNET_PREFIX

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, xendit_api_key FROM outlets "
        "WHERE xendit_api_key IS NOT NULL AND xendit_api_key != ''"
    )).fetchall()

    encrypted_count = 0
    skipped_count = 0

    for row in rows:
        value = row.xendit_api_key
        if value.startswith(_VERSION_PREFIX) or value.startswith(_LEGACY_FERNET_PREFIX):
            skipped_count += 1
            continue
        encrypted = encrypt_field(value)
        conn.execute(
            sa.text("UPDATE outlets SET xendit_api_key = :val WHERE id = :id"),
            {"val": encrypted, "id": str(row.id)}
        )
        encrypted_count += 1

    print(f"Migration 080: encrypted {encrypted_count} xendit_api_key values, "
          f"skipped {skipped_count} (already encrypted)")


def downgrade():
    """
    Decrypt back to plaintext — EMERGENCY rollback only.
    Butuh ENCRYPTION_KEY yang sama dengan saat encrypt (kalau key hilang,
    downgrade akan fail decrypt).
    """
    from backend.utils.encryption import decrypt_field, _VERSION_PREFIX

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, xendit_api_key FROM outlets "
        "WHERE xendit_api_key IS NOT NULL AND xendit_api_key != ''"
    )).fetchall()

    decrypted_count = 0
    for row in rows:
        value = row.xendit_api_key
        if not value.startswith(_VERSION_PREFIX):
            continue
        decrypted = decrypt_field(value)
        conn.execute(
            sa.text("UPDATE outlets SET xendit_api_key = :val WHERE id = :id"),
            {"val": decrypted, "id": str(row.id)}
        )
        decrypted_count += 1

    print(f"Migration 080 downgrade: decrypted {decrypted_count} xendit_api_key values")
