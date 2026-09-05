"""Notifikasi push ke app kasir lewat Firebase Cloud Messaging (5 Sep 2026).

Kenapa ada: sampai sekarang kabar "pesanan online masuk" cuma sampai lewat
WhatsApp pemilik dan lewat SSE yang HANYA hidup selama app kasir dibuka.
Begitu HP dikunci atau app ditutup, kasir buta. FCM nutup lubang itu: HP
bunyi walau app mati.

**Pakai HTTP v1, bukan server key legacy.** Endpoint `fcm.googleapis.com/fcm/send`
dengan header `Authorization: key=...` sudah dimatikan Google (Juni 2024).
Yang hidup cuma `POST /v1/projects/{id}/messages:send` dengan OAuth2 Bearer
dari service account.

**Nggak nambah dependensi.** `firebase-admin` itu SDK sinkron yang bakal
ngeblok event loop (Rule #9 — FastAPI async only) dan narik grpc plus
google-auth. Yang kita butuhin cuma dua HTTP call, dan bahan-bahannya sudah
ada: `python-jose` buat nandatangani JWT RS256, `httpx` buat kirim.

**Token akses di-cache di Redis** (`fcm:access_token`, umur 1 jam dikurangi
2 menit). Tanpa cache, tiap notifikasi jadi dua request ke Google.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CACHE_KEY = "fcm:access_token"

# Channel notifikasi Android. HARUS sama persis dengan yang dibikin app di
# `push_service.dart`, kalau beda Android pakai channel default yang senyap.
CHANNEL_ID = "pesanan_online"

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def enabled() -> bool:
    """Kosong = fitur mati total dan semua pemanggil balik diam-diam. Ini yang
    bikin kode ini aman di-deploy sebelum proyek Firebase-nya jadi."""
    return bool(
        settings.FCM_PROJECT_ID
        and settings.FCM_CLIENT_EMAIL
        and settings.FCM_PRIVATE_KEY
    )


def _private_key() -> str:
    """Kunci di .env ditulis satu baris dengan `\\n` harfiah (baris beneran
    bakal mecah parser .env). Balikin ke bentuk PEM."""
    raw = settings.FCM_PRIVATE_KEY.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw.replace("\\n", "\n")


async def _redis():
    from backend.services.online_orders import _redis as r
    return r


async def _access_token() -> Optional[str]:
    """Bearer token buat FCM. Dibikin dengan nandatangani JWT pakai kunci
    service account, lalu ditukar ke Google. Di-cache di Redis."""
    if not enabled():
        return None
    try:
        r = await _redis()
        cached = await r.get(_CACHE_KEY)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else str(cached)
    except Exception:  # noqa: BLE001
        # Redis mati bukan alasan notifikasi mati; cuma jadi lebih boros.
        logger.warning("fcm: cache token nggak kebaca", exc_info=True)

    now = int(time.time())
    claims = {
        "iss": settings.FCM_CLIENT_EMAIL,
        "scope": _SCOPE,
        "aud": _TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    try:
        from jose import jwt as jose_jwt
        assertion = jose_jwt.encode(claims, _private_key(), algorithm="RS256")
    except Exception:  # noqa: BLE001
        logger.error("fcm: gagal nandatangani JWT — cek FCM_PRIVATE_KEY", exc_info=True)
        return None

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(_TOKEN_URL, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            })
        if resp.status_code != 200:
            logger.error("fcm: tukar token ditolak %s %s", resp.status_code, resp.text[:300])
            return None
        body = resp.json()
        token = body.get("access_token")
        umur = int(body.get("expires_in") or 3600)
    except Exception:  # noqa: BLE001
        logger.error("fcm: tukar token gagal", exc_info=True)
        return None

    if not token:
        return None
    try:
        r = await _redis()
        await r.set(_CACHE_KEY, token, ex=max(60, umur - 120))
    except Exception:  # noqa: BLE001
        pass
    return token


def _payload(token: str, *, title: str, body: str, data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Kirim blok `notification` DAN `data` sekaligus.

    `notification` yang bikin Android nampilin sendiri waktu app di belakang
    atau mati (tanpa itu pesan cuma nyampe ke app yang lagi hidup). `data`
    yang dibaca app buat tahu harus buka layar mana.
    """
    isi = {k: str(v) for k, v in (data or {}).items() if v is not None}
    return {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            "data": isi,
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": CHANNEL_ID,
                    "sound": "default",
                    # Notifikasi dengan tag sama saling menimpa: 5 pesanan
                    # nggak numpuk jadi 5 baris kalau tag-nya disamain lewat
                    # data. Dibiarkan default (numpuk) karena tiap pesanan
                    # memang perlu dilihat satu-satu.
                    "default_vibrate_timings": True,
                },
            },
        }
    }


