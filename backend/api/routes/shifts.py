from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.shift import Shift, CashActivity, ShiftStatus, CashActivityType
from backend.schemas.shift import (
    ShiftCreate, ShiftClose, ShiftResponse, ShiftWithActivitiesResponse,
    CashActivityCreate, CashActivityResponse, CashPaymentSummary
)
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
    # Check if there's already an open shift for this user in this outlet
    query = select(Shift).where(
        Shift.outlet_id == outlet_id,
        Shift.user_id == current_user.id,
        Shift.status == ShiftStatus.open,
        Shift.deleted_at.is_(None)
    )
    result = await db.execute(query)
    existing_shift = result.scalar_one_or_none()
    
    if existing_shift:
        raise HTTPException(
            status_code=400, 
            detail="Shift sudah terbuka, tutup dulu"
        )

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

@router.get("/current", response_model=StandardResponse[Optional[ShiftWithActivitiesResponse]])
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
        Shift.user_id == current_user.id,
        Shift.status == ShiftStatus.open,
        Shift.deleted_at.is_(None)
    )
    result = await db.execute(query)
    shift = result.scalar_one_or_none()
    
    if not shift:
        return StandardResponse(
            success=True,
            data=None,
            request_id=request.state.request_id,
            message="No open shift found"
        )

    enriched = await _enrich_shift_with_payments(db, shift)
    return StandardResponse(
        success=True,
        data=enriched,
        request_id=request.state.request_id
    )

@router.post("/{shift_id}/close", response_model=StandardResponse[ShiftResponse])
async def close_shift(
    request: Request,
    shift_id: UUID,
    shift_in: ShiftClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Close a shift.
    """
    query = select(Shift).where(Shift.id == shift_id, Shift.deleted_at.is_(None))
    result = await db.execute(query)
    shift = result.scalar_one_or_none()
    
    if not shift:
        raise HTTPException(status_code=404, detail="Shift tidak ditemukan")
        
    if shift.status == ShiftStatus.closed:
        raise HTTPException(status_code=400, detail="Shift sudah ditutup")
        
    if shift.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Tidak berwenang menutup shift ini")

    # Calculate expected cash
    # expected_cash = starting_cash + total_income - total_expense + cash_payments
    # For now, we just sum up cash_activities. In a real scenario, we also need to sum up cash payments from orders.
    activities_query = select(
        CashActivity.activity_type, 
        func.sum(CashActivity.amount).label("total")
    ).where(
        CashActivity.shift_id == shift_id,
        CashActivity.deleted_at.is_(None)
    ).group_by(CashActivity.activity_type)
    
    activities_result = await db.execute(activities_query)
    totals = {row.activity_type: row.total for row in activities_result.all()}
    
    income = totals.get(CashActivityType.income, 0)
    expense = totals.get(CashActivityType.expense, 0)
    
    # Calculate cash payments from orders
    cash_payments_query = select(
        func.sum(Payment.amount_paid - Payment.change_amount).label("total_cash")
    ).where(
        Payment.shift_session_id == shift_id,
        Payment.payment_method == 'cash',
        Payment.status == 'paid',
        Payment.deleted_at.is_(None)
    )
    
    cash_payments_result = await db.execute(cash_payments_query)
    total_cash_payments = cash_payments_result.scalar() or 0
    
    expected_cash = float(shift.starting_cash) + float(income) - float(expense) + float(total_cash_payments)

    shift.status = ShiftStatus.closed
    shift.end_time = datetime.now(timezone.utc)
    shift.ending_cash = shift_in.ending_cash
    shift.expected_ending_cash = expected_cash
    if shift_in.notes:
        shift.notes = shift_in.notes
    shift.row_version += 1

    await db.commit()
    await db.refresh(shift)

    await log_audit(
        db=db,
        action="CLOSE_SHIFT",
        entity="shift",
        entity_id=shift.id,
        after_state={"ending_cash": float(shift.ending_cash), "expected_ending_cash": float(shift.expected_ending_cash)},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        success=True,
        data=ShiftResponse.model_validate(shift),
        request_id=request.state.request_id,
        message="Shift closed successfully"
    )

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

    if shift.user_id != current_user.id and not current_user.is_superuser:
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

@router.get("/{shift_id}/activities", response_model=StandardResponse[List[CashActivityResponse]])
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
