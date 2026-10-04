import asyncio
import re
import time

import httpx
from fastapi import HTTPException
from jose import JWTError, jwt

from backend.core.config import settings

_KEY_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
_keys: dict = {}
_expires = 0.0
_refreshed = 0.0
_lock = asyncio.Lock()


async def _public_keys(kid: str) -> dict:
    global _keys, _expires, _refreshed
    now = time.monotonic()
    if now < _expires and (kid in _keys or now - _refreshed < 30):
        return _keys
    async with _lock:
        now = time.monotonic()
        if now < _expires and (kid in _keys or now - _refreshed < 30):
            return _keys
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(_KEY_URL)
                response.raise_for_status()
            keys = {key["kid"]: key for key in response.json()["keys"]}
            if not keys:
                raise ValueError("Empty signing keys")
            match = re.search(r"max-age=(\d+)", response.headers.get("cache-control", ""))
            ttl = min(int(match.group(1)), 3600) if match else 300
            _keys, _refreshed, _expires = keys, now, now + ttl
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            raise HTTPException(503, "Google belum dapat dihubungi. Coba lagi atau gunakan kode Sefrekuensi.") from None
        return _keys


async def verify_google_token(id_token: str) -> dict:
    project = settings.GOOGLE_FIREBASE_PROJECT_ID.strip()
    if not project:
        raise HTTPException(503, "Login Google belum diaktifkan. Gunakan kode Sefrekuensi.")
    try:
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise ValueError("Invalid signing header")
        keys = await _public_keys(header["kid"])
        key = keys.get(header["kid"])
        if key is None:
            raise ValueError("Unknown signing key")
        claims = jwt.decode(
            id_token, key, algorithms=["RS256"], audience=project,
            issuer=f"https://securetoken.google.com/{project}",
            options={"require_exp": True, "require_iat": True, "require_sub": True,
                     "require_aud": True, "require_iss": True},
        )
        uid = claims["sub"]
        if not isinstance(uid, str) or not 1 <= len(uid) <= 128:
            raise ValueError("Invalid subject")
        auth_time = claims.get("auth_time")
        if not isinstance(auth_time, (int, float)) or auth_time > time.time():
            raise ValueError("Invalid authentication time")
        if claims.get("iat", 0) > time.time():
            raise ValueError("Future token")
        if (claims.get("firebase") or {}).get("sign_in_provider") != "google.com":
            raise ValueError("Wrong identity provider")
        if claims.get("email_verified") is not True or not claims.get("email"):
            raise ValueError("Unverified email")
        return {"project": project, "uid": uid, "email": claims["email"], "name": claims.get("name", "")}
    except (JWTError, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(401, "Login Google tidak valid atau sudah kedaluwarsa. Pilih akun Google kembali.") from None
