"""Kunci "cuma satu yang jalan" buat janitor.

uvicorn jalan dengan `--workers 2`, dan TIAP worker punya task supervisor
sendiri. Artinya setiap loop latar belakang yang didaftarkan di `main.py`
hidup DUA kali dan menyapu data yang sama pada detik yang sama.

Akibatnya nyata dan sudah kejadian di produksi:
- `subscription_billing` bikin invoice langganan DOBEL. Cek "sudah ada
  invoice?" lolos di dua worker sebelum salah satunya insert, jadi merchant
  ditagih dua kali. Ditemukan 5 Sep 2026: 4 pasang invoice, semuanya lahir
  pada menit yang sama persis (Kasira Coffee 598.000 tiga bulan, Dita Coffee
  198.000).
- `stale_order_cleanup` membatalkan order yatim dan MENGEMBALIKAN STOK. Dua
  worker = stok balik dua kali, diam-diam.
- `online_order_timeout` sudah kena ini di hari pertamanya (3 Sep) dan sudah
  dikasih kunci sendiri. Modul ini menyamakan polanya untuk semua janitor.

Pemakaian:

    async with single_flight("nama_janitor", ttl=50) as boleh:
        if not boleh:
            return
        ...

Redis mati = `boleh` True (janitor tetap jalan). Lebih baik dobel daripada
mati total, dan janitor yang berisiko punya lapis kedua sendiri (FOR UPDATE
SKIP LOCKED, cek idempotensi).

TTL harus LEBIH PENDEK dari interval loop-nya, supaya siklus berikutnya
nggak ikut kekunci; dan lebih panjang dari lama kerja satu siklus.
"""
from __future__ import annotations

import contextlib
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def single_flight(name: str, ttl: int = 50) -> AsyncIterator[bool]:
    """True = worker ini yang bertugas siklus ini. False = worker lain duluan.

    Kuncinya SENGAJA dibiarkan kedaluwarsa sendiri, bukan dihapus di akhir:
    kalau worker mati di tengah kerja, kunci tetap lepas setelah ttl, dan
    kalau kerjanya kelewat lama kunci nggak dilepas lebih awal oleh siklus
    yang sudah selesai duluan.
    """
    key = f"janitor:{name}:lock"
    try:
        from backend.services.online_orders import _redis
        got = await _redis.set(key, "1", nx=True, ex=ttl)
        if not got:
            yield False
            return
    except Exception:  # noqa: BLE001
        logger.warning("janitor %s: kunci redis gagal, jalan tanpa kunci", name, exc_info=True)
    yield True
