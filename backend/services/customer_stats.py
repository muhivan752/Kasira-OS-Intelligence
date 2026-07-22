"""Agregat belanja per pelanggan.

`customers.total_visits` / `total_spent` / `first_visit_at` / `last_visit_at`
ada di skema sejak migrasi 009 tapi **tidak pernah ada kode yang mengisinya** —
semua nol. Modul ini yang bikin angkanya nyata.

Sengaja **dihitung dari tabel orders**, bukan di-increment tiap transaksi:
increment gampang melenceng (retry, refund, order dibatalkan sesudah bayar) dan
kalau udah melenceng nggak ada yang nyadar. Hitung ulang selalu benar dan aman
dijalankan berkali-kali.

Definisi "kunjungan" = order yang **lunas** dan tidak dibatalkan. Order pending
atau gagal bayar tidak dihitung, biar angkanya sama dengan yang dilihat owner di
laporan.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.customer import Customer
from backend.models.order import Order
from backend.models.payment import Payment
from backend.models.tab import Tab

logger = logging.getLogger(__name__)


def _is_paid_order():
    """Predikat "order ini lunas" — DUA jalur, dan yang kedua sempat kelewat.

    1. Order biasa: ada Payment berstatus paid yang nunjuk order ini.
    2. Order di dalam tab: kelunasan ada di level TAB, bukan per-order. Bayar
       lewat split / pay-items nggak pernah bikin Payment per-order, dan bayar
       penuh cuma bikin SATU Payment dengan `order_id = order pertama` sebagai
       jangkar (lihat `tabs.py` + gotcha #17). Jadi kalau cuma pakai jalur (1),
       semua order ke-2 dan seterusnya di satu meja dianggap belum lunas —
       pelanggan yang makan di tempat kunjungannya ke-undercount, kadang nol.

    Cerminan `loyalty_service.earn_points_for_tab` yang juga baca kelunasan tab
    dari `tab.status == 'paid'`, bukan dari Payment per-order.
    """
    return or_(
        Order.id.in_(
            select(Payment.order_id).where(
                Payment.status == "paid",
                Payment.deleted_at.is_(None),
            )
        ),
        Order.tab_id.in_(
            select(Tab.id).where(
                Tab.status == "paid",
                Tab.deleted_at.is_(None),
            )
        ),
    )


def _live_order_filter(customer_id):
    """Order milik pelanggan ini yang sah dihitung: lunas, nggak dibatalkan,
    nggak dihapus."""
    return (
        Order.customer_id == customer_id,
        Order.deleted_at.is_(None),
        Order.status != "cancelled",
        _is_paid_order(),
    )


def paid_orders_of_customer(customer_id):
    """Subquery order lunas milik satu pelanggan."""
    return select(Order).where(*_live_order_filter(customer_id))


async def compute_stats(db: AsyncSession, customer_id: UUID) -> dict:
    """Hitung agregat satu pelanggan. Tidak menulis apa pun."""
    row = (await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.min(Order.created_at),
            func.max(Order.created_at),
        ).select_from(Order).where(*_live_order_filter(customer_id))
    )).first()

    visits = int(row[0] or 0)
    spent = float(row[1] or 0)
    return {
        "total_visits": visits,
        "total_spent": spent,
        "first_visit_at": row[2],
        "last_visit_at": row[3],
        "avg_spent": (spent / visits) if visits else 0.0,
    }


async def refresh_customer(db: AsyncSession, customer_id: UUID) -> Optional[dict]:
    """Hitung ulang lalu simpan ke baris customer. Tidak commit — caller yang commit."""
    cust = await db.get(Customer, customer_id)
    if cust is None or cust.deleted_at is not None:
        return None
    st = await compute_stats(db, customer_id)
    cust.total_visits = st["total_visits"]
    cust.total_spent = st["total_spent"]
    cust.first_visit_at = st["first_visit_at"]
    cust.last_visit_at = st["last_visit_at"]
    return st


async def refresh_tenant(db: AsyncSession, tenant_id: UUID) -> int:
    """Hitung ulang semua pelanggan satu tenant. Dipakai backfill + perbaikan.

    Return jumlah pelanggan yang diproses.
    """
    ids = (await db.execute(
        select(Customer.id).where(
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    )).scalars().all()
    for cid in ids:
        await refresh_customer(db, cid)
    return len(ids)


# ---------------------------------------------------------------------------
# Pemanggil dari jalur pembayaran
#
# Sebelum ini kolom agregat cuma keisi kalau ada yang MEMBUKA detail pelanggan
# atau menekan tombol hitung-ulang. Halaman Pelanggan di dashboard (`/customers/
# crm`) baca kolomnya langsung, jadi transaksi yang baru masuk nggak pernah
# kelihatan sampai ada yang mancing manual — persis keluhan "data yang udah
# transaksi nggak masuk realtime".
#
# Kontrak fungsi di bawah, mengikuti pola `loyalty_service`:
#   - TIDAK PERNAH raise. Statistik gagal nggak boleh ngerusak pembayaran.
#   - TIDAK PERNAH commit. Caller yang pegang transaksi.
#   - Nulisnya di dalam SAVEPOINT (`begin_nested`). `try/except` doang NGGAK
#     cukup: sekali statement ditolak Postgres, seluruh transaksi jadi aborted
#     dan commit pembayarannya ikut mati walau error-nya udah ditangkep
#     (gotcha #20).
#   - Bukan fitur Pro. CRM jalan di semua tier, jadi di sini nggak ada cek tier
#     seperti di loyalty.
# ---------------------------------------------------------------------------


async def refresh_customer_safe(db: AsyncSession, customer_id: Optional[UUID]) -> bool:
    """Hitung ulang satu pelanggan, aman dipanggil dari jalur pembayaran."""
    if not customer_id:
        return False
    try:
        async with db.begin_nested():
            await refresh_customer(db, customer_id)
        return True
    except Exception:
        logger.warning(
            "customer_stats: refresh gagal customer=%s", customer_id, exc_info=True,
        )
        return False


async def refresh_for_order(db: AsyncSession, order) -> bool:
    """Hitung ulang pelanggan yang nempel di satu order."""
    return await refresh_customer_safe(db, getattr(order, "customer_id", None))


async def refresh_for_order_id(db: AsyncSession, order_id) -> bool:
    """Varian by-id untuk caller yang belum megang objek Order (jalur sync)."""
    import uuid as _uuid

    if not order_id:
        return False
    try:
        oid = order_id if isinstance(order_id, _uuid.UUID) else _uuid.UUID(str(order_id))
        order = (await db.execute(
            select(Order).where(Order.id == oid, Order.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not order:
            return False
        return await refresh_customer_safe(db, order.customer_id)
    except Exception:
        logger.warning(
            "customer_stats: refresh by-id gagal order=%s", order_id, exc_info=True,
        )
        return False


async def refresh_for_tab(db: AsyncSession, tab) -> int:
    """Hitung ulang semua pelanggan yang nempel di order-order satu tab.

    Per-order, bukan per-tab: satu meja bisa isi beberapa order dengan
    pelanggan berbeda (rombongan yang bayar sendiri-sendiri). Di-dedup biar
    pelanggan yang punya banyak order di tab yang sama nggak dihitung ulang
    berkali-kali.
    """
    seen = set()
    done = 0
    try:
        for order in (getattr(tab, "orders", None) or []):
            cid = getattr(order, "customer_id", None)
            if not cid or cid in seen:
                continue
            seen.add(cid)
            if await refresh_customer_safe(db, cid):
                done += 1
    except Exception:
        logger.warning(
            "customer_stats: refresh tab gagal tab=%s", getattr(tab, "id", None),
            exc_info=True,
        )
    return done
