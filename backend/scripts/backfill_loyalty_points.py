"""Backfill poin loyalty untuk order lama yang kelewat.

Kenapa perlu:
Sampai fix ini, earn poin cuma dipanggil di `POST /payments/` dan webhook
Xendit, dan dua-duanya butuh `order.customer_id` SUDAH terisi pada detik itu.
Kenyataannya kasir baru nangkep nomor pelanggan di halaman struk (sesudah
bayar), plus jalur tab/split dan order offline gak pernah manggil earn sama
sekali. Hasilnya: order yang punya pelanggan tapi saldo poinnya nol.

Script ini nyari order-order itu dan ngasih poinnya sekarang, pakai fungsi
yang sama persis dengan jalur live (`backend/services/loyalty_service.py`) —
bukan SQL tandingan. Jadi aturan tier, pembulatan poin, dan idempotensinya
dijamin identik; gak ada risiko backfill ngasih angka beda dari runtime.

Pakai:
    # lihat dulu, gak nulis apa-apa
    sudo docker exec kasira-backend-1 python -m backend.scripts.backfill_loyalty_points

    # eksekusi beneran
    sudo docker exec kasira-backend-1 python -m backend.scripts.backfill_loyalty_points --apply

    # batasi ke satu tenant
    sudo docker exec kasira-backend-1 python -m backend.scripts.backfill_loyalty_points \
        --apply --tenant-id <uuid>

Aman diulang: idempotensi dipaksa di level DB lewat
UNIQUE(order_id, type='earn'), jadi jalan dua kali gak bikin poin dobel.
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select, text

from backend.core.database import AsyncSessionLocal
from backend.models.loyalty import PointTransaction
from backend.models.order import Order
from backend.models.outlet import Outlet
from backend.models.tab import Tab
from backend.models.tenant import Tenant
from backend.services.loyalty_service import (
    PRO_TIERS,
    earn_points_for_order,
    order_is_fully_paid,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("backfill_loyalty")


async def _eligible_orders(db, tenant_id=None):
    """Order yang punya pelanggan tapi belum pernah dapet poin.

    Sengaja gak ngefilter status='completed': order yang dibayar lewat tab
    kadang statusnya masih 'preparing'/'ready' sementara tab-nya udah lunas.
    Kelunasan diputuskan belakangan per-order, pakai predikat yang sama dengan
    runtime.
    """
    earned_subq = select(PointTransaction.order_id).where(
        PointTransaction.type == "earn",
        PointTransaction.order_id.is_not(None),
    )

    stmt = (
        select(Order, Outlet.tenant_id)
        .join(Outlet, Outlet.id == Order.outlet_id)
        .join(Tenant, Tenant.id == Outlet.tenant_id)
        .where(
            Order.customer_id.is_not(None),
            Order.deleted_at.is_(None),
            Order.status != "cancelled",
            Order.id.not_in(earned_subq),
        )
        .order_by(Order.created_at)
    )
    if tenant_id:
        stmt = stmt.where(Outlet.tenant_id == tenant_id)

    rows = (await db.execute(stmt)).all()
    return rows


async def run(apply: bool, tenant_id: str | None) -> int:
    async with AsyncSessionLocal() as db:
        # RLS bypass — gotcha #16. `current_setting` untuk key yang belum
        # pernah di-set balikin NULL, dan NULL != '' bikin policy nolak semua
        # baris tanpa bunyi. Harus di-set eksplisit tiap transaksi baru.
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

        rows = await _eligible_orders(db, tenant_id)
        logger.info("kandidat order tanpa poin: %d", len(rows))

        # Cache tier per tenant — ratusan order biasanya cuma segelintir tenant.
        tier_cache: dict = {}
        granted = 0
        skipped_tier = 0
        skipped_unpaid = 0
        skipped_small = 0
        total_points = 0

        for order, tid in rows:
            if tid not in tier_cache:
                tenant = (await db.execute(
                    select(Tenant).where(Tenant.id == tid)
                )).scalar_one_or_none()
                raw = getattr(tenant, "subscription_tier", "starter") or "starter"
                tier = raw.value if hasattr(raw, "value") else str(raw)
                tier_cache[tid] = tier.lower() in PRO_TIERS
            if not tier_cache[tid]:
                skipped_tier += 1
                continue

            # Kelunasan: order tab dinilai di level tab, sisanya per-order.
            # Cerminan persis `_try_earn_loyalty_points_for_receipt`.
            is_tab_order = getattr(order, "tab_id", None) is not None
            if is_tab_order:
                tab = await db.get(Tab, order.tab_id)
                tab_status = None
                if tab:
                    tab_status = tab.status.value if hasattr(tab.status, "value") else str(tab.status)
                if tab_status != "paid":
                    skipped_unpaid += 1
                    continue
            else:
                if not await order_is_fully_paid(db, order):
                    skipped_unpaid += 1
                    continue

            points = int(float(order.total_amount or 0) // 10_000)
            if points <= 0:
                skipped_small += 1
                continue

            if not apply:
                logger.info(
                    "[DRY] order=%s total=%s → +%d poin (customer=%s)",
                    order.id, order.total_amount, points, order.customer_id,
                )
                granted += 1
                total_points += points
                continue

            awarded = await earn_points_for_order(
                db, order, order.outlet_id, tid,
                source="backfill",
                require_fully_paid=not is_tab_order,
                skip_tier_check=True,  # sudah dicek di atas, pakai cache
            )
            if awarded > 0:
                granted += 1
                total_points += awarded
                logger.info(
                    "order=%s → +%d poin (customer=%s)",
                    order.id, awarded, order.customer_id,
                )

        if apply:
            await db.commit()
            logger.info("COMMIT selesai.")
        else:
            await db.rollback()
            logger.info("DRY RUN — gak ada yang ditulis. Tambah --apply buat eksekusi.")

        logger.info(
            "ringkasan: diberi=%d poin_total=%d | skip_tier=%d skip_belum_lunas=%d skip_terlalu_kecil=%d",
            granted, total_points, skipped_tier, skipped_unpaid, skipped_small,
        )
        return granted


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill poin loyalty order lama")
    parser.add_argument("--apply", action="store_true", help="tulis beneran (default dry-run)")
    parser.add_argument("--tenant-id", default=None, help="batasi ke satu tenant")
    args = parser.parse_args()

    asyncio.run(run(args.apply, args.tenant_id))


if __name__ == "__main__":
    sys.exit(main())
