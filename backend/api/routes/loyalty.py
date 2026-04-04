"""
Kasira Loyalty Points Route

GET  /loyalty/balance               → saldo poin customer
POST /loyalty/earn                  → tambah poin dari order (idempoten via UNIQUE order_id+type)
POST /loyalty/redeem                → tukar poin (optimistic lock via row_version)
GET  /loyalty/history               → riwayat transaksi poin

Aturan:
- 1 poin per Rp10.000 (earn)
- 1 poin = Rp100 (redeem value)
- Min 10 poin untuk redeem
- UNIQUE(order_id, type) — Rule #35: double points = trust hancur
- Optimistic lock via row_version — Rule #30
- Rule #2: Audit log setiap WRITE
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.customer import Customer
from backend.models.loyalty import CustomerPoints, PointTransaction
from backend.models.outlet import Outlet
from backend.models.user import User
from backend.services.audit import log_audit

router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])
logger = logging.getLogger(__name__)

POINTS_PER_RUPIAH = 10_000   # Rp10.000 → 1 poin
REDEEM_VALUE = 100            # 1 poin = Rp100
MIN_REDEEM = 10               # min 10 poin untuk redeem


class EarnPointsInput(BaseModel):
    customer_id: UUID
    outlet_id: UUID
    order_id: UUID
    amount: float = Field(gt=0, description="Total transaksi dalam Rupiah")


class RedeemPointsInput(BaseModel):
    customer_id: UUID
    outlet_id: UUID
    points: int = Field(gt=0)
    order_id: Optional[UUID] = None
    row_version: int = Field(..., description="Expected row_version (optimistic lock)")


@router.get("/balance")
async def get_balance(
    customer_id: UUID = Query(...),
    outlet_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Saldo poin aktif customer di outlet ini."""
    # Validate outlet ownership
    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    cp_result = await db.execute(
        select(CustomerPoints).where(
            CustomerPoints.customer_id == customer_id,
            CustomerPoints.outlet_id == outlet_id,
            CustomerPoints.deleted_at.is_(None),
        )
    )
    cp = cp_result.scalar_one_or_none()

    balance = cp.balance if cp else 0
    lifetime = cp.lifetime_earned if cp else 0
    row_version = cp.row_version if cp else 0

    return {
        "success": True,
        "data": {
            "balance": balance,
            "lifetime_earned": lifetime,
            "redeem_value_per_point": REDEEM_VALUE,
            "min_redeem_points": MIN_REDEEM,
            "balance_rupiah": balance * REDEEM_VALUE,
            "row_version": row_version,
        },
    }


