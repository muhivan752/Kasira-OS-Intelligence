"""Loyalty earn — satu sumber kebenaran untuk semua jalur pembayaran.

Kenapa service, bukan helper lokal di payments.py:
Poin harus bisa di-earn dari EMPAT titik yang berbeda dan semuanya wajib
konsisten:

  1. `POST /payments/` cash fully-paid           (payments.create_payment)
  2. Webhook Xendit `paid`                        (payments.xendit_webhook)
  3. `POST /payments/send-receipt`                (kasir baru nangkep nomor
     pelanggan DI HALAMAN STRUK — sesudah bayar. Ini jalur mayoritas.)
  4. Tab / split bill saat tab close ke 'paid'    (tabs.py + webhook tab branch)
  5. Order offline yang masuk lewat `POST /sync/`

Dulu cuma (1) dan (2) yang ada, dan dua-duanya butuh `order.customer_id` SUDAH
terisi pada detik itu juga. Realitanya nomor pelanggan baru nempel di (3),
puluhan detik setelah bayar → poin hilang permanen. 5019 order, 24 punya
customer, cuma 2 yang dapet poin.

Kontrak fungsi di modul ini:
- TIDAK PERNAH raise ke caller. Loyalty gagal gak boleh ngerusak pembayaran.
- TIDAK PERNAH commit. Caller yang pegang transaksi.
- Idempoten via `UNIQUE(order_id, type='earn')` — Rule #35. Dipaksa di level
  DB pakai `ON CONFLICT DO NOTHING`, bukan cuma SELECT-lalu-INSERT. Bedanya
  penting: dengan 5 call site, dua jalur bisa balapan di order yang sama
  (contoh: webhook QRIS + kasir mencet kirim struk). SELECT-dulu bakal lolos
  dua-duanya lalu kena IntegrityError pas flush — dan di SQLAlchemy itu
  meracuni SELURUH transaksi, jadi pembayarannya ikut mati. ON CONFLICT
  menyelesaikannya di dalam satu statement, gak ada transaksi yang keracunan.
- Selalu log kalau gagal. Versi lama `except Exception: pass` tanpa logger —
  itu sebabnya bug ini bisa hidup berbulan-bulan tanpa ketahuan.
"""

import logging
import uuid
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import utc_now
from backend.models.loyalty import CustomerPoints, PointTransaction
from backend.models.order import Order
from backend.models.payment import Payment

logger = logging.getLogger(__name__)

POINTS_PER_RUPIAH = 10_000  # Rp10.000 → 1 poin (mirror loyalty.py)

PRO_TIERS = {"pro", "business", "enterprise"}


async def tenant_is_pro(db: AsyncSession, tenant_id: UUID) -> bool:
    """Loyalty = fitur Pro+. Enum bisa datang sebagai Enum atau str (gotcha tier)."""
    from backend.models.tenant import Tenant

    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )).scalar_one_or_none()
    if not tenant:
        return False
    raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter"
    tier = raw_tier.value if hasattr(raw_tier, "value") else str(raw_tier)
    return tier.lower() in PRO_TIERS


async def order_is_fully_paid(db: AsyncSession, order: Order) -> bool:
    """Sudah lunas? Predikat yang sama persis dipakai create_payment buat
    nentuin order.status → completed (payments.py). Sengaja dicerminkan biar
    gak ada order yang dianggap lunas oleh loyalty tapi belum oleh POS."""
    total_paid = (await db.execute(
        select(func.sum(Payment.amount_paid)).where(
            Payment.order_id == order.id,
            Payment.status == "paid",
            Payment.deleted_at.is_(None),
        )
    )).scalar() or 0
    return float(total_paid) >= float(order.total_amount or 0)


