from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.shift import Shift, CashActivity, ShiftStatus, CashActivityType
from backend.schemas.shift import (
    ShiftCreate, ShiftClose, ShiftResponse, ShiftWithActivitiesResponse,
    CashActivityCreate, CashActivityResponse, CashPaymentSummary, ShiftPauseResponse,
)
from backend.services import shift_service
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.models.payment import Payment
from backend.models.order import Order

router = APIRouter()


async def _enrich_shift_with_payments(db: AsyncSession, shift) -> dict:
    """Tambahkan data cash payments ke shift response."""
    shift_data = ShiftWithActivitiesResponse.model_validate(shift)

    # Query semua payments dari shift ini
    pay_query = select(Payment).where(
        Payment.shift_session_id == shift.id,
        Payment.status == 'paid',
        Payment.deleted_at.is_(None),
    ).order_by(Payment.created_at.desc())
    pay_result = await db.execute(pay_query)
    payments = pay_result.scalars().all()

    total_cash = 0.0
    total_qris = 0.0
    cash_payments_list = []

    for p in payments:
        net = float(p.amount_paid) - float(p.change_amount or 0)
        # Get display_number dari order
        display_number = None
        if p.order_id:
            order = await db.get(Order, p.order_id)
            if order:
                display_number = order.display_number

        cash_payments_list.append(CashPaymentSummary(
            id=p.id,
            order_id=p.order_id,
            display_number=display_number,
            amount=float(p.amount_paid),
            change_amount=float(p.change_amount or 0),
            net_amount=net,
            payment_method=p.payment_method,
            status=p.status,
            paid_at=p.paid_at,
            created_at=p.created_at,
        ))

        if p.payment_method == 'cash':
            total_cash += net
        elif p.payment_method == 'qris':
            total_qris += net

    shift_data.cash_payments = cash_payments_list
    shift_data.total_cash_sales = total_cash
    shift_data.total_qris_sales = total_qris
    return shift_data


