"""
Subscription lifecycle helpers — tier check, cache, downgrade cascade.

Fix CRITICAL audit #15 + #16:
  #15 — Tier expiry check harus efisien (gak hit DB per request) + fail-closed
        kalau tenant suspended/expired. `require_pro_tier` dulu cuma cek enum,
        lolos untuk tenant expired/suspended.
  #16 — Downgrade logic wajib cascade:
        - Reset outlet.stock_mode ke simple (cegah ghost stock mode=recipe
          tapi ingredient endpoint 403)
        - Validate outlet count vs tier limit (Starter max 1 outlet)
        - Preserve data (soft-signal, tidak auto-delete/deactivate)

Scope: helper service. Dipakai dari deps.py, superadmin.py, outlets.py,
tasks/subscription_billing.py. Zero direct route/model change di sini —
cuma helpers.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.outlet import Outlet
from backend.models.tenant import Tenant

logger = logging.getLogger(__name__)


# ─── Constants ────────────────────────────────────────────────────────────────
PRO_TIERS: frozenset = frozenset({"pro", "business", "enterprise"})

# Status yang dianggap "active subscription" — tier Pro+ cuma efektif kalau
# status aktif. Suspended/expired/cancelled = fail-closed walau tier masih pro.
ACTIVE_STATUSES: frozenset = frozenset({"trial", "active"})

# Outlet limit per tier. None = unlimited.
TIER_OUTLET_LIMITS: dict = {
    "starter": 1,
    "pro": 5,
    "business": 20,
    "enterprise": None,
}

# Cache TTL — cukup pendek supaya tier change cepet terasa tapi cukup panjang
# untuk cover ratusan request window login normal.
TENANT_CACHE_TTL_SEC = 30


# ─── Tenant snapshot (cache-friendly DTO) ─────────────────────────────────────
@dataclass
class TenantSnapshot:
    """
    Lightweight JSON-serializable representation of Tenant untuk Redis cache.
    Cuma field yang dibutuhkan di auth/tier check. Avoid ORM lifecycle issues
    (detached session dll).
    """
    id: str
    schema_name: str
    is_active: bool
    subscription_tier: str
    subscription_status: str
    row_version: int
    next_billing_date: Optional[str] = None  # ISO date string

    @classmethod
    def from_tenant(cls, tenant: Tenant) -> "TenantSnapshot":
        tier_raw = getattr(tenant, "subscription_tier", "starter") or "starter"
        tier_str = tier_raw.value if hasattr(tier_raw, "value") else str(tier_raw)
        status_raw = getattr(tenant, "subscription_status", "active") or "active"
        status_str = status_raw.value if hasattr(status_raw, "value") else str(status_raw)
        nbd = getattr(tenant, "next_billing_date", None)
        return cls(
            id=str(tenant.id),
            schema_name=str(tenant.schema_name),
            is_active=bool(tenant.is_active),
            subscription_tier=tier_str.lower(),
            subscription_status=status_str.lower(),
            row_version=int(tenant.row_version or 0),
            next_billing_date=nbd.isoformat() if nbd else None,
        )


# ─── Subscription state checks ────────────────────────────────────────────────
def get_tier_name(tenant_or_snapshot) -> str:
    """Extract normalized tier name (lowercase string) dari Tenant ORM atau Snapshot."""
    raw = getattr(tenant_or_snapshot, "subscription_tier", "starter") or "starter"
    v = raw.value if hasattr(raw, "value") else str(raw)
    return v.lower()


def get_status_name(tenant_or_snapshot) -> str:
    """Extract normalized status name."""
    raw = getattr(tenant_or_snapshot, "subscription_status", "active") or "active"
    v = raw.value if hasattr(raw, "value") else str(raw)
    return v.lower()


def is_pro_tier(tenant_or_snapshot) -> bool:
    return get_tier_name(tenant_or_snapshot) in PRO_TIERS


def is_subscription_active(tenant_or_snapshot) -> bool:
    """
    Full subscription health check — fail-closed untuk Pro features.
    - tenant.is_active = True (not suspended)
    - subscription_status in {trial, active} (bukan expired/cancelled/suspended)
    """
    if not getattr(tenant_or_snapshot, "is_active", False):
        return False
    return get_status_name(tenant_or_snapshot) in ACTIVE_STATUSES


def get_outlet_limit(tier_name: str) -> Optional[int]:
    """Return max outlets untuk tier. None = unlimited."""
    return TIER_OUTLET_LIMITS.get(tier_name.lower(), 1)


# ─── Redis cache ──────────────────────────────────────────────────────────────
def _cache_key(tenant_id: str) -> str:
    return f"tenant:snapshot:{tenant_id}"


async def get_cached_tenant_snapshot(redis_client, tenant_id: str) -> Optional[TenantSnapshot]:
    """Read snapshot dari cache. Return None on miss/error (log)."""
    try:
        raw = await redis_client.get(_cache_key(tenant_id))
    except Exception as e:
        logger.warning("tenant cache GET error (Redis down?) tenant=%s: %s", tenant_id, e)
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return TenantSnapshot(**data)
    except Exception as e:
        logger.warning("tenant cache DECODE error tenant=%s: %s", tenant_id, e)
        return None


async def cache_tenant_snapshot(redis_client, snapshot: TenantSnapshot) -> None:
    """Write snapshot to cache. Non-blocking — log error, jangan gagal request."""
    try:
        await redis_client.setex(
            _cache_key(snapshot.id),
            TENANT_CACHE_TTL_SEC,
            json.dumps(asdict(snapshot)),
        )
    except Exception as e:
        logger.warning("tenant cache SET error tenant=%s: %s", snapshot.id, e)


async def invalidate_tenant_cache(redis_client, tenant_id: str) -> None:
    """Invalidate cache setelah tenant write (tier change, status flip, etc)."""
    try:
        await redis_client.delete(_cache_key(str(tenant_id)))
        logger.info("tenant cache invalidated tenant=%s", tenant_id)
    except Exception as e:
        logger.warning(
            "tenant cache INVALIDATE failed tenant=%s (next read might be stale until TTL): %s",
            tenant_id, e,
        )


# ─── Downgrade cascade ────────────────────────────────────────────────────────
async def apply_tier_downgrade_cascade(
    db: AsyncSession,
    tenant: Tenant,
    old_tier: str,
    new_tier: str,
    user_id,
) -> dict:
    """
    Apply cascade effects saat tier DOWNGRADE.
    Dipanggil dari superadmin.update_tier + subscription_billing auto-downgrade.

    Cascade steps (order penting):
      1. Kalau new_tier == 'starter' dan old_tier = Pro+:
         - Reset outlet.stock_mode='simple' untuk SEMUA outlet tenant
           (cegah ghost stock_mode=recipe + ingredient endpoint 403)
         - HLC: bump outlet.row_version biar sync ke Flutter pick up
      2. Count existing outlets. Kalau > tier limit:
         - Log warning + include di report (admin UI surfaces)
         - TIDAK auto-deactivate (data preservation — user pilih manual)
         - Block CREATE outlet baru via limit check di outlets.py

    Return dict report — caller log/include di audit_log.
    Zero silent failure: setiap step log success atau error.
    """
    from backend.services.audit import log_audit

    report = {
        "tenant_id": str(tenant.id),
        "from_tier": old_tier,
        "to_tier": new_tier,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stock_mode_reset_count": 0,
        "outlet_count": 0,
        "outlet_limit": None,
        "outlets_over_limit": False,
        "errors": [],
    }

    # Step 1: Reset stock_mode kalau downgrade ke Starter
    if new_tier.lower() == "starter" and old_tier.lower() in PRO_TIERS:
        try:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                update(Outlet)
                .where(
                    Outlet.tenant_id == tenant.id,
                    Outlet.deleted_at.is_(None),
                    Outlet.stock_mode != "simple",
                )
                .values(
                    stock_mode="simple",
                    row_version=Outlet.row_version + 1,
                    updated_at=now,
                )
            )
            affected = result.rowcount or 0
            report["stock_mode_reset_count"] = affected
            if affected > 0:
                logger.info(
                    "downgrade cascade: reset stock_mode to 'simple' on %d outlet(s) tenant=%s",
                    affected, tenant.id,
                )
                await log_audit(
                    db=db,
                    action="DOWNGRADE_STOCK_MODE_RESET",
                    entity="outlets",
                    entity_id=tenant.id,
                    before_state={"stock_mode": "recipe"},
                    after_state={"stock_mode": "simple", "outlet_count": affected},
                    user_id=user_id,
                    tenant_id=tenant.id,
                )
        except Exception as e:
            err = f"stock_mode reset failed: {e}"
            report["errors"].append(err)
            logger.error(
                "downgrade cascade stock_mode reset FAILED tenant=%s: %s",
                tenant.id, e,
            )
            raise  # re-raise — caller handle rollback via db.rollback()

    # Step 2: Cek outlet count vs limit (tidak auto-deactivate, cuma flag)
    try:
        count_result = await db.execute(
            select(Outlet.id)
            .where(Outlet.tenant_id == tenant.id, Outlet.deleted_at.is_(None))
        )
        outlet_count = len(count_result.scalars().all())
        report["outlet_count"] = outlet_count
        limit = get_outlet_limit(new_tier)
        report["outlet_limit"] = limit

        if limit is not None and outlet_count > limit:
            report["outlets_over_limit"] = True
            logger.warning(
                "downgrade cascade: tenant=%s has %d outlet(s) but tier '%s' "
                "limit=%d. NOT auto-deactivating — preserve data. Admin should "
                "notify user to upgrade or manually deactivate.",
                tenant.id, outlet_count, new_tier, limit,
            )
            await log_audit(
                db=db,
                action="DOWNGRADE_OVER_LIMIT_WARNING",
                entity="tenants",
                entity_id=tenant.id,
                before_state={"outlet_count": outlet_count},
                after_state={"tier": new_tier, "limit": limit},
                user_id=user_id,
                tenant_id=tenant.id,
            )
    except Exception as e:
        err = f"outlet count check failed: {e}"
        report["errors"].append(err)
        logger.error("downgrade cascade outlet count FAILED tenant=%s: %s", tenant.id, e)
        # non-fatal — continue

    return report
