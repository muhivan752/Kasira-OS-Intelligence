"""Jabatan siap pakai buat toko baru: Kasir, Barista, Kepala toko.

Dibuat SEKALI per tenant, waktu pemilik pertama kali membuka halaman tim, dan
hanya kalau tenant belum punya jabatan dengan pengaturan izin. Penanda
`template` di JSONB permissions (sistem cuma membaca `access_policy`) mencegah
jabatan dibuat ulang walau nanti diganti nama. Pemilik bebas mengubahnya.
"""
from uuid import uuid4

from sqlalchemy import select, text

from backend.models import Role
from backend.schemas.account import SUPPORTED_ROLE_PERMISSIONS

_KASIR = {"hris.self", "pos.sell", "pos.shift.manage", "pos.cash.manage", "pos.refund", "stock.view", "customers.lookup"}
TEMPLATES = (
    ("Kasir", "kasir", _KASIR),
    ("Barista", "barista", {"hris.self", "pos.kitchen", "stock.view"}),
    ("Kepala toko", "kepala_toko", _KASIR | {
        "pos.refund.approve", "pos.discount.override", "pos.kitchen", "sales.detail.view",
        "stock.receive", "stock.adjust", "hris.employees.manage", "hris.schedules.manage",
        "hris.attendance.manage", "customers.view", "purchasing.view"}),
)
assert all(perms <= SUPPORTED_ROLE_PERMISSIONS for _, _, perms in TEMPLATES)


async def ensure_default_roles(db, user):
    """Commit sendiri kalau membuat jabatan; konteks RLS dipasang ulang sesudahnya."""
    if user.is_superuser is not True:
        return False
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"default_roles:{user.tenant_id}"})
    existing = (await db.scalars(select(Role.permissions).where(Role.tenant_id == user.tenant_id))).all()
    if any(isinstance(p, dict) and ("template" in p or "access_policy" in p) for p in existing):
        return False
    for name, key, perms in TEMPLATES:
        db.add(Role(id=uuid4(), tenant_id=user.tenant_id, name=name, scope="tenant", is_system=False, row_version=1,
            permissions={"access_policy": {"version": 1, "permissions": {p: True for p in sorted(perms)},
                "outlet_ids": [], "brand_ids": []}, "template": key}))
    await db.commit()
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), {"tenant": str(user.tenant_id)})
    return True
