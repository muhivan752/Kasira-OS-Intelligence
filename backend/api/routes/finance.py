"""
/finance — keuangan ringan (semua tier, keputusan Ivan 2026-09-02 "gas semuanya").

  GET  /finance/summary?outlet_id&month=YYYY-MM   laba rugi + arus kas + tren 6 bulan
  GET  /finance/categories                         daftar kategori pengeluaran
  GET  /finance/accounts                           akun kas (auto-seed 3 akun)
  PUT  /finance/accounts/{id}
  GET  /finance/expenses?outlet_id&month
  POST /finance/expenses
  PUT  /finance/expenses/{id}
  DELETE /finance/expenses/{id}
  POST /finance/expenses/copy-recurring?outlet_id&month   salin template bulanan
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.finance import Expense, CashAccount, EXPENSE_CATEGORIES
from backend.models.event import Event
from backend.schemas.finance import (
    FinanceSummary, CashAccountResponse, CashAccountUpdate,
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services import finance_service as svc

logger = logging.getLogger(__name__)
router = APIRouter()


async def _outlet(db: AsyncSession, outlet_id: UUID, tenant_id: UUID) -> Outlet:
    o = (await db.execute(select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None)))).scalar_one_or_none()
    if not o or o.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    return o


def _current_month() -> str:
    return datetime.now(svc.WIB).strftime("%Y-%m")


@router.get("/summary", response_model=StandardResponse[FinanceSummary])
async def finance_summary(
    request: Request,
    outlet_id: UUID,
    month: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    outlet = await _outlet(db, outlet_id, current_user.tenant_id)
    data = await svc.summary(db, tenant_id=current_user.tenant_id, outlet=outlet, month=month or _current_month())
    await db.commit()  # ensure_accounts bisa nge-seed
    return StandardResponse(success=True, data=data, request_id=request.state.request_id)


@router.get("/categories", response_model=StandardResponse[list])
async def categories(request: Request, current_user: User = Depends(deps.get_current_user)) -> Any:
    return StandardResponse(
        success=True, data=[{"key": k, "label": v} for k, v in EXPENSE_CATEGORIES],
        request_id=request.state.request_id,
    )


@router.get("/accounts", response_model=StandardResponse[List[CashAccountResponse]])
async def list_accounts(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    accs = await svc.ensure_accounts(db, current_user.tenant_id)
    await db.commit()
    return StandardResponse(success=True, data=[CashAccountResponse.model_validate(a) for a in accs], request_id=request.state.request_id)


@router.put("/accounts/{account_id}", response_model=StandardResponse[CashAccountResponse])
async def update_account(
    request: Request, account_id: UUID, body: CashAccountUpdate,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    acc = (await db.execute(select(CashAccount).where(
        CashAccount.id == account_id, CashAccount.tenant_id == current_user.tenant_id, CashAccount.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Akun kas tidak ditemukan")
    if acc.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Akun sudah berubah, muat ulang")
    for k, v in body.model_dump(exclude_unset=True, exclude={"row_version"}).items():
        setattr(acc, k, v)
    acc.row_version += 1
    await log_audit(db=db, action="UPDATE", entity="cash_accounts", entity_id=acc.id,
                    after_state=body.model_dump(exclude_unset=True), user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit(); await db.refresh(acc)
    return StandardResponse(success=True, data=CashAccountResponse.model_validate(acc), request_id=request.state.request_id)


@router.get("/expenses", response_model=StandardResponse[List[ExpenseResponse]])
async def list_expenses(
    request: Request, outlet_id: UUID, month: Optional[str] = None,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet(db, outlet_id, current_user.tenant_id)
    rows = await svc.list_expenses(db, tenant_id=current_user.tenant_id, outlet_id=outlet_id, month=month or _current_month())
    return StandardResponse(success=True, data=[svc.expense_to_response(e) for e in rows], request_id=request.state.request_id)


@router.post("/expenses", response_model=StandardResponse[ExpenseResponse])
async def create_expense(
    request: Request, body: ExpenseCreate,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    if body.outlet_id:
        await _outlet(db, body.outlet_id, current_user.tenant_id)
    accounts = await svc.ensure_accounts(db, current_user.tenant_id)
    acc_id = body.cash_account_id
    if acc_id and not any(a.id == acc_id for a in accounts):
        raise HTTPException(status_code=404, detail="Akun kas tidak ditemukan")
    if not acc_id:
        acc = svc.account_for_method(accounts, body.payment_method)
        acc_id = acc.id if acc else None

    e = Expense(
        tenant_id=current_user.tenant_id, outlet_id=body.outlet_id, category=body.category,
        amount=body.amount, paid_at=body.paid_at or datetime.now(timezone.utc),
        payment_method=body.payment_method, cash_account_id=acc_id, supplier_id=body.supplier_id,
        note=(body.note or None), photo_url=body.photo_url, recurring=body.recurring, recorded_by=current_user.id,
    )
    db.add(e); await db.flush()
    if body.outlet_id:
        db.add(Event(
            outlet_id=body.outlet_id, stream_id=f"expense:{e.id}", event_type="expense.recorded",
            event_data={"expense_id": str(e.id), "category": e.category, "amount": str(e.amount),
                        "paid_at": e.paid_at.isoformat(), "user_id": str(current_user.id)},
        ))
    await log_audit(db=db, action="CREATE", entity="expenses", entity_id=e.id,
                    after_state={"category": e.category, "amount": str(e.amount), "note": e.note},
                    user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit()
    e = (await db.execute(select(Expense).options(selectinload(Expense.cash_account), selectinload(Expense.supplier)).where(Expense.id == e.id))).scalar_one()
    return StandardResponse(success=True, data=svc.expense_to_response(e), message="Pengeluaran dicatat", request_id=request.state.request_id)


@router.put("/expenses/{expense_id}", response_model=StandardResponse[ExpenseResponse])
async def update_expense(
    request: Request, expense_id: UUID, body: ExpenseUpdate,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    e = (await db.execute(select(Expense).options(selectinload(Expense.cash_account), selectinload(Expense.supplier)).where(
        Expense.id == expense_id, Expense.tenant_id == current_user.tenant_id, Expense.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Pengeluaran tidak ditemukan")
    if e.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data sudah berubah, muat ulang")
    if e.purchase_id:
        raise HTTPException(status_code=400, detail="Pengeluaran dari nota belanja diubah lewat notanya")
    changes = body.model_dump(exclude_unset=True, exclude={"row_version"})
    if "category" in changes:
        changes["category"] = ExpenseCreate.model_validate({"amount": 1, "category": changes["category"]}).category
    before = {"category": e.category, "amount": str(e.amount), "note": e.note}
    for k, v in changes.items():
        setattr(e, k, v)
    e.row_version += 1
    await log_audit(db=db, action="UPDATE", entity="expenses", entity_id=e.id, before_state=before,
                    after_state={k: (str(v) if v is not None else None) for k, v in changes.items()},
                    user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit(); await db.refresh(e)
    return StandardResponse(success=True, data=svc.expense_to_response(e), message="Pengeluaran diperbarui", request_id=request.state.request_id)


@router.delete("/expenses/{expense_id}", response_model=StandardResponse[dict])
async def delete_expense(
    request: Request, expense_id: UUID,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    e = (await db.execute(select(Expense).where(
        Expense.id == expense_id, Expense.tenant_id == current_user.tenant_id, Expense.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Pengeluaran tidak ditemukan")
    if e.purchase_id:
        raise HTTPException(status_code=400, detail="Pengeluaran dari nota belanja nggak bisa dihapus terpisah")
    e.deleted_at = datetime.now(timezone.utc); e.row_version += 1
    await log_audit(db=db, action="DELETE", entity="expenses", entity_id=e.id,
                    before_state={"category": e.category, "amount": str(e.amount)},
                    user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Pengeluaran dihapus", request_id=request.state.request_id)


@router.post("/expenses/copy-recurring", response_model=StandardResponse[List[ExpenseResponse]])
async def copy_recurring(
    request: Request, outlet_id: UUID, month: Optional[str] = None,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet(db, outlet_id, current_user.tenant_id)
    created = await svc.copy_recurring(db, tenant_id=current_user.tenant_id, outlet_id=outlet_id,
                                       month=month or _current_month(), user_id=current_user.id)
    for e in created:
        await log_audit(db=db, action="CREATE", entity="expenses", entity_id=e.id,
                        after_state={"category": e.category, "amount": str(e.amount), "note": e.note, "copied": True},
                        user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit()
    ids = [e.id for e in created]
    rows = (await db.execute(select(Expense).options(selectinload(Expense.cash_account), selectinload(Expense.supplier)).where(Expense.id.in_(ids)))).scalars().all() if ids else []
    return StandardResponse(success=True, data=[svc.expense_to_response(e) for e in rows],
                            message=f"{len(rows)} pengeluaran bulanan disalin" if rows else "Tidak ada yang perlu disalin",
                            request_id=request.state.request_id)
