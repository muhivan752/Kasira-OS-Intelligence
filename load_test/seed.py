"""
Load test seed — create isolated tenant + data untuk locust runs.
Run: sudo docker exec kasira-backend-1 python -m load_test.seed
Output: JSON ke stdout (JWT + tenant/outlet/product IDs) untuk consumption locust.
"""
import asyncio
import sys
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.models.tenant import Tenant


# Bypass RLS pakai superuser connection (app user gak bisa insert lintas-tenant).
# Load test seed = admin operation, safe untuk pakai superuser.
_SUPERUSER_URI = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
_engine = create_async_engine(_SUPERUSER_URI, echo=False)
AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
from backend.models.brand import Brand
from backend.models.outlet import Outlet
from backend.models.user import User
from backend.models.role import Role
from backend.models.category import Category
from backend.models.product import Product
from backend.models.shift import Shift
from backend.core.security import create_access_token

LOADTEST_PHONE = "6289999990001"
LOADTEST_TENANT_NAME = "_loadtest_tenant"


async def seed():
    async with AsyncSessionLocal() as db:
        # 1. Tenant (Pro tier biar akses full API)
        tenant = (await db.execute(
            select(Tenant).where(Tenant.name == LOADTEST_TENANT_NAME)
        )).scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
                name=LOADTEST_TENANT_NAME,
                schema_name="loadtest",
                is_active=True,
                subscription_tier="pro",
                subscription_status="active",
                billing_interval="monthly",
                billing_day=1,
                owner_email="loadtest@kasira.internal",
                is_demo=True,
            )
            db.add(tenant)
            await db.flush()
            print(f"[seed] created tenant {tenant.id}", file=sys.stderr)

        # 2. Role — owner, full permissions
        role = (await db.execute(
            select(Role).where(Role.tenant_id == tenant.id, Role.name == "Owner")
        )).scalar_one_or_none()
        if not role:
            role = Role(
                tenant_id=tenant.id,
                name="Owner",
                scope="tenant",
                permissions={"all": True},
                is_system=True,
                can_view_hpp=True,
                can_view_revenue_detail=True,
                can_view_supplier_price=True,
                can_approve_hpp_update=True,
                can_scan_invoice=True,
                can_refund=True,
                can_approve_refund=True,
                can_discount_override=True,
            )
            db.add(role)
            await db.flush()

        # 3. Brand
        brand = (await db.execute(
            select(Brand).where(Brand.tenant_id == tenant.id, Brand.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not brand:
            brand = Brand(
                tenant_id=tenant.id,
                name="LoadTest Brand",
                type="cafe",
                is_active=True,
            )
            db.add(brand)
            await db.flush()

        # 4. Outlet (simple stock mode — lebih cepat, gak butuh recipe)
        outlet = (await db.execute(
            select(Outlet).where(Outlet.brand_id == brand.id, Outlet.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not outlet:
            outlet = Outlet(
                tenant_id=tenant.id,
                brand_id=brand.id,
                name="LoadTest Outlet",
                slug="loadtest-outlet",
                phone=LOADTEST_PHONE,
                stock_mode="simple",
                is_active=True,
                is_open=True,
            )
            db.add(outlet)
            await db.flush()

        # 5. Users (20 buah — biar rate limit per-user gak spread ke IP)
        users = []
        for i in range(20):
            phone = f"6289999990{i:03d}"
            existing = (await db.execute(
                select(User).where(User.phone == phone, User.deleted_at.is_(None))
            )).scalar_one_or_none()
            if existing:
                users.append(existing)
                continue
            u = User(
                tenant_id=tenant.id,
                phone=phone,
                full_name=f"LoadTest User {i+1}",
                role_id=role.id,
                is_active=True,
                is_superuser=False,
            )
            db.add(u)
            await db.flush()
            users.append(u)
        user = users[0]  # primary user buat shift owner

        # 6. Category
        category = (await db.execute(
            select(Category).where(Category.brand_id == brand.id, Category.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not category:
            category = Category(
                brand_id=brand.id,
                name="Menu Utama",
                is_active=True,
            )
            db.add(category)
            await db.flush()

        # 7. Products (50 buah, stock tinggi biar gak habis)
        existing_products = (await db.execute(
            select(Product).where(Product.brand_id == brand.id, Product.deleted_at.is_(None))
        )).scalars().all()

        if len(existing_products) < 50:
            for i in range(len(existing_products), 50):
                p = Product(
                    brand_id=brand.id,
                    category_id=category.id,
                    name=f"LoadTest Produk {i+1}",
                    base_price=15000 + (i * 1000),
                    stock_enabled=True,
                    stock_qty=999999,
                    stock_low_threshold=10,
                    is_active=True,
                    sku=f"LT-{i+1:03d}",
                )
                db.add(p)
            await db.flush()
            print(f"[seed] created {50 - len(existing_products)} products", file=sys.stderr)

        # 8. Open shift untuk SEMUA 20 users (payment endpoint check per-user)
        shifts = []
        for u in users:
            s = (await db.execute(
                select(Shift).where(
                    Shift.outlet_id == outlet.id,
                    Shift.user_id == u.id,
                    Shift.status == "open",
                    Shift.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if not s:
                s = Shift(
                    outlet_id=outlet.id,
                    user_id=u.id,
                    status="open",
                    starting_cash=100000,
                    start_time=datetime.now(timezone.utc),
                )
                db.add(s)
                await db.flush()
            shifts.append(s)
        shift = shifts[0]

        await db.commit()

        # 9. Mint JWT untuk SEMUA 20 user
        jwts = [
            create_access_token(subject=str(u.id), expires_delta=timedelta(days=1))
            for u in users
        ]
        token = jwts[0]

        # 10. Load products buat locust sampling
        all_products = (await db.execute(
            select(Product.id, Product.name, Product.base_price)
            .where(Product.brand_id == brand.id, Product.deleted_at.is_(None))
            .limit(50)
        )).all()

        out = {
            "jwt": token,  # primary (backward compat)
            "jwts": jwts,  # 20 tokens untuk distribute load per-user
            "tenant_id": str(tenant.id),
            "brand_id": str(brand.id),
            "outlet_id": str(outlet.id),
            "user_id": str(user.id),
            "user_ids": [str(u.id) for u in users],
            # user_id → shift_id mapping (payment endpoint butuh shift per-user)
            "user_shifts": {str(u.id): str(s.id) for u, s in zip(users, shifts)},
            "shift_id": str(shift.id),  # backward compat
            "product_ids": [str(p.id) for p in all_products],
            "product_prices": {str(p.id): float(p.base_price) for p in all_products},
        }
        print(json.dumps(out))


if __name__ == "__main__":
    asyncio.run(seed())
