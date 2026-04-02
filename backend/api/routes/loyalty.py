"""
Loyalty Points — earn, redeem, balance, history

Aturan bisnis (configurable nanti via tenant settings):
  EARN_RATE   = 1 poin per Rp 10.000 transaksi
  REDEEM_RATE = 1 poin = Rp 100 diskon
  MIN_REDEEM  = 10 poin
"""
import uuid
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.models.customer import Customer
from backend.models.loyalty import CustomerPoints, PointTransaction
from backend.models.user import User
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter()

# ── Konstanta ────────────────────────────────────────────────────────────────
EARN_RATE: Decimal = Decimal("10000")   # Rp per 1 poin
REDEEM_RATE: Decimal = Decimal("100")   # Rp per 1 poin
MIN_REDEEM: Decimal = Decimal("10")     # minimum poin untuk redeem


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_points(db: AsyncSession, customer_id: uuid.UUID) -> CustomerPoints:
    stmt = select(CustomerPoints).where(CustomerPoints.customer_id == customer_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        row = CustomerPoints(
            id=uuid.uuid4(),
            customer_id=customer_id,
            balance=Decimal("0"),
            lifetime_earned=Decimal("0"),
            lifetime_redeemed=Decimal("0"),
            row_version=0,
        )
        db.add(row)
        await db.flush()
    return row


# ── Schemas ──────────────────────────────────────────────────────────────────

class PointsBalanceResponse(BaseModel):
    customer_id: str
    customer_name: str
    balance: float
    lifetime_earned: float
    lifetime_redeemed: float
    redeem_value_rp: float  # nilai rupiah jika semua poin diredeeem


class EarnPointsRequest(BaseModel):
    customer_id: str
    order_id: str
    transaction_amount: float = Field(..., gt=0)


class RedeemPointsRequest(BaseModel):
    customer_id: str
    order_id: str
    points_to_redeem: float = Field(..., gt=0)


class PointTxnResponse(BaseModel):
    id: str
    type: str
    amount: float
    balance_after: float
    description: Optional[str]
    created_at: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{customer_id}/balance", response_model=StandardResponse[PointsBalanceResponse])
async def get_balance(
    customer_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Cek saldo poin pelanggan."""
    cid = uuid.UUID(customer_id)

    customer = (await db.execute(
        select(Customer).where(Customer.id == cid, Customer.deleted_at == None)
    )).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")

    pts = await _get_or_create_points(db, cid)
    await db.commit()

    return StandardResponse(data=PointsBalanceResponse(
        customer_id=str(cid),
        customer_name=customer.name,
        balance=float(pts.balance),
        lifetime_earned=float(pts.lifetime_earned),
        lifetime_redeemed=float(pts.lifetime_redeemed),
        redeem_value_rp=float(pts.balance * REDEEM_RATE),
    ))


@router.post("/earn", response_model=StandardResponse[PointTxnResponse])
async def earn_points(
    body: EarnPointsRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Tambah poin setelah transaksi selesai.
    Dipanggil otomatis oleh orders route saat status=completed.
    Golden Rule #35: UNIQUE(order_id, type) — idempoten.
    """
    cid = uuid.UUID(body.customer_id)
    oid = uuid.UUID(body.order_id)

    # Idempoten — jika sudah ada earn untuk order ini, skip
    existing = (await db.execute(
        select(PointTransaction).where(
            PointTransaction.order_id == oid,
            PointTransaction.type == "earn",
        )
    )).scalar_one_or_none()
    if existing:
        return StandardResponse(data=PointTxnResponse(
            id=str(existing.id),
            type=existing.type,
            amount=float(existing.amount),
            balance_after=float(existing.balance_after),
            description=existing.description,
            created_at=existing.created_at.isoformat(),
        ), message="Poin sudah pernah diberikan untuk order ini")

    earned = Decimal(str(body.transaction_amount)) // EARN_RATE
    if earned <= 0:
        raise HTTPException(status_code=400, detail="Transaksi terlalu kecil untuk mendapat poin")

    # Optimistic lock (Rule #30)
    pts = await _get_or_create_points(db, cid)
    expected_version = pts.row_version
    pts.balance += earned
    pts.lifetime_earned += earned
    pts.row_version += 1

    rows = await db.execute(
        __import__('sqlalchemy').update(CustomerPoints)
        .where(CustomerPoints.customer_id == cid, CustomerPoints.row_version == expected_version)
        .values(balance=pts.balance, lifetime_earned=pts.lifetime_earned, row_version=pts.row_version)
    )
    if rows.rowcount == 0:
        raise HTTPException(status_code=409, detail="Konflik update poin, silakan coba lagi")

    txn = PointTransaction(
        id=uuid.uuid4(),
        customer_id=cid,
        order_id=oid,
        type="earn",
        amount=earned,
        balance_after=pts.balance,
        description=f"+{int(earned)} poin dari transaksi Rp {int(body.transaction_amount):,}",
    )
    db.add(txn)
    await db.commit()

    await log_audit(db, action="earn_points", entity="point_transactions",
                    entity_id=str(txn.id),
                    after_state={"customer_id": body.customer_id, "earned": float(earned)},
                    user_id=str(current_user.id))

    return StandardResponse(data=PointTxnResponse(
        id=str(txn.id), type=txn.type, amount=float(txn.amount),
        balance_after=float(txn.balance_after), description=txn.description,
        created_at=txn.created_at.isoformat(),
    ), message=f"+{int(earned)} poin berhasil ditambahkan")


@router.post("/redeem", response_model=StandardResponse[dict])
async def redeem_points(
    body: RedeemPointsRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Tukar poin jadi diskon saat checkout.
    Return: discount_amount (Rp) yang harus dikurangi dari total order.
    """
    cid = uuid.UUID(body.customer_id)
    oid = uuid.UUID(body.order_id)
    to_redeem = Decimal(str(body.points_to_redeem))

    if to_redeem < MIN_REDEEM:
        raise HTTPException(status_code=400, detail=f"Minimum redeem {int(MIN_REDEEM)} poin")

    # Idempoten
    existing = (await db.execute(
        select(PointTransaction).where(
            PointTransaction.order_id == oid,
            PointTransaction.type == "redeem",
        )
    )).scalar_one_or_none()
    if existing:
        return StandardResponse(data={
            "discount_amount": float(existing.amount * REDEEM_RATE),
            "points_redeemed": float(existing.amount),
        }, message="Poin sudah pernah di-redeem untuk order ini")

    pts = await _get_or_create_points(db, cid)
    if pts.balance < to_redeem:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo poin tidak cukup. Saldo: {int(pts.balance)}, diminta: {int(to_redeem)}"
        )

    discount_rp = to_redeem * REDEEM_RATE

    # Optimistic lock
    expected_version = pts.row_version
    pts.balance -= to_redeem
    pts.lifetime_redeemed += to_redeem
    pts.row_version += 1

    rows = await db.execute(
        __import__('sqlalchemy').update(CustomerPoints)
        .where(CustomerPoints.customer_id == cid, CustomerPoints.row_version == expected_version)
        .values(balance=pts.balance, lifetime_redeemed=pts.lifetime_redeemed, row_version=pts.row_version)
    )
    if rows.rowcount == 0:
        raise HTTPException(status_code=409, detail="Konflik update poin, silakan coba lagi")

    txn = PointTransaction(
        id=uuid.uuid4(),
        customer_id=cid,
        order_id=oid,
        type="redeem",
        amount=to_redeem,
        balance_after=pts.balance,
        description=f"-{int(to_redeem)} poin = diskon Rp {int(discount_rp):,}",
    )
    db.add(txn)
    await db.commit()

    await log_audit(db, action="redeem_points", entity="point_transactions",
                    entity_id=str(txn.id),
                    after_state={"customer_id": body.customer_id, "redeemed": float(to_redeem), "discount_rp": float(discount_rp)},
                    user_id=str(current_user.id))

    return StandardResponse(data={
        "discount_amount": float(discount_rp),
        "points_redeemed": float(to_redeem),
        "remaining_balance": float(pts.balance),
    }, message=f"Redeem {int(to_redeem)} poin → diskon Rp {int(discount_rp):,}")


@router.get("/{customer_id}/history", response_model=StandardResponse[List[PointTxnResponse]])
async def get_history(
    customer_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Riwayat transaksi poin pelanggan (20 terakhir)."""
    cid = uuid.UUID(customer_id)
    stmt = (
        select(PointTransaction)
        .where(PointTransaction.customer_id == cid, PointTransaction.deleted_at == None)
        .order_by(desc(PointTransaction.created_at))
        .limit(20)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return StandardResponse(data=[
        PointTxnResponse(
            id=str(r.id), type=r.type, amount=float(r.amount),
            balance_after=float(r.balance_after), description=r.description,
            created_at=r.created_at.isoformat(),
        ) for r in rows
    ])
