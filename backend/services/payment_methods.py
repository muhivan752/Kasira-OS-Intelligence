"""Satu pola buat semua metode bayar (4 Sep 2026).

Dua pertanyaan yang dijawab di sini, dan HANYA di sini:

1. Metode apa yang toko ini aktifkan? -> `enabled_methods(outlet)`.
   Tunai selalu ada. App kasir, tab meja, dan storefront cuma nampilin yang
   aktif; endpoint bayar nolak yang nggak aktif (400 PAYMENT_METHOD_DISABLED).

2. Pembayaran ini settle langsung atau nunggu webhook? -> `resolve_channel`.
   - 'manual': kasir yang konfirmasi (tunai, transfer, kartu EDC, dan QRIS
     statis milik toko). Status langsung 'paid', sama persis dengan tunai.
   - 'xendit': QR dinamis dari Xendit, status 'pending' sampai webhook.
   QRIS jatuh ke 'xendit' HANYA kalau toko punya kunci Xendit (BYOK) atau
   sub-account. Tanpa itu, QRIS = manual. Nggak ada lagi "QRIS tidak tersedia".

Jangan tulis `payment_method == 'cash'` buat nentuin settle-inline di tempat
lain. Pakai `settles_inline(method, channel)`.
"""
from __future__ import annotations

from typing import Iterable, Optional

ALL_METHODS = ("cash", "qris", "transfer", "card")
DEFAULT_METHODS = ["cash", "qris"]
METHOD_LABELS = {"cash": "Tunai", "qris": "QRIS", "transfer": "Transfer bank", "card": "Kartu EDC"}

CHANNEL_XENDIT = "xendit"
CHANNEL_MANUAL = "manual"


def normalize_methods(methods: Optional[Iterable[str]]) -> list[str]:
    """Bersihin daftar dari klien: urutan tetap (tunai, QRIS, transfer, kartu),
    duplikat dibuang, yang nggak dikenal dibuang, tunai selalu ada."""
    wanted = {str(m).strip().lower() for m in (methods or [])}
    wanted.add("cash")
    return [m for m in ALL_METHODS if m in wanted]


def enabled_methods(outlet) -> list[str]:
    raw = getattr(outlet, "payment_methods", None) if outlet is not None else None
    if not raw:
        return list(DEFAULT_METHODS)
    return normalize_methods(raw)


def is_enabled(outlet, method: str) -> bool:
    return _val(method) in enabled_methods(outlet)


def has_xendit(outlet) -> bool:
    return bool(outlet is not None and (getattr(outlet, "xendit_api_key", None) or getattr(outlet, "xendit_business_id", None)))


def qris_channel(outlet) -> str:
    """Saluran QRIS toko ini kalau nggak diminta khusus."""
    return CHANNEL_XENDIT if has_xendit(outlet) else CHANNEL_MANUAL


def resolve_channel(outlet, method: str, requested: Optional[str] = None) -> str:
    """Saluran final untuk satu pembayaran.

    Klien boleh minta 'manual' buat QRIS walau toko punya Xendit (misal
    pelanggan bayar ke QR standee dan kasir lihat notifikasinya). Klien
    nggak boleh minta 'xendit' kalau toko nggak punya kuncinya: jatuh ke manual.
    """
    m = _val(method)
    if m != "qris":
        return CHANNEL_MANUAL
    if requested == CHANNEL_MANUAL:
        return CHANNEL_MANUAL
    return qris_channel(outlet)


def settles_inline(method: str, channel: Optional[str]) -> bool:
    """True = status 'paid' saat dibuat, tanpa webhook."""
    m = _val(method)
    if m != "qris":
        return True
    return (channel or CHANNEL_XENDIT) == CHANNEL_MANUAL


def public_config(outlet) -> dict:
    """Bentuk yang dibaca app kasir dan storefront."""
    methods = enabled_methods(outlet)
    return {
        "payment_methods": methods,
        "qris_channel": qris_channel(outlet) if "qris" in methods else None,
        "qris_static_image_url": getattr(outlet, "qris_static_image_url", None),
        "bank_name": getattr(outlet, "bank_name", None),
        "bank_account_number": getattr(outlet, "bank_account_number", None),
        "bank_account_name": getattr(outlet, "bank_account_name", None),
    }


def disabled_error(method: str) -> dict:
    label = METHOD_LABELS.get(_val(method), _val(method))
    return {
        "code": "PAYMENT_METHOD_DISABLED",
        "message": f"Metode {label} belum diaktifkan toko ini. Nyalakan di Pengaturan, bagian Metode pembayaran.",
        "received_method": _val(method),
    }


def _val(v) -> str:
    return v.value if hasattr(v, "value") else str(v)
