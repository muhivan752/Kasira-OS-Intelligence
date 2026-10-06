"""Unified staff creation through real HTTP/JWT against synthetic forced-RLS PostgreSQL."""
import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api.api import api_router
from backend.api import deps
from backend.core.config import settings
from backend.core.database import engine, AsyncSessionLocal
from backend.core.security import create_access_token
from backend.models import AuditLog, Brand, HrEmployee, Outlet, Role, Tenant, User
from backend.services import accounts, staff_accounts

assert settings.POSTGRES_SERVER == "selaris-business-qa-db"
assert settings.POSTGRES_APP_USER == "business_app"
admin = create_async_engine("postgresql+asyncpg://business_admin:business-test-only@selaris-business-qa-db/business_qa")
Admin = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI(); app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_id(request, call_next):
    request.state.request_id = "staff-accounts-qa"
    return await call_next(request)


class Redis:
    def __init__(self): self.values = {}
    async def get(self, key): return self.values.get(key)
    async def eval(self, *args): return 1


async def main():
    async with Admin() as db:
        tid, foreign_tid = uuid4(), uuid4()
        db.add_all([Tenant(id=t, name="Synthetic staff QA", schema_name="qa_" + t.hex,
            login_username="staff_" + t.hex, subscription_tier="pro") for t in (tid, foreign_tid)])
        await db.flush()
        brand = Brand(id=uuid4(), tenant_id=tid, name="Staff fixture", type="cafe"); db.add(brand); await db.flush()
        outlets = [Outlet(id=uuid4(), tenant_id=tid, brand_id=brand.id, name="Fixture " + str(i),
            slug="qa-" + uuid4().hex, timezone="Asia/Jakarta") for i in range(2)]
        db.add_all(outlets); await db.flush()
        def role(name, grants, ids, scope="outlet"):
            return Role(id=uuid4(), tenant_id=tid, name=name, scope=scope,
                permissions={"access_policy": {"version": 1, "permissions": {p: True for p in grants},
                    "outlet_ids": [str(i) for i in ids], "brand_ids": []}})
        manager_role = role("Fixture manager", ["hris.accounts.manage", "hris.employees.manage", "hris.self", "pos.sell"], [outlets[0].id])
        staff_role = role("Fixture kasir", ["hris.self", "pos.sell"], [outlets[0].id])
        broad_role = role("Fixture luas", ["hris.self", "pos.sell"], [], "tenant")
        finance_role = role("Fixture keuangan", ["hris.self", "finance.manage"], [outlets[0].id])
        no_grant = role("Fixture profil", ["hris.employees.manage", "hris.self"], [outlets[0].id])
        db.add_all([manager_role, staff_role, broad_role, finance_role, no_grant]); await db.flush()
        owner = User(id=uuid4(), tenant_id=tid, full_name="Fixture owner", is_superuser=True)
        manager = User(id=uuid4(), tenant_id=tid, full_name="Fixture manager", role_id=manager_role.id)
        profile_manager = User(id=uuid4(), tenant_id=tid, full_name="Fixture profile manager", role_id=no_grant.id)
        legacy = User(id=uuid4(), tenant_id=tid, full_name="Fixture Irfan legacy", phone="6285270782220")
        foreign = User(id=uuid4(), tenant_id=foreign_tid, full_name="Foreign fixture")
        db.add_all([owner, manager, profile_manager, legacy, foreign]); await db.commit()
        shop = "staff_" + tid.hex
    redis = Redis()
    tokens = {u.id: create_access_token(u.id) for u in (owner, manager, profile_manager, foreign)}
    with patch.object(deps, "get_redis_client", AsyncMock(return_value=redis)), patch.object(accounts, "get_redis_client", AsyncMock(return_value=redis)):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://qa") as client:
            async def call(method, path, body=None, actor=owner, status=200, token=None):
                response = await client.request(method, "/api/v1" + path, json=body,
                    headers={"Authorization": "Bearer " + (token or tokens[actor.id])})
                assert response.status_code == status, (method, path, status, response.status_code, response.text)
                return response.json().get("data")
            password = "  qa-pass-staff  "
            profile = {"client_request_id": str(uuid4()), "name": "Fixture Irfan", "position": "Barista",
                "outlet_id": str(outlets[0].id), "started_on": "2026-01-01", "phone": "085270782220",
                "account": {"use_phone": True, "password": password}}
            created, replay = await asyncio.gather(*[call("POST", "/hris/employees", profile, manager) for _ in range(2)])
            assert created == replay and created["account_username"] == "6285270782220"
            eid, uid = created["id"], UUID(created["account_id"])
            await call("POST", "/hris/employees", {**profile, "name": "Different"}, manager, 409)
            receipt = await call("GET", "/hris/requests/" + profile["client_request_id"], actor=manager)
            assert receipt["state"] == "saved" and receipt["result"] == created
            assert (await call("GET", "/hris/requests/" + profile["client_request_id"]))["state"] == "unknown"
            async with Admin() as db:
                account = await db.get(User, uid)
                assert account.phone is None and await accounts.password_matches(account, password)
                assert not await accounts.password_matches(account, password.strip())
                logs = (await db.scalars(select(AuditLog).where(AuditLog.tenant_id == tid))).all()
                assert password not in json.dumps([r.after_state for r in logs])
                assert await db.scalar(select(func.count()).select_from(HrEmployee).where(HrEmployee.user_id == uid)) == 1
                assert len((await db.scalars(select(Role).where(Role.tenant_id == tid, Role.name.like("Absensi pribadi%")))).all()) == 1
            print("PASS atomic profile+account create, concurrent replay, keyed audit without password, actor-only receipt; password whitespace preserved")
            for phone in ("085270782220", "6285270782220", "+62 852-7078-2220"):
                logged = await call("POST", "/auth/password/login", {"shop_username": shop, "username": phone, "password": password})
                assert logged["user_id"] == str(uid)
            await call("POST", "/hris/employees", {**profile, "client_request_id": str(uuid4())}, manager, 409)
            print("PASS phone aliases login, tenant-local collision prevention, no claim of OTP phone identity")
            for bad, status, actor in [({"outlet_id": str(outlets[1].id)}, 404, manager),
                ({"account": {"username": "finance-user", "role_id": str(finance_role.id), "password": password}}, 403, manager),
                ({"account": {"username": "broad-user", "role_id": str(broad_role.id), "password": password}}, 403, manager),
                ({}, 403, profile_manager), ({"user_id": str(owner.id)}, 403, manager),
                ({"user_id": str(manager.id)}, 403, manager), ({"user_id": str(legacy.id)}, 403, manager),
                ({"user_id": str(foreign.id)}, 404, manager),
                ({"account": {"username": "short", "password": "1234567"}}, 422, owner)]:
                await call("POST", "/hris/employees", {**profile, "client_request_id": str(uuid4()), **bad}, actor, status)
            allowed = await call("POST", "/hris/employees", {**profile, "client_request_id": str(uuid4()),
                "account": {"username": "fixture-kasir", "role_id": str(staff_role.id), "password": password}}, manager)
            async with Admin() as db:
                assert (await db.get(User, UUID(allowed["account_id"]))).role_id == staff_role.id
                assert await db.scalar(select(func.count()).select_from(HrEmployee).where(HrEmployee.tenant_id == tid)) == 2
            print("PASS manager granular grant, outlet/permission subset, owner/self/legacy/foreign protection, failed writes rolled back")
            legacy_profile = await call("POST", "/hris/employees", {"client_request_id": str(uuid4()), "name": "Irfan existing",
                "position": "Barista", "outlet_id": str(outlets[0].id), "started_on": "2026-01-01", "user_id": str(legacy.id),
                "account": {"username": "irfan", "password": password, "user_row_version": 1}})
            assert legacy_profile["account_id"] == str(legacy.id)
            async with Admin() as db:
                old = await db.get(User, legacy.id)
                assert old.role_id is None and old.phone == "6285270782220"
                old_version = old.row_version
            edited_body = {"client_request_id": str(uuid4()), "row_version": legacy_profile["row_version"], "name": "Irfan existing",
                "position": "Senior barista", "outlet_id": str(outlets[0].id), "started_on": "2026-01-01", "user_id": str(legacy.id),
                "account": {"username": "irfan", "user_row_version": old_version}}
            await call("PUT", "/hris/employees/" + legacy_profile["id"], edited_body)
            await call("PUT", "/hris/employees/" + legacy_profile["id"], {**edited_body, "client_request_id": str(uuid4())}, status=409)
            print("PASS existing Irfan UUID and legacy role preserved; optional password, optimistic profile/account versions")
            setup = await call("GET", "/hris/setup", actor=manager)
            assert setup["account_admin"] and "hris.accounts.manage" in setup["permissions"]
            assert legacy.id not in {UUID(a["id"]) for a in setup["accounts"]}
            assert all(r["id"] not in {str(finance_role.id), str(broad_role.id)} for r in setup["roles"])
            assert not (await call("GET", "/hris/setup", actor=profile_manager))["account_admin"]
            assert "access.manage" in (await call("GET", "/hris/setup"))["permissions"]
            print("PASS scoped account/role choices and owner account-settings link; no escalation through options")
            original_set = accounts.set_password
            async def revoke_during_hash(db, user, password):
                await original_set(db, user, password)
                redis.values["revoked-token:" + accounts.digest(tokens[manager.id])] = "1"
            with patch.object(accounts, "set_password", revoke_during_hash):
                await call("POST", "/hris/employees", {**profile, "client_request_id": str(uuid4()),
                    "account": {"username": "revoked-staff", "password": password}}, manager, 401)
            async with Admin() as db:
                assert not await db.scalar(select(User.id).where(User.tenant_id == tid, User.login_username == "revoked-staff"))
                for table in ("users", "hr_employees", "roles", "audit_log"):
                    flags = (await db.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname=:name"), {"name": table})).one()
                    assert flags == (True, True), (table, flags)
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tid)})
                assert not await db.scalar(select(User.id).where(User.id == foreign.id))
                flags = (await db.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"))).one()
                assert flags == (False, False)
            print("PASS revoked JWT during password hashing discards whole transaction; real NOSUPERUSER/NOBYPASSRLS and forced tenant RLS")
            async with Admin() as db:
                default_role = await db.scalar(select(Role).where(Role.tenant_id == tid, Role.name.like("Absensi pribadi%")))
                default_role.permissions = {"access_policy": {"version": 1, "permissions": {"hris.self": True, "finance.manage": True}, "outlet_ids": [str(outlets[0].id)]}}
                await db.commit()
            await call("POST", "/hris/employees", {**profile, "client_request_id": str(uuid4()),
                "account": {"username": "changed-default", "password": password}}, status=409)
            print("PASS default Absensi pribadi refuses silently expanded permissions; broader grants require explicit role selection")
            async with Admin() as db:
                for username in ("0812345678", "62812345678", "012345678901234"):
                    account = User(id=uuid4(), tenant_id=tid, full_name="Numeric legacy fixture", login_username=username,
                        role_id=staff_role.id, phone=None, credential_version=0, row_version=1)
                    db.add(account); await db.flush(); await accounts.set_password(db, account, password)
                await db.commit()
            await call("POST", "/auth/password/login", {"shop_username": shop, "username": "0812345678", "password": password}, status=401)
            logged = await call("POST", "/auth/password/login", {"shop_username": shop, "username": "012345678901234", "password": password})
            assert logged["username"] == "012345678901234"
            print("PASS ambiguous legacy phone aliases fail closed; long numeric username compatibility; existing OTP phone untouched")
    await engine.dispose(); await admin.dispose()


asyncio.run(main())
