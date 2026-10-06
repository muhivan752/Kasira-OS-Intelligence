from datetime import date, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from backend.api.deps import get_current_user
from backend.core.database import get_db
from backend.core.config import settings
from backend.models import AccountChallenge, Brand, Category, HrEmployee, LoginSession, Outlet, Role, Tenant, User
from backend.schemas.account import AccountRequest, ConsumeChallenge, EmployeeAccountSave, SUPPORTED_ROLE_PERMISSIONS, PasswordClaim, PasswordLogin, PasswordRegister, RoleSave
from backend.schemas.response import StandardResponse
from backend.schemas.access import AccessPolicy
from backend.services import accounts as svc
from backend.services.access import resolve_access
from backend.services.hris import employee_lock, version

auth_router = APIRouter()
hris_router = APIRouter()


def response(data):
    return StandardResponse(data=data)


async def bind(db, tenant_id):
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), {"tenant": str(tenant_id)})


async def payload(db, user):
    from backend.api.routes.auth import _login_payload
    return await _login_payload(user, db)


async def owner(db, user):
    context = await resolve_access(db, user)
    context.require("access.manage")
    # Delegated access administrators are deliberately not enabled yet.
    if not user.is_superuser:
        raise HTTPException(403, "Pengaturan akun saat ini dikelola pemilik usaha")
    await svc.lock(db, f"tenant:{user.tenant_id}")
    return context


async def fresh_user(db, user_id, tenant_id):
    row = await db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id,
        User.deleted_at.is_(None)).with_for_update().execution_options(populate_existing=True))
    if not row:
        raise HTTPException(404, "Akun tidak ditemukan")
    return row


def identity_data(tenant, user):
    return {"shop_username": tenant.login_username, "username": user.login_username,
        "password_enabled": bool(user.password_hash), "user_id": str(user.id)}


async def recovery_result(db, user, body, data):
    await bind(db, user.tenant_id)
    code = svc.secret_code(user.id, body.client_request_id, "recovery")
    challenge = await db.scalar(select(AccountChallenge).where(AccountChallenge.user_id == user.id,
        AccountChallenge.tenant_id == user.tenant_id, AccountChallenge.token_hash == svc.digest(code),
        AccountChallenge.consumed_at.is_(None), AccountChallenge.expires_at > svc.now()))
    return {**data, "recovery_code": code if challenge else None}


@auth_router.post("/password/login")
async def password_login(body: PasswordLogin, request: Request, db: AsyncSession = Depends(get_db)):
    await svc.limited(request, body.shop_username, body.username)
    user = await svc.identity(db, body.shop_username, body.username)
    if not await svc.password_matches(user, body.password):
        raise HTTPException(401, "Username toko, username akun atau password tidak sesuai")
    await bind(db, user.tenant_id)
    return response(await payload(db, user))


@auth_router.post("/password/register")
async def password_register(body: PasswordRegister, request: Request, db: AsyncSession = Depends(get_db)):
    await svc.limited(request, body.shop_username, body.username, "register")
    previous = await svc.audit_replay(db, None, body, "password_register")
    if previous:
        user = await svc.identity(db, body.shop_username, body.username)
        if not user or str(user.id) != previous["user_id"] or not await svc.password_matches(user, body.password):
            raise HTTPException(409, "Akun sudah berubah. Silakan masuk kembali.")
        await bind(db, user.tenant_id)
        data = await recovery_result(db, user, body, await payload(db, user))
        return response(data)
    await svc.lock(db, f"shop:{body.shop_username}")
    if await db.scalar(select(Tenant.id).where(Tenant.login_username == body.shop_username)):
        raise HTTPException(409, "Username toko sudah digunakan. Pilih username lain.")
    tid, bid, oid, uid = uuid4(), uuid4(), uuid4(), uuid4()
    tenant = Tenant(id=tid, name=body.business_name.strip(), login_username=body.shop_username,
        schema_name=f"tenant_{tid.hex[:16]}", is_active=True, subscription_tier="starter",
        subscription_status="trial", billing_day=date.today().day, next_billing_date=date.today() + timedelta(days=30))
    user = User(id=uid, tenant_id=tid, full_name=body.owner_name.strip(), phone=None,
        login_username="owner", is_superuser=True, is_active=True, row_version=1, credential_version=0)
    try:
        db.add(tenant); await db.flush()
        await bind(db, tid)
        db.add(Brand(id=bid, tenant_id=tid, name=tenant.name, type=body.business_type, is_active=True)); await db.flush()
        db.add(Outlet(id=oid, tenant_id=tid, brand_id=bid, name=tenant.name, slug=f"{body.shop_username}-{oid.hex[:8]}", is_active=True)); await db.flush()
        db.add(user); await db.flush()
        from backend.api.routes.auth import DEFAULT_CATEGORIES
        db.add_all([Category(id=uuid4(), brand_id=bid, name=name, is_active=True)
            for name in DEFAULT_CATEGORIES[body.business_type]])
        await svc.set_password(db, user, body.password)
        code = await svc.challenge(db, user, body.client_request_id, "recovery")
        svc.add_audit(db, None, tid, body, "password_register", uid, {"user_id": str(uid), "tenant_id": str(tid)})
        return response({**await payload(db, user), "recovery_code": code})
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Username toko sudah digunakan. Pilih username lain.") from None


