from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class ReferralResponse(BaseModel):
    id: UUID
    referrer_tenant_id: UUID
    referred_tenant_id: UUID
    referral_code: str
    commission_pct: int
    status: str
    created_at: datetime
    referred_name: Optional[str] = None
    referred_tier: Optional[str] = None
    total_commission: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class CommissionResponse(BaseModel):
    id: UUID
    invoice_amount: int
    commission_pct: int
    commission_amount: int
    status: str
    created_at: datetime
    referred_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReferralStatsResponse(BaseModel):
    referral_code: str
    commission_pct: int
    total_referrals: int
    active_referrals: int
    total_earned: int
    pending_balance: int
    referrals: list[ReferralResponse] = []
    recent_commissions: list[CommissionResponse] = []
