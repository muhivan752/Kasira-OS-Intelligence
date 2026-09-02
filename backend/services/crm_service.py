"""
CRM gelombang 3 — segmen pelanggan yang KEBENTUK SENDIRI dari order lunas.

Nggak ada yang diisi manual. `refresh_segments()` ngitung per pelanggan:
  recency   = hari sejak kunjungan terakhir (order lunas)
  frequency = jumlah order lunas 90 hari terakhir
  monetary  = total belanja 90 hari terakhir
lalu nempelin satu label dengan bahasa warung, bukan jargon:

  baru          total kunjungan ≤ 1 dan kunjungan pertama ≤ 14 hari
  setia         ≥ 4 kunjungan dalam 30 hari
  vip           top 10% monetary 90 hari (min 3 kunjungan)
  mulai_jarang  dulu rajin (≥ 2 kunjungan di hari 31–90) tapi absen > 21 hari
  hilang        absen > 60 hari
  biasa         sisanya

Refresh malas: dipanggil dari GET /crm/segments/summary kalau
`segment_updated_at` tertua > 6 jam, dan dari POST /crm/segments/refresh.
Kelunasan order pakai pola gotcha #24 (tab lunas = tab.status paid).
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.customer import Customer
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.payment import Payment
from backend.models.tab import Tab

logger = logging.getLogger(__name__)

SEGMENTS: list[tuple[str, str, str]] = [
    # key, label, saran aksi
    ("baru", "Baru", "Kasih voucher kunjungan ke-2"),
    ("setia", "Setia", "Jangan diganggu promo, kasih poin ekstra"),
    ("vip", "VIP", "Akses menu baru duluan, ucapan ulang tahun"),
    ("biasa", "Biasa", "Ajak balik lewat promo bulanan"),
    ("mulai_jarang", "Mulai jarang", "WA 'kangen' + menu favorit + voucher kecil"),
    ("hilang", "Hilang", "Satu campaign win-back, kalau nggak balik berhenti kirim"),
]
SEGMENT_LABEL = {k: v for k, v, _ in SEGMENTS}
SEGMENT_HINT = {k: h for k, _, h in SEGMENTS}
STALE_AFTER = timedelta(hours=6)


def _paid_order_filter():
    return or_(
        and_(Order.tab_id.is_(None),
             Order.id.in_(select(Payment.order_id).where(Payment.status == "paid", Payment.deleted_at.is_(None)))),
        and_(Order.tab_id.isnot(None),
             Order.tab_id.in_(select(Tab.id).where(Tab.status == "paid", Tab.deleted_at.is_(None)))),
    )


async def refresh_segments(db: AsyncSession, tenant_id: UUID) -> dict:
    """Hitung ulang semua pelanggan tenant. Return ringkasan per segmen. Tidak commit."""
    now = datetime.now(timezone.utc)
    d30, d90 = now - timedelta(days=30), now - timedelta(days=90)

    outlet_ids = list((await db.execute(
        select(Outlet.id).where(Outlet.tenant_id == tenant_id, Outlet.deleted_at.is_(None))
    )).scalars().all())
    customers = list((await db.execute(
        select(Customer).where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
    )).scalars().all())
    if not customers:
        return {"total": 0, "by_segment": {}}

    # Order lunas 90 hari per pelanggan (tanggal + total)
    rows = (await db.execute(
        select(Order.customer_id, Order.created_at, Order.total_amount)
        .where(
            Order.outlet_id.in_(outlet_ids) if outlet_ids else False,
            Order.customer_id.isnot(None), Order.deleted_at.is_(None), Order.status != "cancelled",
            Order.created_at >= d90, _paid_order_filter(),
        )
    )).all()
    by_cust: dict[UUID, list] = defaultdict(list)
    for cid, at, total in rows:
        by_cust[cid].append((at, Decimal(str(total or 0))))

    # Produk favorit = qty terbanyak 90 hari
    fav_rows = (await db.execute(
        select(Order.customer_id, OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.outlet_id.in_(outlet_ids) if outlet_ids else False,
            Order.customer_id.isnot(None), Order.deleted_at.is_(None), Order.status != "cancelled",
            Order.created_at >= d90, OrderItem.deleted_at.is_(None), _paid_order_filter(),
        ).group_by(Order.customer_id, OrderItem.product_id)
    )).all()
    fav: dict[UUID, tuple[UUID, int]] = {}
    for cid, pid, qty in fav_rows:
        if cid not in fav or int(qty) > fav[cid][1]:
            fav[cid] = (pid, int(qty))

    # VIP threshold = persentil 90 monetary (min 3 kunjungan)
    monetary = {cid: sum(t for _, t in v) for cid, v in by_cust.items()}
    eligible = sorted((m for cid, m in monetary.items() if len(by_cust[cid]) >= 3 and m > 0), reverse=True)
    vip_cut = eligible[max(0, len(eligible) // 10 - 1)] if eligible else None
    if vip_cut is not None and len(eligible) < 10:
        vip_cut = eligible[0]  # tenant kecil: cuma yang paling gede

    counts: Counter = Counter()
    for c in customers:
        orders = by_cust.get(c.id, [])
        last_at = max((at for at, _ in orders), default=None) or c.last_visit_at
        recency = (now - last_at).days if last_at else None
        freq_30 = sum(1 for at, _ in orders if at >= d30)
        freq_90 = len(orders)
        mon_90 = monetary.get(c.id, Decimal("0"))
        older = sum(1 for at, _ in orders if at < d30)  # hari 31–90
        total_visits = max(c.total_visits or 0, freq_90)
        first_at = c.first_visit_at or (min((at for at, _ in orders), default=None))

        if recency is None:
            seg = "baru" if (first_at is None or (now - first_at).days <= 14) else "hilang"
        elif recency > 60:
            seg = "hilang"
        elif older >= 2 and recency > 21:
            seg = "mulai_jarang"
        elif vip_cut is not None and freq_90 >= 3 and mon_90 >= vip_cut:
            seg = "vip"
        elif freq_30 >= 4:
            seg = "setia"
        elif total_visits <= 1 and first_at is not None and (now - first_at).days <= 14:
            seg = "baru"
        else:
            seg = "biasa"

        c.segment = seg
        c.segment_updated_at = now
        c.rfm_recency_days = recency
        c.rfm_frequency_90d = freq_90
        c.rfm_monetary_90d = mon_90
        if c.id in fav:
            c.favorite_product_id = fav[c.id][0]
        counts[seg] += 1

    await db.flush()
    return {"total": len(customers), "by_segment": dict(counts)}


async def needs_refresh(db: AsyncSession, tenant_id: UUID) -> bool:
    oldest = (await db.execute(
        select(func.min(Customer.segment_updated_at)).where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
    )).scalar()
    has_any = (await db.execute(
        select(func.count(Customer.id)).where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
    )).scalar() or 0
    if not has_any:
        return False
    return oldest is None or (datetime.now(timezone.utc) - oldest) > STALE_AFTER


async def segment_summary(db: AsyncSession, tenant_id: UUID) -> list[dict]:
    rows = (await db.execute(
        select(Customer.segment, func.count(Customer.id), func.coalesce(func.sum(Customer.rfm_monetary_90d), 0))
        .where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
        .group_by(Customer.segment)
    )).all()
    by = {r[0]: (int(r[1]), Decimal(str(r[2]))) for r in rows}
    consent = (await db.execute(
        select(Customer.segment, func.count(Customer.id))
        .where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None), Customer.wa_marketing_consent.is_(True))
        .group_by(Customer.segment)
    )).all()
    consent_by = {r[0]: int(r[1]) for r in consent}
    out = []
    for key, label, hint in SEGMENTS:
        n, m = by.get(key, (0, Decimal("0")))
        out.append({"key": key, "label": label, "hint": hint, "count": n, "monetary_90d": str(m),
                    "reachable": consent_by.get(key, 0)})
    return out
