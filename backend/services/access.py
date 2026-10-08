import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from backend.models import Brand, HrEmployee, Outlet, Role
from backend.schemas.access import AccessPolicy, HRIS_MANAGE, PERMISSIONS


LEGACY_BASE = frozenset({"pos.sell", "stock.view", "customers.lookup", "hris.self"})
LEGACY_FLAGS = {
    "can_view_hpp": "hpp.view", "can_view_revenue_detail": "sales.detail.view",
    "can_view_supplier_price": "supplier.price.view", "can_approve_hpp_update": "hpp.approve",
    "can_refund": "pos.refund", "can_approve_refund": "pos.refund.approve",
    "can_discount_override": "pos.discount.override",
}
ENFORCED_MODULES = ("hris", "pos", "stock", "sync", "finance", "purchasing", "customers", "hpp", "ai")


def denied(code, message):
    raise HTTPException(403, detail={"code": code, "message": message})


@dataclass(frozen=True)
class AccessContext:
    user_id: UUID
    tenant_id: UUID
    permissions: frozenset[str]
    outlets: tuple[Outlet, ...]
    employee: HrEmployee | None
    mode: str
    version: str
    scope: str = "tenant"

    @property
    def outlet_ids(self):
        return frozenset(o.id for o in self.outlets)

    def allows(self, permission):
        return permission in PERMISSIONS and permission in self.permissions

    def require(self, permission):
        if not self.allows(permission):
            denied("PERMISSION_DENIED", "Akses ini belum diberikan oleh pemilik usaha")

    def require_outlet(self, outlet_id):
        if outlet_id not in self.outlet_ids:
            raise HTTPException(404, "Outlet aktif tidak ditemukan dalam akses akun ini")

    def public(self):
        return {
            "user_id": str(self.user_id), "tenant_id": str(self.tenant_id),
            "permissions": sorted(self.permissions), "enforcement_mode": self.mode,
            "enforced_modules": list(ENFORCED_MODULES), "access_version": self.version,
            "outlets": [{"id": str(o.id), "name": o.name, "timezone": o.timezone} for o in self.outlets],
            "employee_id": str(self.employee.id) if self.employee else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "offline_pos_allowed": self.mode != "managed",
            "scope": self.scope,
        }


def role_permissions(user, role):
    if user.is_superuser is True:
        return PERMISSIONS, "owner", None
    if user.role_id and role is None:
        denied("ROLE_UNAVAILABLE", "Jabatan akun tidak tersedia. Hubungi pemilik usaha")
    raw = role.permissions if role else None
    if raw is not None and not isinstance(raw, dict):
        denied("ACCESS_POLICY_INVALID", "Pengaturan akses perlu diperbaiki oleh pemilik usaha")
    raw = raw or {}
    if "access_policy" in raw:
        try:
            policy = AccessPolicy.model_validate(raw["access_policy"])
        except ValidationError:
            denied("ACCESS_POLICY_INVALID", "Pengaturan akses perlu diperbaiki oleh pemilik usaha")
        return frozenset(k for k, v in policy.permissions.items() if v is True), "managed", policy
    permissions = set(LEGACY_BASE)
    if raw.get("hris_manage") is True:
        permissions.update(HRIS_MANAGE)
    if role:
        permissions.update(permission for flag, permission in LEGACY_FLAGS.items() if getattr(role, flag, False) is True)
    # Canonical keys can remove legacy grants; truthy strings never grant access.
    for permission in PERMISSIONS:
        if raw.get(permission) is True:
            permissions.add(permission)
        elif raw.get(permission) is False:
            permissions.discard(permission)
    return frozenset(permissions), "legacy", None


async def resolve_access(db, user):
    if user.deleted_at is not None or user.is_active is not True:
        denied("ACCOUNT_INACTIVE", "Akun tidak aktif. Hubungi pemilik usaha")
    role = None
    if user.role_id:
        role = await db.scalar(select(Role).where(Role.id == user.role_id, Role.tenant_id == user.tenant_id,
            Role.deleted_at.is_(None)).execution_options(populate_existing=True))
    employee = await db.scalar(select(HrEmployee).where(HrEmployee.tenant_id == user.tenant_id,
        HrEmployee.user_id == user.id, HrEmployee.deleted_at.is_(None)).execution_options(populate_existing=True))
    if employee and not employee.is_active and not user.is_superuser:
        denied("EMPLOYEE_INACTIVE", "Status karyawan tidak aktif. Hubungi pengelola tim")
    permissions, mode, policy = role_permissions(user, role)
    query = select(Outlet).where(Outlet.tenant_id == user.tenant_id, Outlet.deleted_at.is_(None),
        Outlet.is_active.is_(True)).order_by(Outlet.created_at, Outlet.id)
    if policy:
        query = query.join(Brand, Brand.id == Outlet.brand_id).where(
            Brand.tenant_id == user.tenant_id, Brand.deleted_at.is_(None), Brand.is_active.is_(True))
        if role.scope == "outlet":
            if policy.brand_ids:
                denied("ACCESS_POLICY_INVALID", "Pengaturan akses outlet tidak sesuai")
            query = query.where(Outlet.id.in_(policy.outlet_ids))
        elif role.scope == "brand":
            if policy.outlet_ids:
                denied("ACCESS_POLICY_INVALID", "Pengaturan akses brand tidak sesuai")
            query = query.where(Outlet.brand_id.in_(policy.brand_ids),
                Brand.tenant_id == user.tenant_id, Brand.deleted_at.is_(None), Brand.is_active.is_(True))
        elif role.scope != "tenant" or policy.outlet_ids or policy.brand_ids:
            denied("ACCESS_POLICY_INVALID", "Pengaturan cakupan akses tidak sesuai")
    outlets = tuple((await db.scalars(query.execution_options(populate_existing=True))).all())
    snapshot = {
        "user": str(user.id), "tenant": str(user.tenant_id), "user_version": user.row_version,
        "role": str(user.role_id), "role_scope": role.scope if role else None,
        "permissions": sorted(permissions), "mode": mode,
        "policy": policy.model_dump(mode="json") if policy else None,
        "employee": [str(employee.id), employee.row_version, str(employee.outlet_id)] if employee else None,
        "outlets": [[str(o.id), o.row_version] for o in outlets],
    }
    version = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return AccessContext(user.id, user.tenant_id, permissions, outlets, employee, mode, version,
                         role.scope if policy else "tenant")