@router.post("/open", response_model=StandardResponse[ShiftResponse])
async def open_shift(
    request: Request,
    outlet_id: UUID,
    shift_in: ShiftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Open a new shift for the current user in the specified outlet.
    """
    # Shift itu PER OUTLET (laci bersama), bukan per kasir — keputusan Ivan
    # 2026-09-02: "di resto yang nyata modal jadi satu". Yang pertama buka
    # shift pegang laci; kasir lain yang login tinggal GABUNG ke shift itu.
    # Siapa input apa tetap kecatat per akun lewat orders.user_id.
    # Shift per kasir (multi laci) = nanti, lewat setting outlet.
    query = select(Shift).where(
        Shift.outlet_id == outlet_id,
        Shift.status == ShiftStatus.open,
        Shift.deleted_at.is_(None)
    ).order_by(Shift.start_time.desc())
    result = await db.execute(query)
    existing_shift = result.scalars().first()
    
    if existing_shift and existing_shift.opened_by == "auto":
        # Sesi ini dibuka sistem di transaksi pertama, modal awalnya cuma
        # perkiraan. Kasir yang sekarang menekan "Buka kasir" lagi ngasih
        # angka modal yang sebenarnya: KLAIM sesi itu, jangan bikin yang baru
        # (transaksi yang udah jalan harus tetap di sesi yang sama).
        existing_shift.starting_cash = shift_in.starting_cash
        existing_shift.opened_by = "manual"
        existing_shift.user_id = current_user.id
        if shift_in.notes:
            existing_shift.notes = shift_in.notes
        existing_shift.row_version = (existing_shift.row_version or 0) + 1
        await log_audit(
            db=db, action="CLAIM_SHIFT", entity="shift", entity_id=existing_shift.id,
            after_state={"starting_cash": float(shift_in.starting_cash)},
            user_id=current_user.id, tenant_id=current_user.tenant_id,
        )
        await db.commit()
        await db.refresh(existing_shift)
        return StandardResponse(
            success=True,
            data=ShiftResponse.model_validate(existing_shift),
            request_id=request.state.request_id,
            message="Modal awal dicatat di sesi yang sedang berjalan",
        )

    if existing_shift:
        # Dulu: 400 "Shift sudah terbuka, tutup dulu" — tapi app yang baru
        # di-install / storage-nya bersih nggak punya shift_session_id lokal,
        # jadi dia nyoba buka lagi, ditolak, dan nggak ada jalan ke tutup
        # shift. Deadlock (kegigit Ivan 2026-09-02: shift open sejak 15 Jun).
        #
        # Sekarang:
        #  - shift masih segar (< 20 jam)  → RESUME: balikin shift itu, app
        #    nyimpen id-nya dan lanjut. Nggak bikin shift dobel.
        #  - shift basi (≥ 20 jam)         → tutup otomatis dengan catatan,
        #    lalu buka shift baru. Laporan per shift tetap bener.
        age = datetime.now(timezone.utc) - existing_shift.start_time
        if age < timedelta(hours=20):
            joining = existing_shift.user_id != current_user.id
            await log_audit(
                db=db, action="JOIN_SHIFT" if joining else "RESUME_SHIFT", entity="shift", entity_id=existing_shift.id,
                after_state={"age_hours": round(age.total_seconds() / 3600, 1), "opened_by": str(existing_shift.user_id)},
                user_id=current_user.id, tenant_id=current_user.tenant_id,
            )
            await db.commit()
            opener = await db.get(User, existing_shift.user_id)
            return StandardResponse(
                success=True,
                data=ShiftResponse.model_validate(existing_shift),
                request_id=request.state.request_id,
                message=(f"Gabung ke shift yang dibuka {opener.full_name if opener else 'kasir lain'}"
                         if joining else "Melanjutkan shift yang masih terbuka"),
            )
        await shift_service.close_shift(
            db, existing_shift, reason="auto_stale",
            user_id=current_user.id, tenant_id=current_user.tenant_id,
            notes=f"Ditutup otomatis: shift dibiarkan terbuka {age.days} hari, kasir buka shift baru",
        )
        await log_audit(
            db=db, action="AUTO_CLOSE_STALE_SHIFT", entity="shift", entity_id=existing_shift.id,
            after_state={"age_days": age.days}, user_id=current_user.id, tenant_id=current_user.tenant_id,
        )
        await db.flush()

    shift = Shift(
        outlet_id=outlet_id,
        user_id=current_user.id,
        status=ShiftStatus.open,
        starting_cash=shift_in.starting_cash,
        notes=shift_in.notes
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)

    await log_audit(
        db=db,
        action="OPEN_SHIFT",
        entity="shift",
        entity_id=shift.id,
        after_state={"starting_cash": float(shift.starting_cash)},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        success=True,
        data=ShiftResponse.model_validate(shift),
        request_id=request.state.request_id,
        message="Shift opened successfully"
    )

@router.get("/current", response_model=StandardResponse[Optional[dict]])
async def get_current_shift(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get the currently open shift for the user in the specified outlet.
    """
    query = select(Shift).options(selectinload(Shift.activities)).where(
        Shift.outlet_id == outlet_id,
        # per outlet — laci bersama, semua kasir lihat shift yang sama
        Shift.status == ShiftStatus.open,
        Shift.deleted_at.is_(None)
    ).order_by(Shift.start_time.desc())
    result = await db.execute(query)
    # Bisa ada >1 shift open (data lama sebelum laci bersama) — ambil yang
    # paling baru, jangan scalar_one_or_none (MultipleResultsFound → 500).
    shift = result.scalars().first()
    
    if not shift:
        return StandardResponse(
            success=True,
            data=None,
            request_id=request.state.request_id,
            message="No open shift found"
        )

    enriched = await _enrich_shift_with_payments(db, shift)
    data = enriched.model_dump(mode="json")
    mode = await shift_service.outlet_shift_mode(db, outlet_id)
    owner = await shift_service.is_owner(db, current_user)
    data["shift_mode"] = mode
    data["is_owner"] = owner
    data["participants"] = [
        {**p, "first_seen": p["first_seen"].isoformat() if p.get("first_seen") else None,
         "last_seen": p["last_seen"].isoformat() if p.get("last_seen") else None}
        for p in await shift_service.shift_participants(db, shift)
    ]
    opener = next((p for p in data["participants"] if p.get("opened")), None)
    data["opened_by_name"] = opener["name"] if opener else None
    data["uncounted_count"] = len(await shift_service.uncounted_shifts(db, outlet_id))
    data["blind_close"] = False
    if shift_service.blind_close_for(mode, owner):
        data = shift_service.blind_view(data)
    return StandardResponse(success=True, data=data, request_id=request.state.request_id)

@router.post("/{shift_id}/close", response_model=StandardResponse[dict])
async def close_shift(
    request: Request,
    shift_id: UUID,
    shift_in: ShiftClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Hitung kas dan tutup sesi. Berlaku untuk sesi terbuka maupun yang
    dijeda ("hitung nanti")."""
    query = select(Shift).where(Shift.id == shift_id, Shift.deleted_at.is_(None))
    shift = (await db.execute(query)).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift tidak ditemukan")
    if shift.status == ShiftStatus.closed:
        raise HTTPException(status_code=400, detail="Shift sudah ditutup")

    # Laci bersama: siapa pun kasir di tenant ini boleh nutup (yang buka bisa
    # aja udah pulang). Siapa yang nutup kecatat di closed_by_user_id.
    outlet = await db.get(Outlet, shift.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tidak berwenang menutup shift ini")

    result = await shift_service.close_shift(
        db, shift, reason="manual",
        user_id=current_user.id, tenant_id=current_user.tenant_id,
        ending_cash=shift_in.ending_cash, notes=shift_in.notes,
    )
    await db.commit()
    await db.refresh(shift)

    variance = result["variance"] or 0.0
    variance_status = result["variance_status"] or "balanced"
    resp = ShiftResponse.model_validate(shift)
    data = {**resp.model_dump(mode="json"), "variance": round(variance, 2), "variance_status": variance_status}
    mode = await shift_service.outlet_shift_mode(db, shift.outlet_id)
    if shift_service.blind_close_for(mode, await shift_service.is_owner(db, current_user)):
        # Blind close: kasir cuma dapat konfirmasi. Selisihnya dibaca pemilik
        # di dashboard, bukan jadi bahan tuduh di depan kasir.
        data = shift_service.blind_view(data)
        return StandardResponse(success=True, data=data, request_id=request.state.request_id,
                                message="Hitungan kas tercatat. Terima kasih.")
    return StandardResponse(
        success=True,
        data=data,
        request_id=request.state.request_id,
        message=f"Shift ditutup. {'Kas seimbang' if variance_status == 'balanced' else f'Selisih Rp {abs(variance):,.0f} ({variance_status})'}",
    )


@router.post("/{shift_id}/pause", response_model=StandardResponse[ShiftPauseResponse])
async def pause_shift(
    request: Request,
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """"Hitung nanti": jeda sesi ini, sesi baru langsung aktif. Penjualan
    nggak berhenti sementara laci lama dihitung dengan tenang."""
    shift = (await db.execute(
        select(Shift).where(Shift.id == shift_id, Shift.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift tidak ditemukan")
    if shift.status != ShiftStatus.open:
        raise HTTPException(status_code=400, detail="Hanya shift yang sedang terbuka yang bisa dijeda")
    outlet = await db.get(Outlet, shift.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tidak berwenang")

    paused, current = await shift_service.pause_shift(db, shift, current_user.id, current_user.tenant_id)
    await db.commit()
    await db.refresh(paused)
    await db.refresh(current)
    return StandardResponse(
        success=True,
        data=ShiftPauseResponse(
            paused=ShiftResponse.model_validate(paused),
            current=ShiftResponse.model_validate(current),
        ),
        request_id=request.state.request_id,
        message="Sesi dijeda. Sesi baru sudah berjalan, hitung laci kapan saja.",
    )


@router.get("/uncounted", response_model=StandardResponse[List[dict]])
async def list_uncounted_shifts(
    request: Request,
    outlet_id: UUID,
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Sesi yang kasnya belum dihitung: dijeda, atau ditutup sistem di 04.00.
    Bahan pengingat "Kas belum dihitung" di Beranda dan daftar di halaman
    kas. Yang ditutup kasir dengan hitungan nggak masuk sini."""
    rows = await shift_service.uncounted_shifts(db, outlet_id, days)
    mode = await shift_service.outlet_shift_mode(db, outlet_id)
    owner = await shift_service.is_owner(db, current_user)
    blind = shift_service.blind_close_for(mode, owner)
    out = []
    for r in rows:
        d = ShiftResponse.model_validate(r).model_dump(mode="json")
        parts = await shift_service.shift_participants(db, r)
        d["participants"] = [p["name"] for p in parts]
        opener = next((p for p in parts if p.get("opened")), None)
        d["opened_by_name"] = opener["name"] if opener else None
        if blind:
            d["expected_ending_cash"] = None
            d["starting_cash"] = None
        out.append(d)
    return StandardResponse(success=True, data=out, request_id=request.state.request_id)


@router.post("/{shift_id}/activities", response_model=StandardResponse[CashActivityResponse])
async def add_cash_activity(
    request: Request,
    shift_id: UUID,
    activity_in: CashActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Add a cash activity (income/expense) to a shift.
    """
    query = select(Shift).where(Shift.id == shift_id, Shift.deleted_at.is_(None))
    result = await db.execute(query)
    shift = result.scalar_one_or_none()
    
    if not shift:
        raise HTTPException(status_code=404, detail="Shift tidak ditemukan")
        
    if shift.status == ShiftStatus.closed:
        raise HTTPException(status_code=400, detail="Tidak bisa tambah aktivitas ke shift yang sudah tutup")

    # Laci bersama: kasir mana pun di tenant ini boleh catat kas keluar/masuk.
    outlet = await db.get(Outlet, shift.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tidak berwenang menambah aktivitas ke shift ini")

    activity = CashActivity(
        shift_id=shift_id,
        activity_type=activity_in.activity_type,
        amount=activity_in.amount,
        description=activity_in.description
    )
    db.add(activity)
    
    # Update shift row_version to trigger sync
    shift.row_version += 1
    
    await db.commit()
    await db.refresh(activity)

    await log_audit(
        db=db,
        action="ADD_CASH_ACTIVITY",
        entity="cash_activity",
        entity_id=activity.id,
        after_state={"type": activity.activity_type, "amount": float(activity.amount)},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        success=True,
        data=CashActivityResponse.model_validate(activity),
        request_id=request.state.request_id,
        message="Cash activity added successfully"
    )

@router.get("/{shift_id}/activities", response_model=StandardResponse)
async def get_cash_activities(
    request: Request,
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all cash activities for a shift.
    """
    query = select(CashActivity).where(
        CashActivity.shift_id == shift_id,
        CashActivity.deleted_at.is_(None)
    ).order_by(CashActivity.created_at.desc())
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Include cash payment transactions from this shift
    pay_query = select(Payment).where(
        Payment.shift_session_id == shift_id,
        Payment.status == 'paid',
        Payment.deleted_at.is_(None),
    ).order_by(Payment.created_at.desc())
    pay_result = await db.execute(pay_query)
    payments = pay_result.scalars().all()

    payment_items = []
    for p in payments:
        display_number = None
        if p.order_id:
            order = await db.get(Order, p.order_id)
            if order:
                display_number = order.display_number
        payment_items.append(CashPaymentSummary(
            id=p.id,
            order_id=p.order_id,
            display_number=display_number,
            amount=float(p.amount_paid),
            change_amount=float(p.change_amount or 0),
            net_amount=float(p.amount_paid) - float(p.change_amount or 0),
            payment_method=p.payment_method,
            status=p.status,
            paid_at=p.paid_at,
            created_at=p.created_at,
        ))

    return StandardResponse(
        success=True,
        data={
            "activities": [CashActivityResponse.model_validate(a) for a in activities],
            "cash_payments": [cp.model_dump(mode='json') for cp in payment_items],
        },
        request_id=request.state.request_id
    )