async def _send_one(client: httpx.AsyncClient, url: str, headers: Dict[str, str],
                    token: str, *, title: str, body: str,
                    data: Optional[Dict[str, str]]) -> str:
    """Balikin 'ok' | 'gone' | 'error'. 'gone' = token mati, harus dibuang."""
    try:
        resp = await client.post(url, headers=headers, json=_payload(token, title=title, body=body, data=data))
    except Exception:  # noqa: BLE001
        logger.warning("fcm: kirim gagal (jaringan)", exc_info=True)
        return "error"
    if resp.status_code == 200:
        return "ok"
    # Token yang sudah nggak sah: app di-uninstall, data dibersihkan, atau
    # token diganti Firebase. 404 NOT_FOUND dan 400 dengan alasan token
    # nggak sah dua-duanya berarti buang.
    teks = resp.text or ""
    if resp.status_code == 404 or "UNREGISTERED" in teks or "INVALID_ARGUMENT" in teks:
        logger.info("fcm: token mati (%s), dibuang", resp.status_code)
        return "gone"
    logger.warning("fcm: ditolak %s %s", resp.status_code, teks[:300])
    return "error"


async def send_to_tokens(tokens: Sequence[str], *, title: str, body: str,
                         data: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
    """Kirim ke banyak token. Balikin {'ok': [...], 'gone': [...]}.

    HTTP v1 nggak punya multicast; SDK resmi pun sebenernya looping. Kita
    looping bareng-bareng lewat satu koneksi.
    """
    hasil: Dict[str, List[str]] = {"ok": [], "gone": [], "error": []}
    tokens = [t for t in dict.fromkeys(tokens) if t]
    if not tokens or not enabled():
        return hasil
    akses = await _access_token()
    if not akses:
        return hasil
    url = f"https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send"
    headers = {"Authorization": f"Bearer {akses}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        keluar = await asyncio.gather(*[
            _send_one(client, url, headers, t, title=title, body=body, data=data) for t in tokens
        ], return_exceptions=True)
    for t, k in zip(tokens, keluar):
        if isinstance(k, Exception):
            hasil["error"].append(t)
        else:
            hasil.setdefault(k, []).append(t)
    return hasil


async def notify_outlet(outlet_id, *, title: str, body: str,
                        data: Optional[Dict[str, str]] = None,
                        device_types: Iterable[str] = ("kasir", "owner")) -> int:
    """Kabar ke semua HP yang terdaftar di satu outlet. Balikin jumlah yang
    sampai.

    Bikin sesi DB sendiri: pemanggilnya `wa_owner`, yang dijalankan lewat
    `asyncio.create_task` tanpa bawa sesi (dan sesi request-nya bisa saja
    sudah ditutup). Wajib `SET LOCAL app.current_tenant_id = ''` karena
    tabel `devices` kena RLS dan task latar nggak lewat middleware
    (gotcha #16).
    """
    if not enabled() or not outlet_id:
        return 0
    from sqlalchemy import select, text, update
    from backend.core.database import AsyncSessionLocal
    from backend.models.device import Device

    tipe = tuple(device_types)
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            rows = (await db.execute(
                select(Device).where(
                    Device.outlet_id == outlet_id,
                    Device.deleted_at.is_(None),
                    Device.is_revoked.is_(False),
                    Device.fcm_token.isnot(None),
                    Device.device_type.in_(tipe),
                )
            )).scalars().all()
            tokens = [d.fcm_token for d in rows if d.fcm_token]
            if not tokens:
                return 0
            hasil = await send_to_tokens(tokens, title=title, body=body, data=data)
            mati = set(hasil.get("gone") or [])
            if mati:
                # Token mati dicabut, bukan dihapus: jejak HP-nya masih
                # berguna buat "perangkat terdaftar" (Rule #7 soft delete).
                from backend.models.base import utc_now
                await db.execute(
                    update(Device)
                    .where(Device.fcm_token.in_(list(mati)))
                    .values(fcm_token=None, is_revoked=True, revoked_at=utc_now())
                )
                await db.commit()
            return len(hasil.get("ok") or [])
    except Exception:  # noqa: BLE001
        logger.warning("fcm: notify_outlet gagal untuk outlet %s", outlet_id, exc_info=True)
        return 0