def validate_tenant_header(request, tenant_id):
    supplied = request.headers.get("X-Tenant-ID")
    if supplied is None:
        return
    try:
        matches = UUID(supplied) == tenant_id
    except ValueError:
        matches = False
    if not matches:
        denied("TENANT_MISMATCH", "Pilihan bisnis tidak sesuai dengan akun yang masuk")


# Staf legacy (akun lama tanpa access_policy) tetap boleh semua jalur APK kasir,
# termasuk offline. Yang ditutup hanya pekerjaan pemilik: pengaturan outlet dan
# pembayaran, katalog, CRM, laporan bisnis, langganan. Daftar ini sengaja
# daftar-tolak, bukan daftar-izin: APK legacy memanggil puluhan endpoint kasir.
LEGACY_OWNER_MODULES = frozenset({"crm", "billing", "analytics", "knowledge_graph", "referrals"})
LEGACY_OWNER_ENDPOINTS = {
    "outlets": {"create_outlet", "update_outlet", "setup_payment", "setup_payment_own_key", "remove_payment_own_key",
                "setup_whatsapp", "get_payment_status", "update_stock_mode", "update_tax_config", "update_outlet_location"},
    # update_product sengaja tidak di sini: kasir boleh menandai habis (lihat products.update_product).
    "products": {"create_product", "delete_product", "set_product_variants"},
    "categories": {"create_category", "update_category", "delete_category"},
    "tables": {"create_table", "update_table", "delete_table"},
    "couriers": {"create_courier", "update_courier", "delete_courier"},
    "reservations": {"update_reservation_settings"},
    "customers": {"crm_list", "customer_detail", "refresh_stats"},
    "embeddings": {"generate_all_embeddings"},
    "ai": {"apply_recipe_proposal", "apply_menu_batch", "classify_domain"},
    "tenants": {"create_tenant"},
}
LEGACY_GRANTED_ENDPOINTS = {("reports", "get_report_summary"): ("sales.detail.view",)}


def enforce_legacy_staff(request, context):
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return
    key = (request.method, endpoint)
    # Modul yang sudah punya izin (keuangan, pembelian, HPP, AI) memakai izin yang
    # sama dengan akun managed, termasuk izin lama dari flag jabatan.
    from backend.services.ai_access import route_rules as ai_rules
    from backend.services.business_access import route_rules as business_rules
    grants = ai_rules().get(key)
    if grants is not None:
        for permission in grants:
            context.require(permission)
        return
    grants = business_rules().get(key)
    if grants is not None:
        if not any(context.allows(p) for p in grants):
            denied("PERMISSION_DENIED", "Akses ini belum diberikan oleh pemilik usaha")
        return
    module, name = getattr(endpoint, "__module__", "").rsplit(".", 1)[-1], getattr(endpoint, "__name__", "")
    if module in LEGACY_OWNER_MODULES or name in LEGACY_OWNER_ENDPOINTS.get(module, ()):
        denied("OWNER_ONLY", "Fitur ini khusus pemilik usaha")
    grants = LEGACY_GRANTED_ENDPOINTS.get((module, name))
    if grants and not any(context.allows(p) for p in grants):
        denied("PERMISSION_DENIED", "Akses ini belum diberikan oleh pemilik usaha")


def enforce_route(request, context):
    if context.mode == "legacy":
        return enforce_legacy_staff(request, context)
    if context.mode != "managed":
        return
    from backend.api.routes import auth, hris, users, accounts
    allowed = {
        ("GET", auth.get_me), ("GET", auth.get_access), ("GET", users.read_user_me),
        ("DELETE", auth.logout), ("POST", auth.set_pin), ("POST", auth.login_with_pin),
        ("GET", hris.setup), ("GET", hris.workspace), ("GET", hris.choices), ("GET", hris.request_status),
        ("POST", hris.create_employee), ("PUT", hris.edit_employee),
        ("POST", hris.create_schedule), ("PUT", hris.edit_schedule), ("POST", hris.cancel_schedule),
        ("POST", hris.create_attendance), ("PUT", hris.edit_attendance), ("POST", hris.void_attendance),
        ("POST", hris.punch),
        ("GET", accounts.account_info), ("GET", accounts.sessions), ("POST", accounts.revoke_sessions),
    }
    # FastAPI has resolved endpoint identity before dependencies, even without scope['route'].
    from backend.services.pos_access import supported_route
    from backend.services.business_access import supported_route as business_route
    from backend.services.ai_access import supported_route as ai_route
    if (request.method, request.scope.get("endpoint")) not in allowed and not supported_route(request) and not business_route(request) and not ai_route(request):
        denied("ACCESS_ROUTE_NOT_READY", "Fitur ini belum tersedia untuk akun dengan pengaturan akses baru")
