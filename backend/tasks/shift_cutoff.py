"""
Batas hari usaha — janitor yang menutup shift yang kelewat 04.00 waktu outlet.

Kenapa ada: toggle "Tutup kasir" yang wajib kalah di lapangan (25 dari 27
shift di produksi terbuka lebih dari sehari). Toast menyelesaikan ini dengan
"business day cutoff" jam 4 pagi yang menutup apa pun yang tertinggal, dan
menulis eksplisit bahwa tutup hari manual tidak wajib. Ini padanannya.

Aturan:
- Tiap 10 menit: cari shift `open` / `paused` yang `start_time` < batas hari
  usaha terakhir di zona waktu outlet-nya.
- Tutup dengan `closed_reason='auto_cutoff'`, `end_time` = batasnya (bukan
  sekarang), TANPA `ending_cash`: kasnya belum dihitung, dan sistem nggak
  boleh mengaku cocok. Pemilik lihat itu sebagai "belum dihitung".
- Shift yang dijeda ("hitung nanti") tapi nggak pernah dihitung sampai 04.00
  ikut ditutup dengan status yang sama.

Gotcha #16: tabel `shifts` di-RLS lewat outlets.tenant_id. Tanpa
`SET LOCAL app.current_tenant_id = ''` query ini diam-diam balik 0 baris.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text

from backend.core.database import AsyncSessionLocal
from backend.models.outlet import Outlet
from backend.models.shift import Shift, ShiftStatus
from backend.services.shift_service import business_day_cutoff, close_shift

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 600  # 10 menit


async def close_expired_shifts_once() -> dict:
    # Satu worker per siklus (backend/tasks/lock.py). uvicorn jalan 2 worker
    # dan tiap worker punya supervisor sendiri, jadi tanpa ini pass yang sama
    # jalan dua kali bersamaan.
    from backend.tasks.lock import single_flight
    async with single_flight("shift_cutoff", ttl=570) as boleh:
        if not boleh:
            return {"closed": 0, "skipped_lock": True}

        now = datetime.now(timezone.utc)
        closed = 0
        failed = 0

        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

            rows = (await db.execute(
                select(Shift, Outlet.timezone, Outlet.tenant_id)
                .join(Outlet, Outlet.id == Shift.outlet_id)
                .where(
                    Shift.status.in_([ShiftStatus.open, ShiftStatus.paused]),
                    Shift.deleted_at.is_(None),
                )
            )).all()

            for shift, tz_name, tenant_id in rows:
                cutoff = business_day_cutoff(now, tz_name)
                if shift.start_time >= cutoff:
                    continue
                try:
                    was = shift.status.value if hasattr(shift.status, "value") else str(shift.status)
                    await close_shift(
                        db, shift,
                        reason="auto_cutoff",
                        tenant_id=tenant_id,
                        end_time=cutoff,
                        notes="Ditutup otomatis di batas hari usaha 04.00, kas belum dihitung",
                    )
                    await db.flush()
                    closed += 1
                    logger.info(
                        "shift_cutoff: closed shift=%s outlet=%s was=%s start=%s cutoff=%s",
                        shift.id, shift.outlet_id, was, shift.start_time.isoformat(), cutoff.isoformat(),
                    )
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    logger.error("shift_cutoff: failed shift=%s: %s", shift.id, e, exc_info=True)

            await db.commit()

        return {"closed": closed, "failed": failed}


async def shift_cutoff_loop():
    logger.info("Shift cutoff loop started (interval: %ss, cutoff: 04:00 outlet time)", CHECK_INTERVAL_SECONDS)
    while True:
        try:
            result = await close_expired_shifts_once()
            if result["closed"] or result["failed"]:
                logger.info("shift_cutoff: %s", result)
        except Exception as e:  # noqa: BLE001
            logger.error("shift_cutoff loop error: %s", e, exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
