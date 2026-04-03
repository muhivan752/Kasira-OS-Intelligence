"""
seed_admin.py — Buat akun admin Kasira untuk akses app + dashboard

Jalankan SEKALI setelah `alembic upgrade head`:
  python -m backend.scripts.seed_admin

Credentials yang dibuat:
  Phone  : 628111222333
  PIN    : 111222
  OTP dev: 123456  (master OTP, hanya berlaku di ENVIRONMENT != production)

Akses:
  Flutter App  → login dengan nomor 628111222333, OTP 123456, PIN 111222
  Next.js Dashboard → http://localhost:3000/login  (phone + OTP yang sama)
"""

import asyncio
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, text
from backend.core.database import AsyncSessionLocal
from backend.core.security import get_pin_hash
import backend.models  # noqa: F401 — register all models so FK chain resolves
from backend.models.tenant import Tenant
from backend.models.brand import Brand
from backend.models.outlet import Outlet
from backend.models.user import User

# ── Konfigurasi akun admin ────────────────────────────────────────────────────
ADMIN_PHONE       = "628111222333"
ADMIN_NAME        = "Admin Kasira"
ADMIN_PIN         = "111222"
BUSINESS_NAME     = "Kasira Coffee"
OUTLET_NAME       = "Kasira Coffee - Main"
OUTLET_SLUG       = "kasira-coffee"
OUTLET_ADDRESS    = "Jl. Sudirman No. 1, Jakarta"
# ─────────────────────────────────────────────────────────────────────────────


async def seed_admin() -> None:
    print("=" * 55)
    print("  Kasira — Buat Akun Admin")
    print("=" * 55)

    async with AsyncSessionLocal() as db:
        # Cek duplikat
        existing = (await db.execute(
            select(User).where(User.phone == ADMIN_PHONE, User.deleted_at == None)
        )).scalar_one_or_none()

        if existing:
            # Tampilkan info saja
            tenant_row = (await db.execute(
                select(Tenant).where(Tenant.id == existing.tenant_id)
            )).scalar_one_or_none()
            outlet_row = (await db.execute(
                select(Outlet).where(Outlet.tenant_id == existing.tenant_id, Outlet.deleted_at == None)
            )).scalar_one_or_none()

            print("\n⚠️  Admin sudah ada. Tidak ada perubahan.\n")
            _print_credentials(existing, tenant_row, outlet_row)
            return

        # ── Buat Tenant ───────────────────────────────────────────────────────
        tenant_id  = uuid.uuid4()
        schema_name = f"tenant_{str(tenant_id).replace('-', '')[:16]}"

        tenant = Tenant(
            id=tenant_id,
            name=BUSINESS_NAME,
            schema_name=schema_name,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()

        # ── Buat Brand ────────────────────────────────────────────────────────
        brand_id = uuid.uuid4()
        brand = Brand(
            id=brand_id,
            tenant_id=tenant_id,
            name=BUSINESS_NAME,
            type="cafe",
            is_active=True,
        )
        db.add(brand)

        # ── Buat Outlet ───────────────────────────────────────────────────────
        outlet_id = uuid.uuid4()
        outlet = Outlet(
            id=outlet_id,
            tenant_id=tenant_id,
            brand_id=brand_id,
            name=OUTLET_NAME,
            slug=OUTLET_SLUG,
            address=OUTLET_ADDRESS,
            is_active=True,
        )
        db.add(outlet)

        # ── Buat User ─────────────────────────────────────────────────────────
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            full_name=ADMIN_NAME,
            phone=ADMIN_PHONE,
            pin_hash=get_pin_hash(ADMIN_PIN),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        # ── Setup sequence display_number (kalau belum ada) ───────────────────
        await db.execute(text(
            "CREATE SEQUENCE IF NOT EXISTS order_display_seq START 1000 INCREMENT 1"
        ))

        await db.commit()
        print("\n✅ Akun admin berhasil dibuat!\n")
        _print_credentials(user, tenant, outlet)


def _print_credentials(user, tenant, outlet) -> None:
    tenant_id = str(tenant.id) if tenant else "-"
    outlet_id = str(outlet.id) if outlet else "-"

    print("┌─────────────────────────────────────────────┐")
    print("│           KREDENSIAL AKUN ADMIN              │")
    print("├─────────────────────────────────────────────┤")
    print(f"│  Phone   : {user.phone:<34} │")
    print(f"│  PIN     : {ADMIN_PIN:<34} │")
    print(f"│  OTP dev : 123456  (non-production only)    │")
    print("├─────────────────────────────────────────────┤")
    print(f"│  Tenant  : {tenant_id:<34} │")
    print(f"│  Outlet  : {outlet_id:<34} │")
    print("├─────────────────────────────────────────────┤")
    print("│  Login Flutter App:                          │")
    print(f"│    Nomor  → {user.phone:<33}│")
    print("│    OTP    → 123456  (dev) atau WA asli       │")
    print(f"│    PIN    → {ADMIN_PIN:<33}│")
    print("│                                              │")
    print("│  Login Next.js Dashboard:                    │")
    print("│    URL    → http://localhost:3000/login       │")
    print(f"│    Nomor  → {user.phone:<33}│")
    print("│    OTP    → 123456  (dev)                    │")
    print("└─────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    asyncio.run(seed_admin())
