"""
Kasira Reservations Route — Pro Feature

Auth endpoints (owner/kasir):
  GET    /reservations/?outlet_id=&date=&status=
  POST   /reservations/
  PUT    /reservations/{id}/confirm
  PUT    /reservations/{id}/seat
  PUT    /reservations/{id}/complete
  PUT    /reservations/{id}/cancel
  PUT    /reservations/{id}/no-show
  GET    /reservations/settings/{outlet_id}
  PUT    /reservations/settings/{outlet_id}

Public endpoints (storefront):
  Handled in connect.py
"""

import logging
from typing import Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone, date, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api import deps
from backend.core.database import get_db
from backend.models.outlet import Outlet
from backend.models.reservation import Reservation, Table, ReservationSettings
from backend.models.user import User
from backend.schemas.reservation import (
    ReservationCreate, ReservationResponse, ReservationSettingsUpdate,
    ReservationSettingsResponse,
)
from backend.schemas.response import StandardResponse
from backend.utils.phone import mask_phone
from backend.services.audit import log_audit

router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])
logger = logging.getLogger(__name__)


# ─── Helpers ────────────────────────────────────────────────────────────────

async def _validate_outlet(db: AsyncSession, outlet_id: UUID, tenant_id: UUID) -> Outlet:
    outlet = (await db.execute(
        select(Outlet).where(
            Outlet.id == outlet_id, Outlet.tenant_id == tenant_id, Outlet.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    return outlet


async def _get_reservation(db: AsyncSession, reservation_id: UUID, lock: bool = False):
    stmt = select(Reservation).where(Reservation.id == reservation_id, Reservation.deleted_at.is_(None))
    if lock:
        stmt = stmt.with_for_update()
    reservation = (await db.execute(stmt)).scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")
    return reservation


def _build_response(r: Reservation, table: Optional[Table] = None) -> dict:
    return {
        "id": str(r.id),
        "outlet_id": str(r.outlet_id),
        "table_id": str(r.table_id) if r.table_id else None,
        "table_name": table.name if table else None,
        "table_floor_section": table.floor_section if table else None,
        "reservation_date": r.reservation_date.isoformat() if r.reservation_date else None,
        "start_time": r.start_time.isoformat() if r.start_time else None,
        "end_time": r.end_time.isoformat() if r.end_time else None,
        "guest_count": r.guest_count,
        "customer_name": r.customer_name,
        "customer_phone": mask_phone(r.customer_phone),
        "status": r.status,
        "deposit_amount": float(r.deposit_amount) if r.deposit_amount else None,
        "source": r.source,
        "notes": r.notes,
        "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
        "cancelled_at": r.cancelled_at.isoformat() if r.cancelled_at else None,
        "row_version": r.row_version,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


async def _auto_assign_table(db: AsyncSession, outlet_id: UUID, guest_count: int,
                              res_date: date, start: time, end: time) -> Optional[Table]:
    """Find smallest available table that fits guest_count and has no conflict."""
    # Get all active tables with enough capacity
    tables_result = await db.execute(
        select(Table).where(
            Table.outlet_id == outlet_id,
            Table.deleted_at.is_(None),
            Table.is_active == True,
            Table.capacity >= guest_count,
        ).order_by(Table.capacity.asc())
    )
    candidates = tables_result.scalars().all()

    for table in candidates:
        # Check for conflicting reservations on this table
        conflict = (await db.execute(
            select(func.count(Reservation.id)).where(
                Reservation.table_id == table.id,
                Reservation.reservation_date == res_date,
                Reservation.deleted_at.is_(None),
                Reservation.status.in_(['pending', 'confirmed', 'seated']),
                # Overlap: existing.start < new.end AND existing.end > new.start
                Reservation.start_time < end,
                Reservation.end_time > start,
            )
        )).scalar()
        if conflict == 0:
            return table
    return None


async def _send_wa_confirmation(phone: str, outlet_name: str, res_date: date, start: time, guest_count: int):
    """Fire-and-forget WA confirmation."""
    try:
        from backend.services.fonnte import send_whatsapp_message
        date_str = res_date.strftime("%d %B %Y")
        time_str = start.strftime("%H:%M")
        msg = (
            f"✅ Reservasi Anda di *{outlet_name}* telah dikonfirmasi.\n\n"
            f"📅 {date_str}\n"
            f"🕐 {time_str}\n"
            f"👥 {guest_count} orang\n\n"
            f"Sampai jumpa!"
        )
        await send_whatsapp_message(phone, msg)
    except Exception as e:
        logger.warning(f"Failed to send WA confirmation: {e}")


async def _send_wa_cancelled(phone: str, outlet_name: str, res_date: date):
    try:
        from backend.services.fonnte import send_whatsapp_message
        date_str = res_date.strftime("%d %B %Y")
        msg = f"❌ Reservasi Anda di *{outlet_name}* pada {date_str} telah dibatalkan."
        await send_whatsapp_message(phone, msg)
    except Exception as e:
        logger.warning(f"Failed to send WA cancellation: {e}")


# ─── Settings Endpoints ────────────────────────────────────────────────────

@router.get("/settings/{outlet_id}")
async def get_reservation_settings(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _validate_outlet(db, outlet_id, current_user.tenant_id)

    settings = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet_id)
    )).scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = ReservationSettings(
            outlet_id=outlet_id,
            opening_hour=time(8, 0),
            closing_hour=time(22, 0),
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return StandardResponse(
        success=True,
        data=ReservationSettingsResponse.model_validate(settings),
        request_id=request.state.request_id,
    )


@router.put("/settings/{outlet_id}")
async def update_reservation_settings(
    request: Request,
    outlet_id: UUID,
    body: ReservationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _validate_outlet(db, outlet_id, current_user.tenant_id)

    settings = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet_id)
    )).scalar_one_or_none()

    if not settings:
        settings = ReservationSettings(
            outlet_id=outlet_id,
            opening_hour=time(8, 0),
            closing_hour=time(22, 0),
        )
        db.add(settings)
        await db.flush()

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)

    await db.commit()
    await db.refresh(settings)

    # Invalidate storefront cache (tier/reservation_enabled might change)
    from backend.api.routes.connect import invalidate_storefront_cache
    await invalidate_storefront_cache(outlet_id, db)

    await log_audit(db=db, action="UPDATE", entity="reservation_settings", entity_id=settings.id,
                    after_state=update_data, user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True,
        data=ReservationSettingsResponse.model_validate(settings),
        request_id=request.state.request_id,
        message="Pengaturan reservasi berhasil diupdate",
    )


