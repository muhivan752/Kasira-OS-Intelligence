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
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id or tenant_id == "public":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header X-Tenant-ID wajib diisi"
        )
        
    # Try UUID first (frontend sends tenant UUID), fallback to schema_name
    from sqlalchemy import or_
    try:
        from uuid import UUID as UUID_type
        tid = UUID_type(tenant_id)
        stmt = select(Tenant).where(Tenant.id == tid, Tenant.deleted_at == None)
    except (ValueError, AttributeError):
        stmt = select(Tenant).where(
            or_(Tenant.schema_name == tenant_id, Tenant.name == tenant_id),
            Tenant.deleted_at == None,
        )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")
    if not tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant tidak aktif")

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


PRO_TIERS = {"pro", "business", "enterprise"}

async def require_pro_tier(
    tenant: Tenant = Depends(get_current_tenant),
) -> Tenant:
    """Blokir akses fitur Pro+ untuk tenant Starter."""
    raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter"
    tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)
    if tier.lower() not in PRO_TIERS:
        raise HTTPException(
            status_code=403,
            detail="Fitur ini hanya tersedia untuk paket Pro. Upgrade untuk mengakses."
        )
    return tenant