@router.post("/earn")
async def earn_points(
    body: EarnPointsInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Tambah poin dari order. Idempoten via UNIQUE(order_id, type='earn') — Rule #35.
    1 poin per Rp10.000 dibulatkan ke bawah.
    """
    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == body.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    # Check idempotency — sudah di-earn untuk order ini?
    existing = await db.execute(
        select(PointTransaction).where(
            PointTransaction.order_id == body.order_id,
            PointTransaction.type == 'earn',
        )
    )
    if existing.scalar_one_or_none():
        # Already earned — return current balance idempotently
        cp_result = await db.execute(
            select(CustomerPoints).where(
                CustomerPoints.customer_id == body.customer_id,
                CustomerPoints.outlet_id == body.outlet_id,
            )
        )
        cp = cp_result.scalar_one_or_none()
        return {
            "success": True,
            "data": {"points_earned": 0, "balance": cp.balance if cp else 0, "idempotent": True},
            "message": "Poin sudah pernah ditambahkan untuk order ini",
        }

    points_earned = int(body.amount // POINTS_PER_RUPIAH)
    if points_earned == 0:
        return {
            "success": True,
            "data": {"points_earned": 0, "balance": 0},
            "message": "Transaksi terlalu kecil untuk mendapat poin",
        }

    # Get or create CustomerPoints
    cp_result = await db.execute(
        select(CustomerPoints).where(
            CustomerPoints.customer_id == body.customer_id,
            CustomerPoints.outlet_id == body.outlet_id,
            CustomerPoints.deleted_at.is_(None),
        ).with_for_update()
    )
    cp = cp_result.scalar_one_or_none()
    if not cp:
        cp = CustomerPoints(
            customer_id=body.customer_id,
            outlet_id=body.outlet_id,
            balance=0,
            lifetime_earned=0,
        )
        db.add(cp)
        await db.flush()

    cp.balance += points_earned
    cp.lifetime_earned += points_earned
    cp.row_version += 1

    txn = PointTransaction(
        customer_id=body.customer_id,
        outlet_id=body.outlet_id,
        order_id=body.order_id,
        type='earn',
        points=points_earned,
        description=f"Earn dari transaksi Rp{int(body.amount):,}",
    )
    db.add(txn)

    await log_audit(
        db=db,
        action="loyalty_earn",
        entity="customer_points",
        entity_id=str(body.customer_id),
        after_state={"points_earned": points_earned, "new_balance": cp.balance, "order_id": str(body.order_id)},
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )
    await db.commit()

    return {
        "success": True,
        "data": {"points_earned": points_earned, "balance": cp.balance},
        "message": f"+{points_earned} poin ditambahkan",
    }


@router.post("/redeem")
async def redeem_points(
    body: RedeemPointsInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Tukar poin jadi diskon. Optimistic lock via row_version (Rule #30).
    Min 10 poin. Nilai 1 poin = Rp100.
    """
    if body.points < MIN_REDEEM:
        raise HTTPException(status_code=400, detail=f"Minimum redeem {MIN_REDEEM} poin")

    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == body.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    cp_result = await db.execute(
        select(CustomerPoints).where(
            CustomerPoints.customer_id == body.customer_id,
            CustomerPoints.outlet_id == body.outlet_id,
            CustomerPoints.deleted_at.is_(None),
        ).with_for_update()
    )
    cp = cp_result.scalar_one_or_none()
    if not cp or cp.balance < body.points:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo poin tidak cukup (saldo: {cp.balance if cp else 0}, dibutuhkan: {body.points})",
        )

    # Optimistic lock (Rule #30)
    if cp.row_version != body.row_version:
        raise HTTPException(
            status_code=409,
            detail="Data poin berubah, refresh dan coba lagi",
        )

    discount_amount = body.points * REDEEM_VALUE
    cp.balance -= body.points
    cp.row_version += 1

    txn = PointTransaction(
        customer_id=body.customer_id,
        outlet_id=body.outlet_id,
        order_id=body.order_id,
        type='redeem',
        points=body.points,
        description=f"Redeem {body.points} poin = Rp{discount_amount:,} diskon",
    )
    db.add(txn)

    await log_audit(
        db=db,
        action="loyalty_redeem",
        entity="customer_points",
        entity_id=str(body.customer_id),
        after_state={"points_redeemed": body.points, "discount": discount_amount, "new_balance": cp.balance},
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "points_redeemed": body.points,
            "discount_amount": discount_amount,
            "new_balance": cp.balance,
        },
        "message": f"{body.points} poin ditukar menjadi diskon Rp{discount_amount:,}",
    }


@router.get("/history")
async def get_history(
    customer_id: UUID = Query(...),
    outlet_id: UUID = Query(...),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Riwayat transaksi poin customer."""
    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    if not outlet_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    result = await db.execute(
        select(PointTransaction).where(
            PointTransaction.customer_id == customer_id,
            PointTransaction.outlet_id == outlet_id,
            PointTransaction.deleted_at.is_(None),
        ).order_by(PointTransaction.created_at.desc()).limit(limit)
    )
    transactions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(t.id),
                "type": t.type,
                "points": t.points,
                "description": t.description,
                "order_id": str(t.order_id) if t.order_id else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
    }
