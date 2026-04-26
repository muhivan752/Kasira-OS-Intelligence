"""Pro feature auto-provisioning untuk tenant baru atau upgrade ke Pro.

Saat tenant tier flip starter→pro+, beberapa fitur Pro butuh "default settings"
row biar UX langsung kerasa "aktif". Sebelumnya: row di-create lazy saat user
buka /dashboard/reservasi/settings pertama kali → tenant kira fitur belum ada
karena banner aktif gak prominent.

Helper di sini idempotent: kalau row sudah ada, skip. Aman dipanggil multiple
times (misal tier upgrade lalu downgrade lalu upgrade lagi).

Future: tambah loyalty_settings, ai_settings, dll di provision_pro_features_for_tenant.
"""
from datetime import time as time_type
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.outlet import Outlet
from backend.models.reservation import ReservationSettings


async def ensure_reservation_settings(
    db: AsyncSession,
    outlet_id: UUID,
    *,
    default_enabled: bool = True,
) -> ReservationSettings:
    """Idempotent: create reservation_settings row kalau missing.

    Default `is_enabled=True` saat auto-provision (Pro tenant bayar untuk fitur ini,
    aktif by default. Kalau gak butuh, bisa toggle off via Settings).

    Default opening 08:00, closing 22:00 — ngikutin pattern reservations.py:171-178.
    """
    existing = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet_id)
    )).scalar_one_or_none()
    if existing:
        return existing

    settings = ReservationSettings(
        outlet_id=outlet_id,
        is_enabled=default_enabled,
        opening_hour=time_type(8, 0),
        closing_hour=time_type(22, 0),
    )
    db.add(settings)
    await db.flush()
    return settings


async def provision_pro_features_for_tenant(
    db: AsyncSession,
    tenant_id: UUID,
) -> dict:
    """Auto-provision Pro feature defaults untuk semua outlets di tenant.

    Idempotent — skip outlets yang udah punya settings. Return summary count
    untuk include di response/log.

    Currently provisions:
    - reservation_settings (is_enabled=true)

    Future Pro features yang butuh seed: tambah di sini.
    """
    outlets = (await db.execute(
        select(Outlet).where(
            Outlet.tenant_id == tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )).scalars().all()

    reservation_created = 0
    for outlet in outlets:
        existing = (await db.execute(
            select(ReservationSettings).where(ReservationSettings.outlet_id == outlet.id)
        )).scalar_one_or_none()
        if not existing:
            await ensure_reservation_settings(db, outlet.id, default_enabled=True)
            reservation_created += 1

    return {
        "outlets_total": len(outlets),
        "reservation_settings_created": reservation_created,
    }
