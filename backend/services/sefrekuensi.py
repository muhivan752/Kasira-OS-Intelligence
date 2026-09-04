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

Kontrak di sisi Sefrekuensi (`backend/handlers/partner_otp.go`):
  POST {API}/partner/otp/cek    {phone}                        -> {tersedia, push}
  POST {API}/partner/otp/kirim  {phone, kode, aplikasi, keterangan}
                                -> 200 {terkirim, via: app|push}
                                -> 404 nomor gak kedaftar (sinyal buat jatuh ke WA)
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
