"""Perangkat terdaftar + notifikasi push — /devices (5 Sep 2026).

Semua tier. Kabar "pesanan online masuk" itu kebutuhan dasar warung, bukan
fitur analitik; toko Starter yang cuma punya satu HP justru paling butuh.

Tabelnya `devices` dari mig 007 yang selama ini nganggur. Jangan bikin tabel
baru — lihat catatan di `backend/models/device.py`.
"""
import logging
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import AsyncSessionLocal, get_db
from backend.models.base import utc_now
from backend.models.device import Device
from backend.models.outlet import Outlet
from backend.models.user import User
from backend.schemas.device import DEVICE_TYPES, DeviceRegister, DeviceResponse, DeviceUnregister
from backend.schemas.response import StandardResponse
from backend.services import fcm

logger = logging.getLogger(__name__)

router = APIRouter()


async def _milik_tenant(db: AsyncSession, outlet_id: UUID, tenant_id) -> Outlet:
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    return outlet


@router.post("/register", response_model=StandardResponse[DeviceResponse])
async def register_device(
    request: Request,
    body: DeviceRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Daftarkan HP ini buat notifikasi. Aman dipanggil berkali-kali.

    Dipanggil app tiap kali dibuka dan tiap kali Firebase ngasih token baru,
    jadi WAJIB idempoten: kunci baris ada di `fcm_token`.

    Pembukuan tokennya jalan di sesi TERPISAH tanpa RLS. Alasannya nyata:
    satu HP bisa dipakai login ke dua tenant (akun demo Ivan dan akun
    tokonya). Kalau upsert-nya kena RLS, baris milik tenant lama nggak
    kelihatan, jadi nggak ke-update, dan tenant lama bakal terus ngirim
    notifikasi ke HP yang sudah pindah tangan.
    """
    if body.device_type not in DEVICE_TYPES:
        raise HTTPException(status_code=400, detail=f"Jenis perangkat tidak dikenal: {body.device_type}")
    await _milik_tenant(db, body.outlet_id, current_user.tenant_id)

    token = body.fcm_token.strip()
    async with AsyncSessionLocal() as sesi:
        await sesi.execute(text("SET LOCAL app.current_tenant_id = ''"))
        dev = (await sesi.execute(
            select(Device).where(Device.fcm_token == token)
        )).scalars().first()
        if dev is None:
            dev = Device(fcm_token=token)
            sesi.add(dev)
        dev.user_id = current_user.id
        dev.outlet_id = body.outlet_id
        dev.device_name = body.device_name[:120]
        dev.device_type = body.device_type
        dev.is_revoked = False
        dev.revoked_at = None
        dev.deleted_at = None
        dev.last_seen_at = utc_now()
        await sesi.commit()
        await sesi.refresh(dev)
        hasil = DeviceResponse.model_validate(dev)

    return StandardResponse(success=True, data=hasil, request_id=request.state.request_id)


@router.post("/unregister", response_model=StandardResponse[dict])
async def unregister_device(
    request: Request,
    body: DeviceUnregister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Dipanggil saat logout. Dicabut, bukan dihapus (Rule #7): jejak
    perangkatnya masih kepakai buat daftar "HP yang pernah dipakai"."""
    token = body.fcm_token.strip()
    async with AsyncSessionLocal() as sesi:
        await sesi.execute(text("SET LOCAL app.current_tenant_id = ''"))
        await sesi.execute(
            update(Device).where(Device.fcm_token == token)
            .values(fcm_token=None, is_revoked=True, revoked_at=utc_now())
        )
        await sesi.commit()
    return StandardResponse(success=True, data={"unregistered": True}, request_id=request.state.request_id)


@router.get("/", response_model=StandardResponse[List[DeviceResponse]])
async def list_devices(
    request: Request,
    outlet_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """HP yang terdaftar di outlet. RLS `devices` sudah nyaring per tenant."""
    q = select(Device).where(Device.deleted_at.is_(None), Device.is_revoked.is_(False))
    if outlet_id:
        await _milik_tenant(db, outlet_id, current_user.tenant_id)
        q = q.where(Device.outlet_id == outlet_id)
    rows = (await db.execute(q.order_by(Device.last_seen_at.desc().nullslast()))).scalars().all()
    return StandardResponse(
        success=True, data=[DeviceResponse.model_validate(d) for d in rows],
        request_id=request.state.request_id,
    )


@router.post("/test-push", response_model=StandardResponse[dict])
async def test_push(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Kirim notifikasi percobaan ke semua HP outlet ini.

    Ada karena push itu susah dites: kalau nggak bunyi, bisa gara-gara kunci
    server, token yang nggak kedaftar, izin notifikasi yang ditolak, atau
    channel yang salah. Tombol ini yang misahin "server nggak ngirim" dari
    "HP nggak nampilin".
    """
    await _milik_tenant(db, outlet_id, current_user.tenant_id)
    if not fcm.enabled():
        raise HTTPException(status_code=503, detail="Notifikasi push belum diaktifkan di server ini")
    sampai = await fcm.notify_outlet(
        outlet_id,
        title="Percobaan notifikasi",
        body="Kalau pesan ini muncul, notifikasi di HP ini sudah aktif.",
        data={"type": "test"},
    )
    return StandardResponse(
        success=True, data={"terkirim": sampai}, request_id=request.state.request_id,
    )
