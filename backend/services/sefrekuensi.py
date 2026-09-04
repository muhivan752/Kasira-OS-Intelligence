"""Sefrekuensi sebagai jalur kirim OTP (4 Sep 2026).

Keputusan Ivan: pelan pelan lepas dari ketergantungan WhatsApp, tapi WA TETAP
ada. Sefrekuensi punya pengguna asli di Play Store, DM dari Yasmin, dan push
FCM, jadi kode masuk bisa nyampe tanpa Fonnte dan tanpa biaya per pesan.

Bentuknya JALUR TAMBAHAN, bukan pengganti:
- Cuma jalan buat orang yang UDAH punya Sefrekuensi dan nomornya sama.
- Gagal apa pun (nomor gak kedaftar, jaringan, Sefrekuensi mati) langsung
  jatuh ke WA. Fungsi di sini nggak pernah melempar exception ke pemanggil.
- Makanya OTP lewat Sefrekuensi BUKAN mesin akuisisi: buat nerima kode di
  sana, app-nya harus udah kepasang duluan. Ini hadiah buat yang udah punya,
  sekaligus nurunin ongkos Fonnte. Ajakan pasang app ditaruh di titik lain
  (notifikasi pesanan masuk), bukan di sini.

Sejak 4 Sep sore keputusannya diubah lagi: USER YANG MILIH kanalnya di layar
masuk/daftar ("WhatsApp ya WhatsApp, Sefrekuensi ya Sefrekuensi"), bukan
server yang nyoba Sefrekuensi diam diam. Alasannya: versi otomatis nggak
pernah nampilin mereknya, dan layar app bohong soal kode dikirim ke mana.
Layar masuk sekarang jadi iklan halus Sefrekuensi. Kalau nomornya nggak ada
di sana, jawabannya "belum terdaftar" + ajakan pasang, BUKAN diam diam
jatuh ke WA. WA tetap tombol utama supaya orang baru nggak kepaksa pasang
app kedua di tengah daftar.

Kontrak di sisi Sefrekuensi (`backend/handlers/partner_otp.go`, `partner_notify.go`):
  POST {API}/partner/otp/cek    {phone}                        -> {tersedia, push}
  POST {API}/partner/otp/kirim  {phone, kode, aplikasi, keterangan}
                                -> 200 {terkirim, via: app|push}
                                -> 404 nomor gak kedaftar (sinyal buat jatuh ke WA)
  POST {API}/partner/notify     {phone, message, aplikasi, outlet_name, source}
                                -> 200 {terkirim, via} | 404 sama seperti di atas
Langkah 2 (notifikasi merchant, 4 Sep sore): kabar pesanan online, reservasi,
bukti bayar mendarat di DM Yasmin + push walau app kasir ditutup. Ini titik
akuisisi yang beneran kuat; OTP cuma pintu branding.
Header wajib `X-Partner-Key`. Sefrekuensi cuma KURIR: kode dibikin dan
diverifikasi di sini, dia nggak nyimpen apa pun soal keabsahan kode.

Kodenya jangan pernah masuk log, di sini maupun di sana.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


def enabled() -> bool:
    return bool((settings.SEFREKUENSI_API_URL or "").strip() and (settings.SEFREKUENSI_PARTNER_KEY or "").strip())


def _url(path: str) -> str:
    return f"{(settings.SEFREKUENSI_API_URL or '').rstrip('/')}/{path.lstrip('/')}"


def _headers() -> dict:
    return {"X-Partner-Key": settings.SEFREKUENSI_PARTNER_KEY}


async def check(phone: str) -> dict:
    """"Boleh nawarin pintu Sefrekuensi ke nomor ini?" -> {tersedia, push}.

    Dipakai buat MEMUTUSKAN TAMPILAN (mis. tombol "kirim ke Sefrekuensi"),
    bukan buat ngirim. Buat ngirim langsung panggil `send_otp`: dia udah
    balikin 404 sendiri kalau nomornya gak kedaftar, jadi nggak perlu dua
    kali jalan bolak balik.
    """
    if not enabled():
        return {"tersedia": False, "push": False}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(_url("partner/otp/cek"), json={"phone": phone}, headers=_headers())
        if r.status_code != 200:
            logger.warning("sefrekuensi cek http %s", r.status_code)
            return {"tersedia": False, "push": False}
        data = r.json()
        return {"tersedia": bool(data.get("tersedia")), "push": bool(data.get("push"))}
    except Exception:  # noqa: BLE001
        logger.warning("sefrekuensi cek gagal", exc_info=True)
        return {"tersedia": False, "push": False}


@dataclass(frozen=True)
class HasilKirim:
    """Jawaban kurir. `via` terisi = sampai. `alasan` buat pesan ke user:
    'sampai' | 'tidak_terdaftar' | 'gangguan' | 'mati' (fitur belum diset)."""

    via: Optional[str]
    alasan: str

    @property
    def sampai(self) -> bool:
        return self.via is not None


async def send_otp(phone: str, code: str, *, note: str = "") -> HasilKirim:
    """Anter kode ke Sefrekuensi. Nggak pernah melempar.

    `tidak_terdaftar` itu jawaban WAJAR, bukan kegagalan sistem: orangnya
    memang belum punya Sefrekuensi, dan itu mayoritas merchant hari ini.
    Pemanggil yang mutusin mau nawarin pasang atau nyuruh lewat WA.
    """
    if not enabled():
        return HasilKirim(None, "mati")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                _url("partner/otp/kirim"),
                json={
                    "phone": phone,
                    "kode": code,
                    "aplikasi": settings.BRAND_NAME,
                    "keterangan": note or "Berlaku 5 menit.",
                },
                headers=_headers(),
            )
        if r.status_code == 200:
            via = str((r.json() or {}).get("via") or "app")
            logger.info("OTP lewat Sefrekuensi via=%s", via)  # nomor & kode sengaja nggak dicatat
            return HasilKirim(via, "sampai")
        if r.status_code == 404:
            return HasilKirim(None, "tidak_terdaftar")
        logger.warning("sefrekuensi kirim http %s", r.status_code)
        return HasilKirim(None, "gangguan")
    except Exception:  # noqa: BLE001
        logger.warning("sefrekuensi kirim gagal", exc_info=True)
        return HasilKirim(None, "gangguan")


async def send_notify(phone: str, message: str, *, outlet_name: str = "", source: str = "selaris") -> HasilKirim:
    """Kabar ke merchant lewat Sefrekuensi (DM Yasmin + push). Nggak pernah
    melempar. `tidak_terdaftar` = merchant belum punya Sefrekuensi, wajar.
    Isi pesan nggak di-log: ada nama + nomor pelanggan di dalamnya."""
    if not enabled():
        return HasilKirim(None, "mati")
    phone = (phone or "").strip()
    if not phone or not (message or "").strip():
        return HasilKirim(None, "gangguan")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                _url("partner/notify"),
                json={
                    "phone": phone,
                    "message": message,
                    "aplikasi": settings.BRAND_NAME,
                    "outlet_name": outlet_name or "",
                    "source": source,
                },
                headers=_headers(),
            )
        if r.status_code == 200:
            via = str((r.json() or {}).get("via") or "app")
            logger.info("Notif merchant lewat Sefrekuensi via=%s", via)
            return HasilKirim(via, "sampai")
        if r.status_code == 404:
            return HasilKirim(None, "tidak_terdaftar")
        logger.warning("sefrekuensi notify http %s", r.status_code)
        return HasilKirim(None, "gangguan")
    except Exception:  # noqa: BLE001
        logger.warning("sefrekuensi notify gagal", exc_info=True)
        return HasilKirim(None, "gangguan")


# ── Langkah 3: ajakan pasang di titik sakit ──────────────────────────────────
#
# Titik sakitnya: kabar pesanan cuma lewat WA, dan WA nggak bunyi kalau nomor
# Fonnte lagi kena blokir / HP-nya ganti. Ajakan ditaruh PERSIS di situ (kaki
# pesan WA pesanan masuk, banner halaman Pesanan Online di app, kartu Beranda
# web), bukan di layar acak. Semua baca status yang sama: nomor toko ada di
# Sefrekuensi atau nggak (Ivan setuju dicek server-to-server tanpa nanya).

_STATUS_TTL = 3600  # status per nomor di-cache 1 jam: ini buat tampilan, bukan kirim


async def status_for_phone(phone: str) -> dict:
    """{enabled, tersedia, push} dengan cache Redis 1 jam per nomor.
    `enabled` False = fitur belum diset di server, klien jangan nampilin apa apa."""
    phone = (phone or "").strip()
    if not enabled() or not phone:
        return {"enabled": enabled(), "tersedia": False, "push": False}
    key = f"sefre:status:{phone}"
    redis = None
    try:
        from backend.services.redis import get_redis_client
        import json as _json
        redis = await get_redis_client()
        cached = await redis.get(key)
        if cached:
            d = _json.loads(cached)
            d["enabled"] = True
            return d
    except Exception:  # noqa: BLE001
        redis = None
    d = await check(phone)
    d["enabled"] = True
    if redis is not None:
        try:
            await redis.setex(key, _STATUS_TTL, _json.dumps({"tersedia": d["tersedia"], "push": d["push"]}))
        except Exception:  # noqa: BLE001
            pass
    return d


async def forget_status(phone: str) -> None:
    """Dipanggil sesudah kirim beneran (OTP / notif) supaya status nggak basi
    begitu orangnya baru pasang."""
    try:
        from backend.services.redis import get_redis_client
        redis = await get_redis_client()
        await redis.delete(f"sefre:status:{(phone or '').strip()}")
    except Exception:  # noqa: BLE001
        pass


def nudge_line() -> str:
    """Kaki pesan WA buat merchant yang belum punya Sefrekuensi. Pendek,
    satu link, tanpa em dash."""
    return (
        f"Mau kabar pesanan langsung di HP walau app kasir ditutup? "
        f"Pasang Sefrekuensi dengan nomor ini: {settings.SEFREKUENSI_PLAY_URL}"
    )


async def nudge_allowed(outlet_id) -> bool:
    """Ajakan di WA maksimal sekali sehari per toko. Pesanan masuk 20 kali
    sehari nggak boleh jadi 20 iklan."""
    try:
        from backend.services.redis import get_redis_client
        redis = await get_redis_client()
        return bool(await redis.set(f"sefre:nudge:{outlet_id}", "1", ex=86400, nx=True))
    except Exception:  # noqa: BLE001
        return False
