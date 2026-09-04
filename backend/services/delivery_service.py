"""Ongkir (delivery gelombang 1, 4 Sep 2026).

Satu rumus, satu tempat. Dipakai kuotasi di storefront (geo/place +
delivery-quote), pembuatan order (server hitung ulang, nggak percaya angka
dari klien), dan tampilan.

    fee = base + per_km × max(0, ceil(jarak − free_km))
    dibulatkan KE ATAS ke kelipatan Rp 500 (ongkir Rp 7.342 nggak ada di dunia nyata)

Tanpa koordinat (peta mati, pelanggan ngetik alamat) = base saja. Toko yang
belum ngisi tarif = Rp 0, perilakunya sama seperti sebelum gelombang ini.

Ongkir SENGAJA di luar `orders.total_amount`: belasan modul laporan membaca
kolom itu sebagai penjualan. Yang ditagih = total_amount + delivery_fee.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Optional

_ROUND_TO = 500


def _num(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def enabled(outlet) -> bool:
    return bool(getattr(outlet, "delivery_enabled", True))


def cod_enabled(outlet) -> bool:
    """Toko terima bayar di tempat buat antar? False = wajib bayar dulu."""
    return bool(getattr(outlet, "delivery_cod_enabled", True))


def compute_fee(outlet, distance_km: Optional[float]) -> int:
    base = _num(getattr(outlet, "delivery_fee_base", 0))
    per_km = _num(getattr(outlet, "delivery_fee_per_km", 0))
    free_km = _num(getattr(outlet, "delivery_free_km", 0))
    fee = base
    if distance_km is not None and per_km > 0:
        extra = max(0.0, float(distance_km) - free_km)
        fee += per_km * math.ceil(extra - 1e-9) if extra > 0 else 0
    if fee <= 0:
        return 0
    return int(math.ceil(fee / _ROUND_TO) * _ROUND_TO)


def min_order(outlet) -> int:
    return int(_num(getattr(outlet, "delivery_min_order", 0)))


def public_config(outlet) -> dict:
    """Bagian payload storefront. Angka dikirim supaya halaman keranjang bisa
    nampilin tarif SEBELUM alamat dipilih; angka finalnya tetap dari server."""
    return {
        "delivery": {
            "enabled": enabled(outlet),
            "cod_enabled": cod_enabled(outlet),
            "fee_base": compute_fee(outlet, None),
            "fee_per_km": int(_num(getattr(outlet, "delivery_fee_per_km", 0))),
            "free_km": _num(getattr(outlet, "delivery_free_km", 0)),
            "min_order": min_order(outlet),
            "radius_km": _num(getattr(outlet, "delivery_radius_km", 0)) or None,
        }
    }


def quote(outlet, distance_km: Optional[float]) -> dict:
    radius = _num(getattr(outlet, "delivery_radius_km", 0))
    within = True
    if distance_km is not None and radius > 0:
        within = float(distance_km) <= radius + 0.3
    return {
        "distance_km": distance_km,
        "within_radius": within,
        "radius_km": radius or None,
        "delivery_fee": compute_fee(outlet, distance_km),
        "min_order": min_order(outlet),
    }


def grand_total(order) -> Decimal:
    return Decimal(str(getattr(order, "total_amount", 0) or 0)) + Decimal(str(getattr(order, "delivery_fee", 0) or 0))
