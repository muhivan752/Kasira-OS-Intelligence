"""Jam buka beneran (delivery gelombang 1, 4 Sep 2026).

Bentuk `outlets.business_hours`:
    {"mon": [["08:00", "22:00"]], "tue": [], "sun": [["10:00", "02:00"]]}
    - kunci hari: mon tue wed thu fri sat sun (yang nggak ada = tutup)
    - tiap hari boleh lebih dari satu rentang (pagi + malam)
    - tutup < buka = lewat tengah malam (10:00 sampai 02:00 esok)

`hours_mode`: 'manual' = cuma saklar is_open (perilaku lama), 'schedule' =
jadwal yang mutusin, TAPI is_open tetap saklar induk: pemilik matiin is_open
= tutup mendadak walau jadwalnya buka. Semua di zona waktu outlet.

Satu pintu buat "toko lagi buka?": `effective_open(outlet)`. Dipakai payload
storefront, POST order, direktori publik, JSON-LD.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_LABEL = {"mon": "Senin", "tue": "Selasa", "wed": "Rabu", "thu": "Kamis", "fri": "Jumat", "sat": "Sabtu", "sun": "Minggu"}
_SCHEMA_DAY = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}


def _parse(hhmm: str) -> Optional[time]:
    try:
        h, m = str(hhmm).strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return time(h, m)
    except Exception:  # noqa: BLE001
        pass
    return None


def validate(raw) -> dict:
    """Bersihkan + validasi. ValueError kalau bentuknya salah. Hasilnya
    dict lengkap 7 hari (hari tutup = [])."""
    if raw is None:
        return {d: [] for d in DAYS}
    if not isinstance(raw, dict):
        raise ValueError("business_hours harus objek per hari")
    out = {}
    for d in DAYS:
        ranges = raw.get(d) or []
        if not isinstance(ranges, list):
            raise ValueError(f"{_LABEL[d]}: rentang jam harus daftar")
        clean = []
        for r in ranges:
            if not (isinstance(r, (list, tuple)) and len(r) == 2):
                raise ValueError(f"{_LABEL[d]}: tiap rentang berisi jam buka dan tutup")
            a, b = _parse(r[0]), _parse(r[1])
            if a is None or b is None:
                raise ValueError(f"{_LABEL[d]}: format jam HH:MM")
            if a == b:
                raise ValueError(f"{_LABEL[d]}: jam buka dan tutup sama")
            clean.append([a.strftime("%H:%M"), b.strftime("%H:%M")])
        out[d] = clean
    return out


def _tz(outlet) -> ZoneInfo:
    try:
        return ZoneInfo(getattr(outlet, "timezone", None) or "Asia/Jakarta")
    except Exception:  # noqa: BLE001
        return ZoneInfo("Asia/Jakarta")


def is_open_at(hours: Optional[dict], at: datetime) -> bool:
    """`at` sudah di zona outlet. Rentang lewat tengah malam dicek dari hari
    sebelumnya juga (Minggu 22:00 sampai 02:00 = Senin 01:00 masih buka)."""
    if not hours:
        return False
    now_t = at.time()
    today = DAYS[at.weekday()]
    yesterday = DAYS[(at.weekday() - 1) % 7]
    for a, b in hours.get(today) or []:
        ta, tb = _parse(a), _parse(b)
        if ta is None or tb is None:
            continue
        if ta < tb:
            if ta <= now_t < tb:
                return True
        else:  # lewat tengah malam: buka dari ta sampai 23:59
            if now_t >= ta:
                return True
    for a, b in hours.get(yesterday) or []:
        ta, tb = _parse(a), _parse(b)
        if ta is None or tb is None:
            continue
        if ta > tb and now_t < tb:  # sisa rentang kemarin yang lewat tengah malam
            return True
    return False


def effective_open(outlet, now: Optional[datetime] = None) -> bool:
    if not getattr(outlet, "is_open", True):
        return False
    if getattr(outlet, "hours_mode", "manual") != "schedule":
        return True
    hours = getattr(outlet, "business_hours", None)
    if not isinstance(hours, dict):
        return True  # jadwal belum diisi = jangan ngunci toko
    at = (now or datetime.now(_tz(outlet))).astimezone(_tz(outlet))
    return is_open_at(hours, at)


def today_label(outlet, now: Optional[datetime] = None) -> Optional[str]:
    """'08:00 sampai 22:00' buat hari ini, atau 'Tutup hari ini'. None kalau
    nggak pakai jadwal (tampilan jatuh ke opening_hours teks)."""
    hours = getattr(outlet, "business_hours", None)
    if getattr(outlet, "hours_mode", "manual") != "schedule" or not isinstance(hours, dict):
        return None
    at = (now or datetime.now(_tz(outlet))).astimezone(_tz(outlet))
    ranges = hours.get(DAYS[at.weekday()]) or []
    if not ranges:
        return "Tutup hari ini"
    return ", ".join(f"{a} sampai {b}" for a, b in ranges)


def next_open_label(outlet, now: Optional[datetime] = None) -> Optional[str]:
    """'Buka lagi Senin 08:00' buat halaman toko saat tutup. None kalau
    tidak pakai jadwal atau nggak ada jadwal buka 7 hari ke depan."""
    hours = getattr(outlet, "business_hours", None)
    if getattr(outlet, "hours_mode", "manual") != "schedule" or not isinstance(hours, dict):
        return None
    at = (now or datetime.now(_tz(outlet))).astimezone(_tz(outlet))
    for i in range(0, 8):
        day = at + timedelta(days=i)
        for a, _b in sorted(hours.get(DAYS[day.weekday()]) or []):
            ta = _parse(a)
            if ta is None:
                continue
            if i == 0 and ta <= at.time():
                continue
            hari = "hari ini" if i == 0 else ("besok" if i == 1 else _LABEL[DAYS[day.weekday()]])
            return f"Buka lagi {hari} {a}"
    return None


def to_jsonld(hours: Optional[dict]) -> list:
    """schema.org OpeningHoursSpecification. Hari dengan jam sama digabung."""
    if not isinstance(hours, dict):
        return []
    out = []
    for d in DAYS:
        for a, b in hours.get(d) or []:
            out.append({"@type": "OpeningHoursSpecification", "dayOfWeek": _SCHEMA_DAY[d], "opens": a, "closes": b})
    return out
