"""Google Maps lewat backend (4 Sep 2026).

Kunci Maps TIDAK pernah dikirim ke browser. Storefront memanggil
`/connect/{slug}/geo/*`, backend yang bicara ke Google dengan kunci server
(`settings.GOOGLE_MAPS_SERVER_KEY`, kunci yang sama dengan Sefrekuensi).
Alasannya: kunci browser harus dibatasi per domain di Google Cloud dan
gampang bocor; kunci server cukup dibatasi per IP VPS.

Yang dipakai:
- Places Autocomplete (legacy JSON) dengan bias lokasi outlet + country:id.
  Pakai `sessiontoken` dari klien supaya Google menagih per sesi ketik,
  bukan per huruf.
- Place Details (fields=geometry,formatted_address) sesudah pelanggan
  memilih saran.
- Geocoding reverse buat tombol "pakai lokasi saya".
- Static Maps buat pratinjau, di-proxy + cache Redis 1 hari (gambar PNG kecil).

Semua fungsi mengembalikan None/[] kalau kunci kosong atau Google gagal,
supaya storefront jatuh ke textarea alamat biasa, bukan error.
"""
from __future__ import annotations

import base64
import logging
import math
from typing import Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://maps.googleapis.com/maps/api"
_TIMEOUT = httpx.Timeout(6.0, connect=3.0)


def enabled() -> bool:
    return bool((settings.GOOGLE_MAPS_SERVER_KEY or "").strip())


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def _get_json(path: str, params: dict) -> Optional[dict]:
    if not enabled():
        return None
    params = {**params, "key": settings.GOOGLE_MAPS_SERVER_KEY, "language": "id", "region": "id"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{_BASE}/{path}", params=params)
        if r.status_code != 200:
            logger.warning("maps %s http %s", path, r.status_code)
            return None
        data = r.json()
        st = data.get("status")
        if st not in ("OK", "ZERO_RESULTS"):
            logger.warning("maps %s status %s: %s", path, st, (data.get("error_message") or "")[:120])
            return None
        return data
    except Exception as e:  # noqa: BLE001
        logger.warning("maps %s gagal: %s", path, e)
        return None


async def autocomplete(query: str, *, lat: Optional[float], lng: Optional[float], session: Optional[str]) -> list[dict]:
    q = (query or "").strip()
    if len(q) < 3:
        return []
    params: dict = {"input": q, "components": "country:id", "types": "geocode|establishment"}
    if lat is not None and lng is not None:
        params["location"] = f"{lat},{lng}"
        params["radius"] = 30000  # 30 km bias, bukan pembatas
    if session:
        params["sessiontoken"] = session[:64]
    data = await _get_json("place/autocomplete/json", params)
    if not data:
        return []
    out = []
    for p in data.get("predictions", [])[:6]:
        sf = p.get("structured_formatting") or {}
        out.append({
            "place_id": p.get("place_id"),
            "main": sf.get("main_text") or p.get("description"),
            "secondary": sf.get("secondary_text") or "",
            "description": p.get("description"),
        })
    return out


async def place_details(place_id: str, *, session: Optional[str]) -> Optional[dict]:
    params: dict = {"place_id": place_id, "fields": "geometry,formatted_address,name"}
    if session:
        params["sessiontoken"] = session[:64]
    data = await _get_json("place/details/json", params)
    res = (data or {}).get("result") or {}
    loc = ((res.get("geometry") or {}).get("location")) or {}
    if "lat" not in loc:
        return None
    return {"lat": float(loc["lat"]), "lng": float(loc["lng"]), "address": res.get("formatted_address") or res.get("name") or ""}


async def reverse(lat: float, lng: float) -> Optional[dict]:
    data = await _get_json("geocode/json", {"latlng": f"{lat},{lng}"})
    results = (data or {}).get("results") or []
    if not results:
        return None
    # Hasil pertama paling spesifik (nomor rumah/jalan), itu yang mau ditulis di alamat.
    return {"lat": lat, "lng": lng, "address": results[0].get("formatted_address") or ""}


async def static_map_png(lat: float, lng: float, *, zoom: int = 16, width: int = 640, height: int = 320,
                         marker2: Optional[tuple[float, float]] = None) -> Optional[bytes]:
    """PNG pratinjau. Di-cache di Redis 24 jam per (lat,lng,zoom,size) supaya
    reload halaman lacak nggak nagih Google lagi."""
    if not enabled():
        return None
    zoom = max(10, min(19, int(zoom)))
    width = max(200, min(640, int(width)))
    height = max(120, min(640, int(height)))
    key = f"geo:static:{round(lat, 5)}:{round(lng, 5)}:{zoom}:{width}x{height}:{marker2 is not None}"
    redis = None
    try:
        from backend.services.online_orders import _redis
        redis = _redis()
        cached = await redis.get(key)
        if cached:
            return base64.b64decode(cached)
    except Exception:  # noqa: BLE001
        redis = None
    params = {
        "key": settings.GOOGLE_MAPS_SERVER_KEY,
        "size": f"{width}x{height}",
        "scale": 2,
        "zoom": zoom,
        "language": "id",
        "markers": f"color:0xE11D74|{lat},{lng}",
    }
    if marker2 is not None:
        params.pop("zoom")  # biar Google fit dua marker
        params["markers"] = [params["markers"], f"color:0x0F172A|label:T|{marker2[0]},{marker2[1]}"]
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{_BASE}/staticmap", params=params)
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
            logger.warning("staticmap http %s", r.status_code)
            return None
        png = r.content
        if redis is not None:
            try:
                await redis.set(key, base64.b64encode(png).decode(), ex=86400)
            except Exception:  # noqa: BLE001
                pass
        return png
    except Exception as e:  # noqa: BLE001
        logger.warning("staticmap gagal: %s", e)
        return None


def maps_link(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def directions_link(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
