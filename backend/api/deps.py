from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core import security
from backend.core.config import settings
from backend.core.database import get_db, tenant_context
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.schemas.token import TokenPayload
from backend.services.redis import get_redis_client
from sqlalchemy import text

security_bearer = HTTPBearer()

async def get_current_user(
    db: AsyncSession = Depends(get_db), 
    token: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> User:
    try:
        payload = jwt.decode(
            token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token tidak valid",
        )
    
    # Cek blacklist (logout) di Redis
    redis = await get_redis_client()
    if await redis.get(f"blacklist:{token_data.sub}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token telah di-revoke. Silakan login ulang.",
        )

    stmt = select(User).where(User.id == token_data.sub, User.deleted_at == None)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Akun tidak aktif")

    # Activate RLS for this session — scope all queries to user's tenant
    await db.execute(text(f"SET LOCAL app.current_tenant_id = '{user.tenant_id}'"))

    # Cek apakah tenant masih aktif (skip untuk platform admin)
    allowed_phones = [p.strip() for p in settings.SUPERADMIN_PHONES.split(",") if p.strip()]
    if user.phone not in allowed_phones:
        tenant_stmt = select(Tenant).where(Tenant.id == user.tenant_id, Tenant.deleted_at == None)
        tenant_result = await db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()
        if tenant and not tenant.is_active:
            raise HTTPException(
                status_code=403,
                detail="Langganan bisnis Anda telah dihentikan. Hubungi admin untuk informasi lebih lanjut.",
            )

    return user

async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Resolve tenant dari X-Tenant-ID header.
    Efficient: try Redis cache first (30s TTL), fallback DB. Cache di-invalidate
    otomatis oleh tenant writes (update_tier, update_status, grace period).
    RLS `SET LOCAL` tetap eksekusi per request — tidak di-cache (per-TX state).
    """
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id or tenant_id == "public":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header X-Tenant-ID wajib diisi"
        )

    from backend.services.subscription import (
        get_cached_tenant_snapshot,
        cache_tenant_snapshot,
        TenantSnapshot,
    )
    from uuid import UUID as UUID_type
    from sqlalchemy import or_

    # Fast path: UUID cache lookup
    tenant: Optional[Tenant] = None
    try:
        tid = UUID_type(tenant_id)
        # Try Redis cache first
        redis = await get_redis_client()
        snapshot = await get_cached_tenant_snapshot(redis, str(tid))
        if snapshot is not None:
            if not snapshot.is_active:
                raise HTTPException(status_code=400, detail="Tenant tidak aktif")
            # Activate RLS (always per-request — not cached)
            await db.execute(text(f"SET LOCAL app.current_tenant_id = '{snapshot.id}'"))
            # Fetch real Tenant ORM object (lightweight — PK lookup) untuk backward
            # compat dgn caller yang butuh ORM relationships. Cache saved the
            # check-and-authz roundtrip, ORM fetch tetep berlaku.
            tenant = (await db.execute(
                select(Tenant).where(Tenant.id == tid, Tenant.deleted_at == None)
            )).scalar_one_or_none()
            if tenant:
                return tenant
            # Cache was stale (tenant deleted) — fall through to DB path

        # Cache miss — DB lookup
        stmt = select(Tenant).where(Tenant.id == tid, Tenant.deleted_at == None)
    except (ValueError, AttributeError):
        # Non-UUID — fallback schema_name/name (rare legacy path, no cache)
        stmt = select(Tenant).where(
            or_(Tenant.schema_name == tenant_id, Tenant.name == tenant_id),
            Tenant.deleted_at == None,
        )
        redis = None

    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")
    if not tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant tidak aktif")

    # Populate cache post-fetch (fire-and-forget — errors logged but non-blocking)
    if redis is not None:
        await cache_tenant_snapshot(redis, TenantSnapshot.from_tenant(tenant))

    # Activate RLS for this session
    await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant.id}'"))
    return tenant

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="Akses ditolak"
        )
    return current_user

async def validate_brand_ownership(db: AsyncSession, brand_id, tenant_id) -> None:
    """Pastikan brand_id milik tenant user. Raise 403 kalau bukan."""
    from backend.models.brand import Brand
    from uuid import UUID as UUID_type
    stmt = select(Brand).where(
        Brand.id == (brand_id if isinstance(brand_id, UUID_type) else UUID_type(str(brand_id))),
        Brand.tenant_id == tenant_id,
        Brand.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Akses ditolak: brand bukan milik tenant Anda")


async def validate_product_ownership(db: AsyncSession, product_id, tenant_id):
    """Fetch product dan validasi tenant ownership via brand. Return product atau raise."""
    from backend.models.product import Product
    from backend.models.brand import Brand
    stmt = (
        select(Product)
        .join(Brand, Product.brand_id == Brand.id)
        .where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
            Brand.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return product


async def validate_category_ownership(db: AsyncSession, category_id, tenant_id):
    """Fetch category dan validasi tenant ownership via brand. Return category atau raise."""
    from backend.models.category import Category
    from backend.models.brand import Brand
    stmt = (
        select(Category)
        .join(Brand, Category.brand_id == Brand.id)
        .where(
            Category.id == category_id,
            Category.deleted_at.is_(None),
            Brand.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    return category


async def get_platform_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Platform-level superadmin check via SUPERADMIN_PHONES env var."""
    allowed = [p.strip() for p in settings.SUPERADMIN_PHONES.split(",") if p.strip()]
    if not allowed or current_user.phone not in allowed:
        raise HTTPException(status_code=403, detail="Akses platform admin ditolak")
    # Superadmin bypasses RLS — can see all tenants
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
    return current_user


# Re-export untuk backward compat — single source of truth di
# services/subscription.py (PRO_TIERS = frozenset).
from backend.services.subscription import PRO_TIERS  # noqa: E402

async def require_pro_tier(
    tenant: Tenant = Depends(get_current_tenant),
) -> Tenant:
    """
    Blokir fitur Pro+ untuk tenant yang:
      1. Tier = starter (upgrade-needed), atau
      2. Subscription tidak aktif (suspended/expired/cancelled) walau tier = pro+.
         Fix CRITICAL #15 — dulu cuma check enum tier, lolos untuk tenant
         expired yang masih bertier "pro".

    Setiap reject di-log untuk observability (alert di grep/Sentry).
    """
    from backend.services.subscription import (
        get_tier_name, get_status_name, is_pro_tier, is_subscription_active,
    )
    import logging
    logger_tier = logging.getLogger("backend.api.deps.tier")

    tier = get_tier_name(tenant)
    status_name = get_status_name(tenant)

    if not is_pro_tier(tenant):
        logger_tier.info(
            "tier gate reject: tenant=%s reason=insufficient_tier tier=%s",
            tenant.id, tier,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_TIER",
                "message": "Fitur ini hanya tersedia untuk paket Pro. Upgrade untuk mengakses.",
                "current_tier": tier,
            },
        )

    if not is_subscription_active(tenant):
        logger_tier.warning(
            "tier gate reject: tenant=%s reason=subscription_inactive "
            "tier=%s status=%s is_active=%s",
            tenant.id, tier, status_name, tenant.is_active,
        )
        raise HTTPException(
            status_code=402,  # Payment Required — semantic for subscription issue
            detail={
                "code": "SUBSCRIPTION_INACTIVE",
                "message": (
                    "Langganan Pro Anda tidak aktif (suspended/expired). "
                    "Bayar invoice terakhir atau hubungi admin untuk re-aktivasi."
                ),
                "status": status_name,
            },
        )

    return tenant
