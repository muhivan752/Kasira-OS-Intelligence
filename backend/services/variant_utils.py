"""Varian produk — satu sumber kebenaran buat harga & validasi.

Harga jual varian = `product.base_price + variant.price_adjustment`. Rumusnya
sepele, justru itu bahayanya: kalau tiap layer ngitung sendiri (POS, storefront,
validasi order, struk), cukup satu yang lupa nambahin adjustment dan merchant
rugi tanpa sadar. Sama persis pelajaran dari HPP unit mismatch (gotcha #11) —
rumus gampang yang disalin ke banyak tempat itu justru yang paling sering beda.

Semua yang butuh harga varian WAJIB lewat `variant_price()`.
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.product import Product, ProductVariant

logger = logging.getLogger(__name__)


def variant_price(product: Product, variant: Optional[ProductVariant]) -> Decimal:
    """Harga jual final satu baris. `variant=None` → harga produk polos.

    `price_adjustment` boleh negatif (size kecil lebih murah), tapi hasil
    akhirnya di-clamp ke 0: harga jual minus bikin total order minus dan
    pembayarannya nggak masuk akal. Kalau ke-clamp, itu salah input pemilik —
    di-log biar ketahuan, bukan diam-diam dibenerin.
    """
    base = Decimal(str(product.base_price or 0))
    if variant is None:
        return base
    adj = Decimal(str(variant.price_adjustment or 0))
    final = base + adj
    if final < 0:
        logger.warning(
            "variant: harga akhir minus, di-clamp ke 0 — product=%s variant=%s base=%s adj=%s",
            product.id, variant.id, base, adj,
        )
        return Decimal("0")
    return final


async def resolve_variant(
    db: AsyncSession,
    product_id: UUID,
    variant_id: Optional[UUID],
    *,
    require_active: bool = True,
) -> Optional[ProductVariant]:
    """Ambil varian sambil MASTIIN dia beneran milik produk yang diklaim.

    Tanpa cek kepemilikan, klien bisa ngirim `product_id` produk murah plus
    `product_variant_id` milik produk lain — dan karena harga dihitung dari
    `product.base_price` + adjustment varian, itu jadi celah manipulasi harga.
    Storefront-nya publik, jadi ini bukan skenario teoretis.

    Return None kalau `variant_id` kosong. Raise `ValueError` kalau varian nggak
    ketemu / bukan milik produk itu / lagi nonaktif — caller yang nerjemahin ke
    HTTP 400 dengan pesan yang ramah.
    """
    if not variant_id:
        return None

    variant = (await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    if variant is None:
        raise ValueError("Varian tidak ditemukan")
    if variant.product_id != product_id:
        logger.warning(
            "variant: tolak varian lintas-produk variant=%s milik=%s diklaim=%s",
            variant_id, variant.product_id, product_id,
        )
        raise ValueError("Varian tidak cocok dengan produknya")
    # Varian nonaktif ditolak buat order BARU, tapi tetap boleh dibaca ulang
    # (struk / riwayat) lewat require_active=False.
    if require_active and not variant.is_active:
        raise ValueError(f"Varian '{variant.name}' sedang tidak tersedia")

    return variant


def variant_label(product_name: str, variant: Optional[ProductVariant]) -> str:
    """Nama buat struk & dapur: "Kopi Susu (Dingin)". Dapur cuma baca teks ini,
    jadi varian HARUS ikut ke sini — kalau nggak, barista bikin yang panas."""
    if variant is None:
        return product_name
    return f"{product_name} ({variant.name})"
