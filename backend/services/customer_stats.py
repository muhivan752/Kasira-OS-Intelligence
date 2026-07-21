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

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.customer import Customer
from backend.models.order import Order
from backend.models.payment import Payment


def paid_orders_of_customer(customer_id):
    """Subquery order lunas milik satu pelanggan.

    Pakai definisi "lunas" yang sama dengan laporan (`reports.py`): ada Payment
    berstatus paid, order tidak dibatalkan dan tidak dihapus.
    """
    return (
        select(Order)
        .where(
            Order.customer_id == customer_id,
            Order.deleted_at.is_(None),
            Order.status != "cancelled",
            Order.id.in_(
                select(Payment.order_id).where(
                    Payment.status == "paid",
                    Payment.deleted_at.is_(None),
                )
            ),
        )
    )


async def compute_stats(db: AsyncSession, customer_id: UUID) -> dict:
    """Hitung agregat satu pelanggan. Tidak menulis apa pun."""
    row = (await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.min(Order.created_at),
            func.max(Order.created_at),
        ).select_from(Order).where(
            Order.customer_id == customer_id,
            Order.deleted_at.is_(None),
            Order.status != "cancelled",
            Order.id.in_(
                select(Payment.order_id).where(
                    Payment.status == "paid",
                    Payment.deleted_at.is_(None),
                )
            ),
        )
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