@auth_router.get("/account")
async def account_info(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, user.tenant_id)
    return response(identity_data(tenant, user))


@auth_router.post("/password/claim")
async def password_claim(body: PasswordClaim, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owner(db, user)
    previous = await svc.audit_replay(db, user.id, body, "password_claim")
    user = await fresh_user(db, user.id, user.tenant_id)
    if previous:
        return response(await recovery_result(db, user, body, await payload(db, user)))
    if user.password_hash:
        if not await svc.password_matches(user, body.current_password or ""):
            raise HTTPException(401, "Password saat ini tidak sesuai")
    else:
        claims = request.state.auth_claims
        issued = claims.get("iat", claims.get("exp", 0) - settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        if svc.now().timestamp() - issued > 900:
            raise HTTPException(401, "Masuk ulang melalui akun lama sebelum membuat password")
    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id).with_for_update().execution_options(populate_existing=True))
    if tenant.login_username and tenant.login_username != body.shop_username:
        raise HTTPException(409, "Username toko sudah ditetapkan dan tidak dapat diganti di formulir ini")
    if user.login_username and user.login_username != body.username:
        raise HTTPException(409, "Username akun sudah ditetapkan")
    try:
        tenant.login_username = body.shop_username
        tenant.row_version += 1
        user.login_username = body.username
        await svc.set_password(db, user, body.password)
        code = await svc.challenge(db, user, body.client_request_id, "recovery")
        svc.add_audit(db, user.id, user.tenant_id, body, "password_claim", user.id, {"user_id": str(user.id)})
        return response({**await payload(db, user), "recovery_code": code})
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Username sudah digunakan. Pilih username lain.") from None


@auth_router.post("/password/challenge")
async def consume_challenge(body: ConsumeChallenge, request: Request, db: AsyncSession = Depends(get_db)):
    await svc.limited(request, body.shop_username, body.username, "challenge")
    user = await svc.identity(db, body.shop_username, body.username)
    if not user:
        raise HTTPException(401, "Kode atau identitas akun tidak sesuai")
    await bind(db, user.tenant_id)
    await svc.lock(db, f"user:{user.id}")
    user = await fresh_user(db, user.id, user.tenant_id)
    await resolve_access(db, user)
    previous = await svc.audit_replay(db, user.id, body, "consume_challenge")
    if previous:
        if previous.get("credential_version") != user.credential_version or not await svc.password_matches(user, body.password):
            raise HTTPException(409, "Akun sudah berubah. Silakan masuk kembali.")
        data = await payload(db, user)
        return response(await recovery_result(db, user, body, data) if user.is_superuser else data)
    challenge = await db.scalar(select(AccountChallenge).where(AccountChallenge.tenant_id == user.tenant_id,
        AccountChallenge.user_id == user.id, AccountChallenge.token_hash == svc.digest(body.code),
        AccountChallenge.purpose == body.purpose, AccountChallenge.deleted_at.is_(None)).with_for_update())
    if not challenge or challenge.consumed_at or challenge.expires_at <= svc.now() or challenge.credential_version != user.credential_version:
        raise HTTPException(401, "Kode tidak sesuai, sudah digunakan atau kedaluwarsa")
    await svc.set_password(db, user, body.password)
    code = await svc.challenge(db, user, body.client_request_id, "recovery") if user.is_superuser else None
    svc.add_audit(db, user.id, user.tenant_id, body, "consume_challenge", user.id,
        {"user_id": str(user.id), "credential_version": user.credential_version})
    return response({**await payload(db, user), "recovery_code": code})