async def earn_points_for_order(
    db: AsyncSession,
    order: Order,
    outlet_id: UUID,
    tenant_id: UUID,
    *,
    source: str = "pos",
    require_fully_paid: bool = True,
    skip_tier_check: bool = False,
) -> int:
    """Kasih poin untuk satu order. Return jumlah poin yang BARU ditambahkan
    (0 kalau di-skip atau sudah pernah earn sebelumnya).

    `require_fully_paid=False` dipakai jalur tab: kelunasan di sana ditentukan
    di level TAB (tab.status == 'paid'), bukan per-order — order dalam tab bisa
    dibayar lewat split/pay-items yang gak pernah bikin Payment.order_id
    per-order, jadi predikat per-order bakal selalu bilang "belum lunas".
    """
    try:
        if not order or not order.customer_id:
            return 0

        order_status = order.status.value if hasattr(order.status, "value") else str(order.status)
        if order_status == "cancelled" or order.deleted_at is not None:
            return 0

        if not skip_tier_check and not await tenant_is_pro(db, tenant_id):
            return 0

        if require_fully_paid and not await order_is_fully_paid(db, order):
            return 0

        points = int(float(order.total_amount or 0) // POINTS_PER_RUPIAH)
        if points <= 0:
            return 0

        now = utc_now()

        # SAVEPOINT. Ini yang bikin janji "loyalty gak boleh ngeblok pembayaran"
        # beneran dipenuhi. `try/except` saja TIDAK cukup: begitu satu statement
        # ditolak Postgres, SELURUH transaksi masuk state aborted, dan semua
        # query sesudahnya — termasuk commit pembayarannya — ikut mati walaupun
        # error-nya sudah kita tangkap. Persis itu yang kejadian pas kolom
        # `row_version` hilang: earn gagal, log muncul rapi, tapi endpoint
        # kirim struk tetap balik 500. Dengan nested transaction, kegagalan
        # cuma nge-rollback sampai savepoint dan transaksi luar tetap sehat.
        async with db.begin_nested():
            # Klaim atomik. Kalau order ini sudah pernah earn, RETURNING kosong
            # dan kita berhenti SEBELUM nyentuh saldo — gak ada double credit.
            claim = (
                pg_insert(PointTransaction.__table__)
                .values(
                    id=uuid.uuid4(),
                    customer_id=order.customer_id,
                    outlet_id=outlet_id,
                    order_id=order.id,
                    type="earn",
                    points=points,
                    description=f"Earn dari transaksi Rp{int(float(order.total_amount or 0)):,}",
                    row_version=0,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_point_transactions_order_type")
                .returning(PointTransaction.__table__.c.id)
            )
            claimed = (await db.execute(claim)).scalar_one_or_none()
            if claimed is None:
                return 0  # sudah pernah di-earn — idempoten, Rule #35

            # Upsert saldo. ON CONFLICT DO UPDATE = gak ada get-or-create race,
            # dan gak butuh SELECT FOR UPDATE terpisah.
            upsert = (
                pg_insert(CustomerPoints.__table__)
                .values(
                    id=uuid.uuid4(),
                    customer_id=order.customer_id,
                    outlet_id=outlet_id,
                    balance=points,
                    lifetime_earned=points,
                    row_version=0,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_customer_points_customer_outlet",
                    set_={
                        "balance": CustomerPoints.__table__.c.balance + points,
                        "lifetime_earned": CustomerPoints.__table__.c.lifetime_earned + points,
                        "row_version": CustomerPoints.__table__.c.row_version + 1,
                        "updated_at": now,
                    },
                )
                .returning(CustomerPoints.__table__.c.balance)
            )
            new_balance = (await db.execute(upsert)).scalar_one_or_none()

        # Jejak untuk event store / AI context. Fail-silent sendiri — kalau
        # event gagal, poin tetap sah.
        try:
            from backend.models.event import Event

            db.add(Event(
                outlet_id=outlet_id,
                stream_id=f"order:{order.id}",
                event_type="loyalty.earned",
                event_data={
                    "order_id": str(order.id),
                    "customer_id": str(order.customer_id),
                    "points": points,
                    "balance_after": int(new_balance) if new_balance is not None else None,
                    "source": source,
                },
                event_metadata={"ts": now.isoformat()},
            ))
        except Exception:
            logger.warning("loyalty: event store gagal order=%s", order.id, exc_info=True)

        logger.info(
            "loyalty earned order=%s customer=%s points=%s source=%s",
            order.id, order.customer_id, points, source,
        )
        return points

    except Exception:
        # Loyalty gagal TIDAK BOLEH ngeblok pembayaran — tapi wajib kelihatan.
        logger.warning(
            "loyalty earn gagal order=%s source=%s",
            getattr(order, "id", None), source, exc_info=True,
        )
        return 0


async def earn_points_for_tab(
    db: AsyncSession,
    tab,
    outlet_id: UUID,
    tenant_id: UUID,
    *,
    source: str = "tab",
) -> int:
    """Kasih poin untuk semua order di dalam tab yang sudah lunas.

    Dipanggil HANYA saat tab close ke 'paid'. Sebelum itu tab masih bisa
    dibayar sebagian (split/pay-items), dan ngasih poin duluan berarti poin
    kekasih buat uang yang belum masuk.

    Per-order, bukan per-tab: satu tab bisa punya beberapa order dengan
    customer berbeda (rombongan yang bayar sendiri-sendiri), dan idempotensi
    di DB kuncinya `order_id`.
    """
    total = 0
    try:
        tab_status = tab.status.value if hasattr(tab.status, "value") else str(tab.status)
        if tab_status != "paid":
            return 0

        if not await tenant_is_pro(db, tenant_id):
            return 0

        for order in (tab.orders or []):
            total += await earn_points_for_order(
                db, order, outlet_id, tenant_id,
                source=source,
                require_fully_paid=False,  # kelunasan ditentukan di level tab
                skip_tier_check=True,      # sudah dicek sekali di atas
            )
    except Exception:
        logger.warning(
            "loyalty earn tab gagal tab=%s", getattr(tab, "id", None), exc_info=True,
        )
    return total


async def earn_points_for_order_id(
    db: AsyncSession,
    order_id: UUID,
    outlet_id: UUID,
    tenant_id: UUID,
    *,
    source: str,
) -> int:
    """Varian by-id untuk caller yang belum megang objek Order (jalur sync)."""
    try:
        # Payload sync datang dari JSON — id-nya string. asyncpg gak mau
        # nyocokin str ke kolom UUID, jadi paksa jadi UUID di sini.
        oid = order_id if isinstance(order_id, uuid.UUID) else uuid.UUID(str(order_id))
        oid_outlet = outlet_id if isinstance(outlet_id, uuid.UUID) else uuid.UUID(str(outlet_id))

        order = (await db.execute(
            select(Order).where(Order.id == oid, Order.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not order:
            return 0
        # Jaga tenant boundary: order harus milik outlet yang diklaim caller.
        if order.outlet_id != oid_outlet:
            logger.warning(
                "loyalty: tolak earn lintas-outlet order=%s outlet=%s", order_id, outlet_id,
            )
            return 0
        return await earn_points_for_order(db, order, oid_outlet, tenant_id, source=source)
    except Exception:
        logger.warning("loyalty earn by-id gagal order=%s", order_id, exc_info=True)
        return 0
