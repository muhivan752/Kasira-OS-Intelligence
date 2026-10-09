from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from backend.models import Brand, HrEmployee, LoginSession, Outlet, Role, Tenant, User
from backend.schemas.access import AccessPolicy
from backend.services import accounts
from backend.services.access import resolve_access


def role_allowed(role, context, outlet_id=None):
    try:
        policy = AccessPolicy.model_validate((role.permissions or {}).get("access_policy"))
    except (ValidationError, TypeError, AttributeError):
        return False
    permissions = {p for p, granted in policy.permissions.items() if granted}
    if role.deleted_at or role.is_system or policy.brand_ids or role.scope not in {"outlet", "tenant"}:
        return False
    if "access.manage" in permissions or not permissions <= context.permissions:
        return False
    if role.scope == "tenant":
        return not policy.outlet_ids and context.scope == "tenant"
    return bool(policy.outlet_ids) and set(policy.outlet_ids) <= context.outlet_ids and (
        outlet_id is None or outlet_id in policy.outlet_ids)


async def fresh_actor(db, request, user):
    # Share the account-admin lock order: tenant, actor, role, profile, session.
    await accounts.lock(db, f"tenant:{user.tenant_id}")
    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id)
        .with_for_update().execution_options(populate_existing=True))
    actor = await db.scalar(select(User).where(User.id == user.id, User.tenant_id == user.tenant_id)
        .with_for_update().execution_options(populate_existing=True))
    if not actor or actor.deleted_at or not actor.is_active or not tenant or tenant.deleted_at or not tenant.is_active:
        raise HTTPException(403, "Akun atau bisnis tidak aktif")
    if actor.role_id:
        await db.scalar(select(Role).where(Role.id == actor.role_id, Role.tenant_id == actor.tenant_id)
            .with_for_update().execution_options(populate_existing=True))
    await db.scalar(select(HrEmployee).where(HrEmployee.user_id == actor.id,
        HrEmployee.tenant_id == actor.tenant_id, HrEmployee.deleted_at.is_(None))
        .with_for_update().execution_options(populate_existing=True))
    claims = request.state.auth_claims
    if claims.get("sid"):
        await db.scalar(select(LoginSession).where(LoginSession.id == UUID(claims["sid"]),
            LoginSession.user_id == actor.id).with_for_update().execution_options(populate_existing=True))
    context = await resolve_access(db, actor)
    context.require("hris.employees.manage")
    context.require("hris.accounts.manage")
    if not actor.is_superuser and context.mode != "managed":
        raise HTTPException(403, "Pemilik perlu memberikan izin akun melalui jabatan dengan pengaturan akses")
    await check_session(db, request, actor)
    await db.scalars(select(Outlet).where(Outlet.id.in_(context.outlet_ids), Outlet.tenant_id == actor.tenant_id)
        .order_by(Outlet.id).with_for_update())
    await db.scalars(select(Brand).where(Brand.tenant_id == actor.tenant_id,
        Brand.id.in_([o.brand_id for o in context.outlets])).order_by(Brand.id).with_for_update())
    context = await resolve_access(db, actor)
    context.require("hris.accounts.manage")
    return context, tenant


async def check_session(db, request, actor):
    claims, token = request.state.auth_claims, request.state.auth_token
    if claims.get("exp", 0) <= accounts.now().timestamp():
        raise HTTPException(401, "Sesi berakhir. Masuk kembali.")
    redis = await accounts.get_redis_client()
    if await redis.get(f"revoked-token:{accounts.digest(token)}") or (
        not claims.get("sid") and await redis.get(f"blacklist:{actor.id}")):
        raise HTTPException(401, "Sesi berakhir. Masuk kembali.")
    await accounts.validate_session(db, actor, claims, token)


async def target(db, user, context, user_id, outlet_id=None):
    account = await db.scalar(select(User).where(User.id == user_id, User.tenant_id == user.tenant_id,
        User.deleted_at.is_(None)).with_for_update().execution_options(populate_existing=True))
    if not account:
        raise HTTPException(404, "Akun karyawan tidak ditemukan")
    if account.is_superuser or (context.mode != "owner" and account.id == user.id):
        raise HTTPException(403, "Akun ini tidak dapat diatur melalui profil karyawan")
    if context.mode != "owner":
        role = await db.scalar(select(Role).where(Role.id == account.role_id, Role.tenant_id == user.tenant_id)
            .with_for_update().execution_options(populate_existing=True))
        if not role or not role_allowed(role, context, outlet_id):
            raise HTTPException(403, "Hak akses akun ini di luar izin pengelola")
        linked = await db.scalar(select(HrEmployee).where(HrEmployee.user_id == account.id,
            HrEmployee.tenant_id == user.tenant_id, HrEmployee.deleted_at.is_(None)))
        if linked:
            context.require_outlet(linked.outlet_id)
    return account