@auth_router.get("/sessions")
async def sessions(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(LoginSession).where(LoginSession.tenant_id == user.tenant_id,
        LoginSession.user_id == user.id, LoginSession.revoked_at.is_(None), LoginSession.deleted_at.is_(None),
        LoginSession.expires_at > svc.now()).order_by(LoginSession.created_at.desc()).limit(100))).all()
    current = request.state.login_session
    return response([{ "id": str(row.id), "created_at": row.created_at.isoformat(),
        "expires_at": row.expires_at.isoformat(), "current": bool(current and row.id == current.id)} for row in rows])


@auth_router.post("/sessions/revoke-all")
async def revoke_sessions(body: AccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    previous = await svc.audit_replay(db, user.id, body, "sessions_revoke")
    if previous:
        return response({"ok": True})
    user = await fresh_user(db, user.id, user.tenant_id)
    await svc.revoke_all(db, user)
    svc.add_audit(db, user.id, user.tenant_id, body, "sessions_revoke", user.id, {"user_id": str(user.id)})
    await db.commit()
    return response({"ok": True})


def role_data(row):
    raw = row.permissions if isinstance(row.permissions, dict) else {}
    policy = raw.get("access_policy")
    try:
        policy = AccessPolicy.model_validate(policy).model_dump(mode="json") if policy is not None else None
    except ValidationError:
        policy = None
    return {"id": str(row.id), "name": row.name, "row_version": row.row_version,
        "editable": bool(policy and not row.is_system), "policy": policy}


def user_data(row):
    return {"id": str(row.id), "full_name": row.full_name, "username": row.login_username,
        "is_active": row.is_active, "is_owner": row.is_superuser, "role_id": str(row.role_id) if row.role_id else None,
        "password_enabled": bool(row.password_hash), "row_version": row.row_version}


@hris_router.get("/access/setup")
async def access_setup(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    context = await owner(db, user)
    tenant = await db.get(Tenant, user.tenant_id)
    roles = (await db.scalars(select(Role).where(Role.tenant_id == user.tenant_id, Role.deleted_at.is_(None)).order_by(Role.name))).all()
    accounts = (await db.scalars(select(User).where(User.tenant_id == user.tenant_id, User.deleted_at.is_(None)).order_by(User.full_name))).all()
    employees = (await db.scalars(select(HrEmployee).where(HrEmployee.tenant_id == user.tenant_id, HrEmployee.deleted_at.is_(None)).order_by(HrEmployee.name))).all()
    return response({"shop_username": tenant.login_username, "roles": [role_data(r) for r in roles],
        "accounts": [user_data(r) for r in accounts], "permissions": sorted(SUPPORTED_ROLE_PERMISSIONS),
        "outlets": context.public()["outlets"], "employees": [{"id": str(r.id), "name": r.name,
            "user_id": str(r.user_id) if r.user_id else None, "outlet_id": str(r.outlet_id),
            "row_version": r.row_version, "is_active": r.is_active} for r in employees]})


@hris_router.post("/access/roles")
async def save_role(body: RoleSave, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    context = await owner(db, user)
    for outlet_id in body.outlet_ids:
        context.require_outlet(outlet_id)
    previous = await svc.audit_replay(db, user.id, body, "role_save")
    if previous:
        return response(previous)
    row = await db.scalar(select(Role).where(Role.id == body.id, Role.tenant_id == user.tenant_id).with_for_update())
    if not row:
        if body.row_version:
            raise HTTPException(409, "Jabatan sudah berubah. Muat ulang.")
        if await db.scalar(select(Role.id).where(Role.id == body.id)):
            raise HTTPException(404, "Jabatan tidak ditemukan")
        row = Role(id=body.id, tenant_id=user.tenant_id, scope="outlet", name=body.name.strip(), row_version=1)
        db.add(row)
    else:
        if row.deleted_at or row.is_system or not (row.permissions or {}).get("access_policy"):
            raise HTTPException(409, "Jabatan lama tidak diubah otomatis. Buat jabatan baru.")
        version(row, body)
        row.row_version += 1
    row.name = body.name.strip()
    row.permissions = {"access_policy": {"version": 1, "permissions": body.permissions,
        "outlet_ids": [str(i) for i in body.outlet_ids], "brand_ids": []}}
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "ID jabatan sudah digunakan atau data berubah. Muat ulang.") from None
    result = role_data(row)
    svc.add_audit(db, user.id, user.tenant_id, body, "role_save", row.id, result)
    await db.commit()
    return response(result)


@hris_router.post("/employees/{employee_id}/account")
async def save_employee_account(employee_id: UUID, body: EmployeeAccountSave, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    context = await owner(db, user)
    employee = await employee_lock(db, user, employee_id)
    context.require_outlet(employee.outlet_id)
    previous = await svc.audit_replay(db, user.id, body, "employee_account")
    if previous:
        if previous.get("employee_id") != str(employee_id):
            raise HTTPException(409, "Permintaan sudah dipakai untuk karyawan lain")
        return response(previous)
    version(employee, body)
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant.login_username:
        raise HTTPException(409, "Tetapkan username toko dan password pemilik terlebih dahulu")
    if body.is_active and not employee.is_active:
        raise HTTPException(409, "Aktifkan profil karyawan terlebih dahulu")
    role = await db.scalar(select(Role).where(Role.id == body.role_id, Role.tenant_id == user.tenant_id, Role.deleted_at.is_(None))) if body.role_id else None
    if body.role_id and not role:
        raise HTTPException(404, "Jabatan tidak ditemukan")
    if not employee.user_id and not role:
        raise HTTPException(422, "Pilih jabatan untuk akun baru")
    if role:
        policy = role_data(role)["policy"]
        if not policy or role.scope != "outlet" or policy["brand_ids"]:
            raise HTTPException(422, "Pilih jabatan dengan pengaturan izin dan outlet yang valid")
        for outlet_id in policy["outlet_ids"]:
            context.require_outlet(UUID(outlet_id))
        if str(employee.outlet_id) not in policy["outlet_ids"]:
            raise HTTPException(422, "Outlet utama karyawan harus termasuk dalam jabatan")
    try:
        if employee.user_id:
            account = await fresh_user(db, employee.user_id, user.tenant_id)
            if account.is_superuser:
                raise HTTPException(403, "Akun pemilik tidak diubah melalui profil karyawan")
            if body.user_row_version != account.row_version:
                raise HTTPException(409, "Akun sudah berubah. Muat ulang.")
            # A missing role preserves an existing legacy account's POS access.
            if body.role_id:
                account.role_id = body.role_id
            account.login_username = body.username
            account.is_active = body.is_active
            await svc.revoke_all(db, account)
        else:
            account = User(id=uuid4(), tenant_id=user.tenant_id, full_name=employee.name,
                phone=None, login_username=body.username, role_id=role.id, is_active=body.is_active,
                is_superuser=False, credential_version=1, row_version=1)
            db.add(account); await db.flush()
            employee.user_id = account.id
        employee.row_version += 1
        await db.flush()
        result = {**user_data(account), "employee_id": str(employee.id), "employee_row_version": employee.row_version}
        svc.add_audit(db, user.id, user.tenant_id, body, "employee_account", account.id, result)
        await db.commit()
        return response(result)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Username akun sudah digunakan atau profil berubah. Muat ulang.") from None


@hris_router.post("/employees/{employee_id}/activation")
async def staff_activation(employee_id: UUID, body: AccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    context = await owner(db, user)
    employee = await employee_lock(db, user, employee_id)
    context.require_outlet(employee.outlet_id)
    if not employee.user_id or not employee.is_active:
        raise HTTPException(409, "Hubungkan akun pada karyawan aktif terlebih dahulu")
    account = await fresh_user(db, employee.user_id, user.tenant_id)
    if account.is_superuser or not account.is_active or not account.login_username:
        raise HTTPException(409, "Aktivasi hanya untuk akun karyawan aktif dengan username")
    previous = await svc.audit_replay(db, user.id, body, "staff_activation")
    if previous and (previous.get("user_id") != str(account.id) or previous.get("credential_version") != account.credential_version):
        raise HTTPException(409, "Aktivasi sudah berubah. Buat kode baru.")
    if not previous:
        await svc.revoke_all(db, account, clear_password=True)
        await svc.challenge(db, account, body.client_request_id, "activation")
        result = {"user_id": str(account.id), "credential_version": account.credential_version}
        svc.add_audit(db, user.id, user.tenant_id, body, "staff_activation", account.id, result)
        await db.commit()
    code = svc.secret_code(account.id, body.client_request_id, "activation")
    await bind(db, user.tenant_id)
    challenge = await db.scalar(select(AccountChallenge).where(AccountChallenge.tenant_id == account.tenant_id,
        AccountChallenge.user_id == account.id, AccountChallenge.token_hash == svc.digest(code),
        AccountChallenge.consumed_at.is_(None), AccountChallenge.expires_at > svc.now()))
    if not challenge:
        raise HTTPException(409, "Kode sudah dipakai atau kedaluwarsa. Buat kode baru.")
    tenant = await db.get(Tenant, user.tenant_id)
    return response({"code": code, "shop_username": tenant.login_username, "username": account.login_username,
        "expires_at": challenge.expires_at.isoformat()})
