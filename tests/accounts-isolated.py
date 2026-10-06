"""Account migration, activation, password recovery and actual device revocation."""
import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api import deps
from backend.api.api import api_router
from backend.api.routes import auth
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, engine
from backend.core.security import create_access_token
from backend.models import AccountChallenge, AuditLog, Brand, HrEmployee, LoginSession, Outlet, Role, Tenant, User
from backend.services import accounts as svc

assert settings.POSTGRES_SERVER == "selaris-account-qa-db"
assert settings.POSTGRES_APP_USER == "account_app"
admin = create_async_engine("postgresql+asyncpg://account_admin:account-test-only@selaris-account-qa-db/account_qa")
Admin = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_id(request, call_next):
    request.state.request_id = "account-qa"
    return await call_next(request)


class Redis:
    def __init__(self): self.values = {}
    async def get(self, key): return self.values.get(key)
    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]
    async def expire(self, key, ttl): return True
    async def eval(self, script, numkeys, key, ttl): return await self.incr(key)
    async def setex(self, key, ttl, value): self.values[key] = value
    async def delete(self, *keys):
        for key in keys: self.values.pop(key, None)


async def main():
    redis = Redis()
    with patch.object(deps, "get_redis_client", AsyncMock(return_value=redis)), \
        patch.object(auth, "get_redis_client", AsyncMock(return_value=redis)), \
        patch.object(svc, "get_redis_client", AsyncMock(return_value=redis)):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://qa") as client:
            async def call(method, path, body=None, token=None, tenant=None, status=200):
                headers = {"Authorization": "Bearer " + token} if token else {}
                if tenant: headers["X-Tenant-ID"] = str(tenant)
                result = await client.request(method, "/api/v1" + path, json=body, headers=headers)
                assert result.status_code == status, (method, path, status, result.status_code, result.text)
                return result.json().get("data")
            password = "qa-short"
            shop = "qa-" + uuid4().hex[:16]
            register = {"shop_username": shop.upper(), "password": password, "business_name": "QA synthetic shop",
                "owner_name": "QA owner", "client_request_id": str(uuid4())}
            await call("POST", "/auth/password/register", {**register, "password": "short7!"}, status=422)
            registered, replay = await asyncio.gather(*[call("POST", "/auth/password/register", register) for _ in range(2)])
            assert registered["tenant_id"] == replay["tenant_id"] and registered["user_id"] == replay["user_id"]
            assert registered["recovery_code"] == replay["recovery_code"]
            owner_token, tid, uid, oid = registered["access_token"], registered["tenant_id"], registered["user_id"], registered["outlet_id"]
            await call("POST", "/auth/password/register", {**register, "client_request_id": str(uuid4())}, status=409)
            await call("POST", "/auth/password/register", {**register, "owner_name": "changed"}, status=409)
            login = await call("POST", "/auth/password/login", {"shop_username": shop, "password": password})
            assert login["tenant_id"] == tid and login["user_id"] == uid
            await call("POST", "/auth/password/login", {"shop_username": shop, "password": "wrong"}, status=401)
            await call("POST", "/auth/password/login", {"shop_username": "unknown-account", "password": "wrong"}, status=401)
            await call("GET", "/auth/me", token=create_access_token(uid), status=401)
            devices = await call("GET", "/auth/sessions", token=owner_token)
            assert len(devices) == 3 and sum(s["current"] for s in devices) == 1
            await call("DELETE", "/auth/logout", token=login["access_token"])
            await call("GET", "/auth/me", token=login["access_token"], status=401)
            await call("GET", "/auth/me", token=owner_token)
            print("PASS registration race and replay, password hash, cross-client identity, logout one device")

            recovery = {"shop_username": shop, "code": registered["recovery_code"], "purpose": "recovery",
                "password": "qa replacement password 456", "client_request_id": str(uuid4())}
            recovered = await call("POST", "/auth/password/challenge", recovery)
            again = await call("POST", "/auth/password/challenge", recovery)
            assert recovered["recovery_code"] == again["recovery_code"]
            await call("POST", "/auth/password/challenge", {**recovery, "client_request_id": str(uuid4())}, status=401)
            await call("GET", "/auth/me", token=owner_token, status=401)
            owner_token = recovered["access_token"]
            print("PASS recovery one-use, safe retry, replacement recovery code, all prior sessions revoked")

            role = {"id": str(uuid4()), "name": "QA staff", "outlet_ids": [oid], "permissions": {"hris.self": True}, "client_request_id": str(uuid4())}
            saved_role = await call("POST", "/hris/access/roles", role, owner_token)
            assert saved_role["row_version"] == 1
            assert await call("POST", "/hris/access/roles", role, owner_token) == saved_role
            ai_role = await call("POST", "/hris/access/roles", {**role, "id": str(uuid4()), "client_request_id": str(uuid4()), "permissions": {"ai.chat": True}}, owner_token)
            assert ai_role["policy"]["permissions"] == {"ai.chat": True}
            await call("POST", "/hris/access/roles", {**role, "id": str(uuid4()), "client_request_id": str(uuid4()), "permissions": {"ai.superuser": True}}, owner_token, status=422)
            await call("POST", "/hris/access/roles", {**role, "id": str(uuid4()), "client_request_id": str(uuid4()), "outlet_ids": [str(uuid4())]}, owner_token, status=404)
            async with Admin() as db:
                employee = HrEmployee(id=uuid4(), tenant_id=tid, outlet_id=oid, code="QA-KRY", name="QA staff",
                    position="QA", started_on=date(2026, 10, 1), is_active=True, row_version=1)
                db.add(employee); await db.commit()
            account_body = {"row_version": 1, "username": "staff-qa", "role_id": role["id"], "client_request_id": str(uuid4())}
            staff = await call("POST", f"/hris/employees/{employee.id}/account", account_body, owner_token)
            assert staff["password_enabled"] is False
            activation_body = {"client_request_id": str(uuid4())}
            activation = await call("POST", f"/hris/employees/{employee.id}/activation", activation_body, owner_token)
            assert await call("POST", f"/hris/employees/{employee.id}/activation", activation_body, owner_token) == activation
            consume = {"shop_username": shop, "username": "staff-qa", "code": activation["code"], "purpose": "activation",
                "password": password, "client_request_id": str(uuid4())}
            activated = await call("POST", "/auth/password/challenge", consume)
            await call("POST", "/auth/password/challenge", {**consume, "client_request_id": str(uuid4())}, status=401)
            await call("GET", "/auth/access", token=activated["access_token"])
            await call("GET", "/hris/access/setup", token=activated["access_token"], status=403)
            await call("GET", "/finance/accounts", token=activated["access_token"], tenant=tid, status=403)
            print("PASS role permissions and outlets, private staff activation, no owner escalation")

            # Two simultaneous uses with different request IDs must consume once.
            reset = await call("POST", f"/hris/employees/{employee.id}/activation", {"client_request_id": str(uuid4())}, owner_token)
            await call("GET", "/auth/me", token=activated["access_token"], status=401)
            race = [client.post("/api/v1/auth/password/challenge", json={**consume, "code": reset["code"], "client_request_id": str(uuid4())}) for _ in range(2)]
            results = await asyncio.gather(*race)
            assert sorted(r.status_code for r in results) == [200, 401], [r.text for r in results]
            staff_token = next(r.json()["data"]["access_token"] for r in results if r.status_code == 200)
            profile = {"name": employee.name, "position": employee.position, "outlet_id": oid,
                "user_id": staff["id"], "started_on": employee.started_on.isoformat(),
                "is_active": False, "row_version": 2, "client_request_id": str(uuid4())}
            inactive = await call("PUT", f"/hris/employees/{employee.id}", profile, owner_token)
            await call("GET", "/auth/me", token=staff_token, status=403)
            await call("POST", "/auth/password/login", {"shop_username": shop, "username": "staff-qa", "password": password}, status=403)
            await call("PUT", f"/hris/employees/{employee.id}", {**profile, "row_version": inactive["row_version"], "is_active": True, "client_request_id": str(uuid4())}, owner_token)
            await call("GET", "/auth/me", token=staff_token, status=401)
            await call("POST", "/auth/password/login", {"shop_username": shop, "username": "staff-qa", "password": password})
            print("PASS activation race, owner reset revocation, inactive HRIS denies password and old JWT")

            async with Admin() as db:
                legacy_tenant = Tenant(id=uuid4(), name="QA legacy", schema_name=f"qa_{uuid4().hex}")
                db.add(legacy_tenant); await db.flush()
                legacy_owner = User(id=uuid4(), tenant_id=legacy_tenant.id, phone=f"qa-{uuid4().hex}", full_name="QA legacy owner", is_superuser=True)
                db.add(legacy_owner); await db.commit()
            legacy_token = create_access_token(legacy_owner.id)
            await call("GET", "/auth/me", token=legacy_token)
            claim = {"shop_username": f"legacy-{uuid4().hex[:10]}", "password": password, "client_request_id": str(uuid4())}
            migrated = await call("POST", "/auth/password/claim", claim, legacy_token)
            assert migrated["tenant_id"] == str(legacy_tenant.id) and migrated["user_id"] == str(legacy_owner.id)
            await call("GET", "/auth/me", token=legacy_token, status=401)
            await call("POST", "/auth/password/claim", {**claim, "client_request_id": str(uuid4())}, migrated["access_token"], status=401)
            await call("GET", "/auth/account", token=migrated["access_token"], tenant=tid, status=403)
            await call("POST", "/auth/sessions/revoke-all", {"client_request_id": str(uuid4())}, migrated["access_token"])
            await call("GET", "/auth/me", token=migrated["access_token"], status=401)
            print("PASS legacy migration keeps UUIDs and phone, requires reauthentication, tenant headers and logout all")

            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": tid})
                assert await db.scalar(select(func.count()).select_from(LoginSession).where(LoginSession.tenant_id == legacy_tenant.id)) == 0
                rows = (await db.scalars(select(AuditLog).where(AuditLog.tenant_id == tid, AuditLog.entity == "account_access"))).all()
                for row in rows:
                    stored = str(row.after_state)
                    assert password not in stored and registered["recovery_code"] not in stored and activation["code"] not in stored
                assert await db.scalar(select(User.phone).where(User.id == UUID(uid))) is None
                row = await db.get(User, UUID(uid))
                assert row.password_hash.startswith("$pbkdf2-sha256$600000$") and row.password_hash != recovery["password"]
                assert not (await db.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"))).scalar()
            redis.values = {}
            for _ in range(12): await svc.limited(type("Req", (), {"client": None})(), "limited-shop", "owner")
            try: await svc.limited(type("Req", (), {"client": None})(), "limited-shop", "owner")
            except Exception as error: assert error.status_code == 429
            else: raise AssertionError("missing rate limit")
            print("PASS forced RLS, credential and audit privacy, real NULL phones, per-identity rate limit")
    await engine.dispose(); await admin.dispose()


asyncio.run(main())
