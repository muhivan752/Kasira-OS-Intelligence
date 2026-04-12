import random
import string
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.referral import Referral, ReferralCommission
from backend.schemas.referral import ReferralResponse, ReferralStatsResponse, CommissionResponse
from backend.schemas.response import StandardResponse

router = APIRouter()

COMMISSION_PCT = 20  # 20% recurring


def _generate_code(name: str) -> str:
    """Generate referral code: first 3 chars of name + 5 random alphanumeric."""
    prefix = "".join(c for c in name.upper() if c.isalpha())[:3].ljust(3, "X")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{prefix}-{suffix}"


@router.get("/my-code", response_model=StandardResponse[dict])
async def get_my_referral_code(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get or generate referral code for current tenant."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")

    if not tenant.referral_code:
        for _ in range(10):
            code = _generate_code(tenant.name)
            existing = (await db.execute(
                select(Tenant).where(Tenant.referral_code == code)
            )).scalar_one_or_none()
            if not existing:
                break
        else:
            raise HTTPException(status_code=500, detail="Gagal generate kode referral")

        tenant.referral_code = code
        await db.commit()
        await db.refresh(tenant)

    return StandardResponse(data={
        "referral_code": tenant.referral_code,
        "commission_pct": COMMISSION_PCT,
        "share_url": f"https://kasira.online/register?ref={tenant.referral_code}",
        "share_text": (
            f"Pakai Kasira POS buat bisnis kamu! Daftar gratis di "
            f"https://kasira.online/register?ref={tenant.referral_code} "
            f"— POS digital lengkap untuk UMKM."
        ),
    })


@router.get("/stats", response_model=StandardResponse[ReferralStatsResponse])
async def get_referral_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get referral statistics + commission earnings."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant or not tenant.referral_code:
        return StandardResponse(data=ReferralStatsResponse(
            referral_code="", commission_pct=COMMISSION_PCT,
            total_referrals=0, active_referrals=0,
            total_earned=0, pending_balance=0,
        ))

    # Fetch referrals with referred tenant info
    stmt = (
        select(Referral, Tenant.name.label("referred_name"), Tenant.subscription_tier)
        .join(Tenant, Tenant.id == Referral.referred_tenant_id)
        .where(
            Referral.referrer_tenant_id == current_user.tenant_id,
            Referral.deleted_at == None,
        )
        .order_by(Referral.created_at.desc())
    )
    results = (await db.execute(stmt)).all()

    # Commission per referral
    referral_ids = [r.id for r, _, _ in results]
    commission_sums = {}
    if referral_ids:
        comm_stmt = (
            select(
                ReferralCommission.referral_id,
                func.sum(ReferralCommission.commission_amount).label("total"),
            )
            .where(
                ReferralCommission.referral_id.in_(referral_ids),
                ReferralCommission.deleted_at == None,
            )
            .group_by(ReferralCommission.referral_id)
        )
        for row in (await db.execute(comm_stmt)).all():
            commission_sums[row.referral_id] = int(row.total or 0)

    referrals = []
    active_count = 0
    for ref, referred_name, referred_tier in results:
        tier_str = referred_tier.value if hasattr(referred_tier, "value") else str(referred_tier or "starter")
        if ref.status == "active":
            active_count += 1
        referrals.append(ReferralResponse(
            id=ref.id,
            referrer_tenant_id=ref.referrer_tenant_id,
            referred_tenant_id=ref.referred_tenant_id,
            referral_code=ref.referral_code,
            commission_pct=ref.commission_pct,
            status=ref.status,
            created_at=ref.created_at,
            referred_name=referred_name,
            referred_tier=tier_str,
            total_commission=commission_sums.get(ref.id, 0),
        ))

    # Total earned + pending
    total_earned = (await db.execute(
        select(func.coalesce(func.sum(ReferralCommission.commission_amount), 0))
        .where(
            ReferralCommission.referrer_tenant_id == current_user.tenant_id,
            ReferralCommission.status == "paid",
            ReferralCommission.deleted_at == None,
        )
    )).scalar() or 0

    pending_balance = (await db.execute(
        select(func.coalesce(func.sum(ReferralCommission.commission_amount), 0))
        .where(
            ReferralCommission.referrer_tenant_id == current_user.tenant_id,
            ReferralCommission.status == "pending",
            ReferralCommission.deleted_at == None,
        )
    )).scalar() or 0

    # Recent commissions
    recent_stmt = (
        select(ReferralCommission, Tenant.name.label("referred_name"))
        .join(Referral, Referral.id == ReferralCommission.referral_id)
        .join(Tenant, Tenant.id == Referral.referred_tenant_id)
        .where(
            ReferralCommission.referrer_tenant_id == current_user.tenant_id,
            ReferralCommission.deleted_at == None,
        )
        .order_by(ReferralCommission.created_at.desc())
        .limit(20)
    )
    recent = (await db.execute(recent_stmt)).all()

    commissions = [
        CommissionResponse(
            id=c.id,
            invoice_amount=c.invoice_amount,
            commission_pct=c.commission_pct,
            commission_amount=c.commission_amount,
            status=c.status,
            created_at=c.created_at,
            referred_name=name,
        ) for c, name in recent
    ]

    return StandardResponse(data=ReferralStatsResponse(
        referral_code=tenant.referral_code,
        commission_pct=COMMISSION_PCT,
        total_referrals=len(referrals),
        active_referrals=active_count,
        total_earned=int(total_earned),
        pending_balance=int(pending_balance),
        referrals=referrals,
        recent_commissions=commissions,
    ))


@router.get("/validate/{code}", response_model=StandardResponse[dict])
async def validate_referral_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Validate referral code (public, no auth). Used during registration."""
    tenant = (await db.execute(
        select(Tenant).where(
            Tenant.referral_code == code.upper().strip(),
            Tenant.is_active == True,
            Tenant.deleted_at == None,
        )
    )).scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Kode referral tidak valid")

    return StandardResponse(data={
        "valid": True,
        "referrer_name": tenant.name,
        "benefit": f"Referrer dapat {COMMISSION_PCT}% komisi dari langganan kamu setiap bulan",
    })
