import os
import base64
from cryptography.fernet import Fernet
from backend.core.config import settings

def _get_fernet() -> Fernet:
    """
    Get Fernet instance using ENCRYPTION_KEY from settings.
    Key must be 32 url-safe base64-encoded bytes.
    """
    key = settings.ENCRYPTION_KEY
    if not key:
        # Fallback for development if not set, but warn
        # In production, this should raise an error
        print("WARNING: ENCRYPTION_KEY not set, using temporary key. Data will be lost on restart.")
        key = Fernet.generate_key().decode()
        
    # Ensure key is properly formatted for Fernet
    try:
        return Fernet(key.encode())
    except ValueError:
        # If key is not valid base64, try to make it valid by hashing or padding
        import hashlib
        hashed = hashlib.sha256(key.encode()).digest()
        b64_key = base64.urlsafe_b64encode(hashed)
        return Fernet(b64_key)

def encrypt_field(text: str) -> str:
    """
    Encrypt a string field.
    """
    if not text:
        return text
    f = _get_fernet()
    return f.encrypt(text.encode()).decode()

def decrypt_field(encrypted_text: str) -> str:
    """
    Decrypt a string field.
    """
    if not encrypted_text:
        return encrypted_text
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        print(f"Error decrypting field: {e}")
        return ""
