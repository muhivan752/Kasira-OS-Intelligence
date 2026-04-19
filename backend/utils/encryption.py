"""
Field-level encryption helper untuk data sensitif (Xendit API key, dll).

Cipher: **AES-256-GCM** (authenticated encryption — ciphertext tampered = decrypt fail).
Key derivation: SHA-256 dari `settings.ENCRYPTION_KEY` → 32 byte (AES-256).

Format stored di DB: `v1:<base64url(nonce || ciphertext_with_tag)>`
- `v1:` prefix — versioned untuk future key rotation / algo upgrade
- nonce 12 byte (AESGCM standard)
- tag 16 byte append auto oleh AESGCM

Backwards compat: `decrypt_field()` detect legacy Fernet ciphertext
(prefix `gAAAA`) dan handle. `encrypt_field()` selalu emit v1.

Migration path dari plaintext: `EncryptedString` TypeDecorator idempotent —
kalau value sudah punya `v1:` prefix, skip re-encrypt.

Fail-loud: `ENCRYPTION_KEY` unset → raise RuntimeError. TIDAK silent-fallback
ke ephemeral key (behavior lama — bikin data hilang on restart).
"""

import os
import base64
import hashlib
import logging
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, String

from backend.core.config import settings

logger = logging.getLogger(__name__)

_VERSION_PREFIX = "v1:"
_NONCE_LEN = 12
_LEGACY_FERNET_PREFIX = "gAAAA"


def _require_key() -> str:
    """Ensure ENCRYPTION_KEY set — fail loud, no ephemeral fallback."""
    k = settings.ENCRYPTION_KEY
    if not k:
        raise RuntimeError(
            "ENCRYPTION_KEY tidak di-set. Set 32+ char random string di .env "
            "production. Ephemeral fallback dihapus — data akan hilang setelah "
            "restart kalau pakai ephemeral key."
        )
    return k


def _derive_aes256_key() -> bytes:
    """SHA-256 dari ENCRYPTION_KEY → 32 byte untuk AES-256."""
    return hashlib.sha256(_require_key().encode("utf-8")).digest()


def _derive_fernet_key() -> bytes:
    """Legacy Fernet key derivation — hanya untuk decrypt data lama."""
    return base64.urlsafe_b64encode(_derive_aes256_key())


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt via AES-256-GCM. Return `v1:<base64>` format.
    Empty/None pass-through.
    """
    if not plaintext:
        return plaintext
    aesgcm = AESGCM(_derive_aes256_key())
    nonce = os.urandom(_NONCE_LEN)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = base64.urlsafe_b64encode(nonce + ct_with_tag).decode("ascii")
    return _VERSION_PREFIX + blob


def decrypt_field(value: str) -> str:
    """
    Decrypt. Support:
      - v1 (AES-256-GCM) — new format
      - Legacy Fernet (gAAAA prefix) — backwards compat
      - Plaintext (no prefix) — pass-through (pre-migration smooth)

    Raise Exception kalau v1/Fernet decrypt fail (wrong key atau corrupt data).
    """
    if not value:
        return value

    if value.startswith(_VERSION_PREFIX):
        blob = base64.urlsafe_b64decode(value[len(_VERSION_PREFIX):].encode("ascii"))
        nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
        return AESGCM(_derive_aes256_key()).decrypt(nonce, ct, None).decode("utf-8")

    if value.startswith(_LEGACY_FERNET_PREFIX):
        return Fernet(_derive_fernet_key()).decrypt(value.encode("utf-8")).decode("utf-8")

    # Plaintext pre-migration — pass-through. TypeDecorator akan auto-encrypt
    # pada next write.
    return value


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator — column-level transparent encryption.

    Usage: `Column(EncryptedString, nullable=True)`

    - `process_bind_param`: encrypt sebelum INSERT/UPDATE.
      Idempotent: value yang sudah `v1:` prefix gak di-re-encrypt.
    - `process_result_value`: decrypt setelah SELECT.
      Backwards compat: handle legacy Fernet + plaintext pre-migration.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None or value == "":
            return value
        # Idempotent — skip re-encrypt kalau sudah ter-encrypt (e.g. migration
        # backfill sudah jalan, atau data round-tripped via ORM refresh).
        if value.startswith(_VERSION_PREFIX):
            return value
        return encrypt_field(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None or value == "":
            return value
        try:
            return decrypt_field(value)
        except Exception as e:
            # Jangan return "" (silent) — caller akan kirim string kosong ke
            # Xendit API = payment gagal misterius. Raise biar bug ketangkep.
            logger.error(
                "Decrypt gagal untuk field EncryptedString — cek ENCRYPTION_KEY "
                "atau data corruption: %s", e
            )
            raise