async def configure(db, request, user, context, tenant, employee, body):
    # Username toko tidak lagi syarat (9 Okt 2026): karyawan masuk dengan nomor
    # HP/username + password, server mencari tokonya (accounts.login_candidates).
    context.require_outlet(employee.outlet_id)
    if not employee.is_active:
        raise HTTPException(409, "Aktifkan profil sebelum membuat atau mengatur akun")
    username = employee.phone if body.use_phone else body.username
    if not username:
        raise HTTPException(422, "Isi nomor HP untuk login karyawan")
    account = await target(db, user, context, employee.user_id, employee.outlet_id) if employee.user_id else None
    if account and body.user_row_version != account.row_version:
        raise HTTPException(409, "Akun sudah berubah. Muat ulang sebelum mengatur login.")
    role = None
    if body.role_id:
        role = await db.scalar(select(Role).where(Role.id == body.role_id, Role.tenant_id == user.tenant_id)
            .with_for_update().execution_options(populate_existing=True))
        if not role or not role_allowed(role, context, employee.outlet_id):
            raise HTTPException(403, "Pilih hak akses yang sesuai izin dan outlet pengelola")
    elif not account:
        context.require("hris.self")
        role_id = uuid5(NAMESPACE_URL, f"selaris:staff-self:{user.tenant_id}:{employee.outlet_id}")
        role = await db.scalar(select(Role).where(Role.id == role_id, Role.tenant_id == user.tenant_id).with_for_update())
        if not role:
            outlet_name = next(o.name for o in context.outlets if o.id == employee.outlet_id)
            role = Role(id=role_id, tenant_id=user.tenant_id, name=f"Absensi pribadi · {outlet_name}",
                scope="outlet", is_system=False, row_version=1,
                permissions={"access_policy": {"version": 1, "permissions": {"hris.self": True},
                    "outlet_ids": [str(employee.outlet_id)], "brand_ids": []}})
            db.add(role)
        try:
            policy = AccessPolicy.model_validate((role.permissions or {}).get("access_policy"))
        except (ValidationError, TypeError, AttributeError):
            raise HTTPException(409, "Hak akses absensi pribadi sudah berubah. Pilih jabatan yang sesuai.") from None
        if not role_allowed(role, context, employee.outlet_id) or role.scope != "outlet" or (
            {p for p, granted in policy.permissions.items() if granted} != {"hris.self"}) or (
            policy.outlet_ids != [employee.outlet_id]):
            raise HTTPException(409, "Hak akses absensi pribadi sudah berubah. Pilih jabatan yang sesuai.")
    await accounts.require_available_username(db, user.tenant_id, username, account.id if account else None)
    if not account:
        if not body.password:
            raise HTTPException(422, "Isi password awal untuk akun baru")
        account = User(id=uuid4(), tenant_id=user.tenant_id, full_name=employee.name,
            login_username=username, phone=None, role_id=role.id, is_active=True,
            is_superuser=False, credential_version=0, row_version=1)
        db.add(account)
        await db.flush()
        employee.user_id = account.id
    account.login_username = username
    if role:
        account.role_id = role.id
    account.is_active = True
    if not account.password_hash and not body.password:
        raise HTTPException(422, "Isi password awal untuk mengaktifkan login akun ini")
    if body.password:
        await accounts.set_password(db, account, body.password)
    else:
        await accounts.revoke_all(db, account)
    await check_session(db, request, user)
    return {"account_configured": True, "account_username": username, "account_id": str(account.id)}


async def options(db, user, context):
    admin = context.allows("hris.accounts.manage") and context.allows("hris.employees.manage") and (
        context.mode in {"owner", "managed"})
    roles = (await db.scalars(select(Role).where(Role.tenant_id == user.tenant_id,
        Role.deleted_at.is_(None)).order_by(Role.name, Role.id))).all() if admin else []
    permitted = {r.id: r for r in roles if role_allowed(r, context)}
    accounts_list = (await db.scalars(select(User).where(User.tenant_id == user.tenant_id,
        User.deleted_at.is_(None), User.is_superuser.is_(False)).order_by(User.full_name, User.id))).all() if (
        admin or context.allows("hris.employees.manage") and context.mode != "managed") else []
    profiles = (await db.scalars(select(HrEmployee).where(HrEmployee.tenant_id == user.tenant_id,
        HrEmployee.user_id.is_not(None), HrEmployee.deleted_at.is_(None)))).all() if admin else []
    linked = {p.user_id: p for p in profiles}
    if context.mode == "managed":
        accounts_list = [a for a in accounts_list if a.id != user.id and a.role_id in permitted and (
            a.id not in linked or linked[a.id].outlet_id in context.outlet_ids)]
    tenant = await db.get(Tenant, user.tenant_id)
    return {"account_admin": admin, "shop_username": tenant.login_username if admin else None,
        "business_name": tenant.name if admin else None,
        "roles": [{"id": str(r.id), "name": r.name, "outlet_ids": (r.permissions["access_policy"].get("outlet_ids") or []),
            "scope": r.scope} for r in permitted.values()],
        "accounts": [{"id": str(a.id), "name": a.full_name, "username": a.login_username,
            "row_version": a.row_version, "role_id": str(a.role_id) if a.role_id else None,
            "password_enabled": bool(a.password_hash), "employee_id": str(linked[a.id].id) if a.id in linked else None}
            for a in accounts_list]}