# ─── Reservation CRUD ──────────────────────────────────────────────────────

@router.get("/")
async def list_reservations(
    request: Request,
    outlet_id: UUID = Query(...),
    reservation_date: Optional[date] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List reservasi untuk outlet, optional filter by date & status."""
    await _validate_outlet(db, outlet_id, current_user.tenant_id)

    stmt = select(Reservation).where(
        Reservation.outlet_id == outlet_id,
        Reservation.deleted_at.is_(None),
    )
    if reservation_date:
        stmt = stmt.where(Reservation.reservation_date == reservation_date)
    if status:
        stmt = stmt.where(Reservation.status == status)
    stmt = stmt.order_by(Reservation.reservation_date.asc(), Reservation.start_time.asc())

    result = await db.execute(stmt)
    reservations = result.scalars().all()

    # Bulk load tables
    table_ids = list({r.table_id for r in reservations if r.table_id})
    tables_map: dict = {}
    if table_ids:
        tbl_result = await db.execute(select(Table).where(Table.id.in_(table_ids)))
        tables_map = {t.id: t for t in tbl_result.scalars().all()}

    items = [_build_response(r, tables_map.get(r.table_id)) for r in reservations]

    return StandardResponse(
        success=True, data=items,
        request_id=request.state.request_id,
    )


@router.post("/")
async def create_reservation(
    request: Request,
    outlet_id: UUID = Query(...),
    body: ReservationCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Kasir/owner buat reservasi manual."""
    outlet = await _validate_outlet(db, outlet_id, current_user.tenant_id)

    # Load settings for slot duration
    settings = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet_id)
    )).scalar_one_or_none()
    slot_minutes = settings.slot_duration_minutes if settings else 120

    # Calculate end_time
    start_dt = datetime.combine(body.reservation_date, body.start_time)
    end_dt = start_dt + timedelta(minutes=slot_minutes)
    end_time = end_dt.time()

    # Auto-assign table if not specified
    table = None
    table_id = body.table_id
    if table_id:
        table = (await db.execute(
            select(Table).where(Table.id == table_id, Table.outlet_id == outlet_id, Table.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
        if table.capacity < body.guest_count:
            raise HTTPException(status_code=400, detail=f"Kapasitas meja ({table.capacity}) kurang untuk {body.guest_count} tamu")
    else:
        table = await _auto_assign_table(db, outlet_id, body.guest_count,
                                          body.reservation_date, body.start_time, end_time)

    reservation = Reservation(
        outlet_id=outlet_id,
        tenant_id=current_user.tenant_id,
        table_id=table.id if table else None,
        reservation_date=body.reservation_date,
        start_time=body.start_time,
        end_time=end_time,
        guest_count=body.guest_count,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        source=body.source,
        notes=body.notes,
        status='confirmed',  # Manual = langsung confirmed
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)

    await log_audit(db=db, action="CREATE", entity="reservation", entity_id=reservation.id,
                    after_state={"customer_name": body.customer_name, "date": str(body.reservation_date)},
                    user_id=current_user.id, tenant_id=current_user.tenant_id)

    # Send WA confirmation (fire-and-forget)
    import asyncio
    asyncio.create_task(_send_wa_confirmation(
        body.customer_phone, outlet.name, body.reservation_date, body.start_time, body.guest_count
    ))

    return StandardResponse(
        success=True, data=_build_response(reservation, table),
        request_id=request.state.request_id,
        message="Reservasi berhasil dibuat",
    )


@router.put("/{reservation_id}/confirm")
async def confirm_reservation(
    request: Request,
    reservation_id: UUID,
    table_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Konfirmasi reservasi pending (dari storefront)."""
    reservation = await _get_reservation(db, reservation_id, lock=True)
    outlet = await _validate_outlet(db, reservation.outlet_id, current_user.tenant_id)

    if reservation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Hanya reservasi pending yang bisa dikonfirmasi (saat ini: {reservation.status})")

    # Assign table if provided or auto-assign
    table = None
    if table_id:
        table = (await db.execute(
            select(Table).where(Table.id == table_id, Table.outlet_id == reservation.outlet_id, Table.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
    elif not reservation.table_id:
        table = await _auto_assign_table(
            db, reservation.outlet_id, reservation.guest_count,
            reservation.reservation_date, reservation.start_time, reservation.end_time,
        )

    if table:
        reservation.table_id = table.id

    reservation.status = "confirmed"
    reservation.confirmed_at = datetime.now(timezone.utc)
    reservation.row_version += 1
    await db.commit()

    await log_audit(db=db, action="reservation_confirm", entity="reservation", entity_id=reservation_id,
                    after_state={"status": "confirmed"}, user_id=current_user.id, tenant_id=current_user.tenant_id)

    # WA confirmation
    if reservation.customer_phone:
        import asyncio
        asyncio.create_task(_send_wa_confirmation(
            reservation.customer_phone, outlet.name,
            reservation.reservation_date, reservation.start_time, reservation.guest_count,
        ))

    return StandardResponse(
        success=True, data=_build_response(reservation, table),
        request_id=request.state.request_id, message="Reservasi dikonfirmasi",
    )


@router.put("/{reservation_id}/seat")
async def seat_reservation(
    request: Request,
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Tamu datang — set status seated."""
    reservation = await _get_reservation(db, reservation_id, lock=True)
    await _validate_outlet(db, reservation.outlet_id, current_user.tenant_id)

    if reservation.status != "confirmed":
        raise HTTPException(status_code=400, detail="Hanya reservasi confirmed yang bisa di-seat")

    reservation.status = "seated"
    reservation.row_version += 1

    # Set table to occupied
    if reservation.table_id:
        table = (await db.execute(
            select(Table).where(Table.id == reservation.table_id).with_for_update()
        )).scalar_one_or_none()
        if table:
            table.status = "occupied"
            table.row_version += 1

    await db.commit()

    await log_audit(db=db, action="reservation_seat", entity="reservation", entity_id=reservation_id,
                    after_state={"status": "seated"}, user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True, data={"status": "seated", "row_version": reservation.row_version},
        request_id=request.state.request_id, message="Tamu telah duduk",
    )


@router.put("/{reservation_id}/complete")
async def complete_reservation(
    request: Request,
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Selesaikan reservasi — release meja."""
    reservation = await _get_reservation(db, reservation_id, lock=True)
    await _validate_outlet(db, reservation.outlet_id, current_user.tenant_id)

    if reservation.status not in ("confirmed", "seated"):
        raise HTTPException(status_code=400, detail="Hanya reservasi confirmed/seated yang bisa diselesaikan")

    reservation.status = "completed"
    reservation.row_version += 1

    # Release table
    if reservation.table_id:
        table = (await db.execute(
            select(Table).where(Table.id == reservation.table_id).with_for_update()
        )).scalar_one_or_none()
        if table and table.status in ("reserved", "occupied"):
            table.status = "available"
            table.row_version += 1

    await db.commit()

    await log_audit(db=db, action="reservation_complete", entity="reservation", entity_id=reservation_id,
                    after_state={"status": "completed"}, user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True, data={"status": "completed"},
        request_id=request.state.request_id, message="Reservasi selesai",
    )


@router.put("/{reservation_id}/cancel")
async def cancel_reservation(
    request: Request,
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Batalkan reservasi — release meja."""
    reservation = await _get_reservation(db, reservation_id, lock=True)
    outlet = await _validate_outlet(db, reservation.outlet_id, current_user.tenant_id)

    if reservation.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Reservasi sudah {reservation.status}")

    # Release table
    if reservation.table_id:
        table = (await db.execute(
            select(Table).where(Table.id == reservation.table_id).with_for_update()
        )).scalar_one_or_none()
        if table and table.status in ("reserved", "occupied"):
            table.status = "available"
            table.row_version += 1

    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now(timezone.utc)
    reservation.row_version += 1
    await db.commit()

    await log_audit(db=db, action="reservation_cancel", entity="reservation", entity_id=reservation_id,
                    after_state={"status": "cancelled"}, user_id=current_user.id, tenant_id=current_user.tenant_id)

    # WA notification
    if reservation.customer_phone and reservation.reservation_date:
        import asyncio
        asyncio.create_task(_send_wa_cancelled(reservation.customer_phone, outlet.name, reservation.reservation_date))

    return StandardResponse(
        success=True, data={"status": "cancelled"},
        request_id=request.state.request_id, message="Reservasi dibatalkan",
    )


@router.put("/{reservation_id}/no-show")
async def noshow_reservation(
    request: Request,
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Tamu tidak datang — deposit hangus (owner decide)."""
    reservation = await _get_reservation(db, reservation_id, lock=True)
    await _validate_outlet(db, reservation.outlet_id, current_user.tenant_id)

    if reservation.status not in ("confirmed",):
        raise HTTPException(status_code=400, detail="Hanya reservasi confirmed yang bisa di-mark no-show")

    # Release table
    if reservation.table_id:
        table = (await db.execute(
            select(Table).where(Table.id == reservation.table_id).with_for_update()
        )).scalar_one_or_none()
        if table and table.status in ("reserved",):
            table.status = "available"
            table.row_version += 1

    reservation.status = "no_show"
    reservation.row_version += 1
    await db.commit()

    await log_audit(db=db, action="reservation_noshow", entity="reservation", entity_id=reservation_id,
                    after_state={"status": "no_show"}, user_id=current_user.id, tenant_id=current_user.tenant_id)

    return StandardResponse(
        success=True, data={"status": "no_show"},
        request_id=request.state.request_id, message="Reservasi ditandai no-show",
    )
