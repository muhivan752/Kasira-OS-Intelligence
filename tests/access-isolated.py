"""Real JWT, HTTP and forced-RLS checks against an empty QA database."""
import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api import deps
from backend.api.api import api_router
from backend.api.routes import auth
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, engine
from backend.core.security import create_access_token, get_pin_hash
from backend.models import AuditLog, Brand, HrAttendance, HrEmployee, HrSchedule, Outlet, Role, Tenant, User
from backend.services import hris as svc
from backend.services.access import resolve_access


assert settings.POSTGRES_SERVER == "selaris-access-qa-db"
assert settings.POSTGRES_APP_USER == "access_app"
admin = create_async_engine("postgresql+asyncpg://access_admin:access-test-only@selaris-access-qa-db/access_qa")
Admin = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_id(request, call_next):
    request.state.request_id = "access-qa"
    return await call_next(request)


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, ttl, value):
        self.values[key] = value

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


async def main():
    async with Admin() as db:
        users, outlets, roles = [], [], []
        tenants = [Tenant(id=uuid4(), name=f"ACCESS QA {i}", schema_name=f"qa_{uuid4().hex}",
            subscription_tier="pro", subscription_status="active") for i in range(2)]
        db.add_all(tenants); await db.flush()
        brands = [Brand(id=uuid4(), tenant_id=t.id, name=f"QA {i}", type="cafe") for i, t in enumerate(tenants)]
        db.add_all(brands); await db.flush()
        for i in range(3):
            tid = tenants[0 if i < 2 else 1].id
            bid = brands[0 if i < 2 else 1].id
            outlets.append(Outlet(id=uuid4(), tenant_id=tid, brand_id=bid, name=f"QA outlet {i}",
                slug=f"qa-{uuid4().hex}", kitchen_mode="display"))
        db.add_all(outlets); await db.flush()
        grants = ({"hris_manage": True},
            {"access_policy": {"version": 1, "permissions": {"hris.self": True}, "outlet_ids": [str(outlets[0].id)]}},
            {"access_policy": {"version": 1, "permissions": {"hris.schedules.manage": True}, "outlet_ids": [str(outlets[0].id)]}},
            {"access_policy": {"version": 1, "permissions": {"hris.employees.manage": True}, "outlet_ids": [str(outlets[0].id)]}},
            {"access_policy": {"version": 1, "permissions": {"hris.attendance.manage": True}, "outlet_ids": [str(outlets[0].id)]}})
        for i, permission in enumerate(grants):
            roles.append(Role(id=uuid4(), tenant_id=tenants[0].id, name=f"QA role {i}",
                scope="tenant" if i == 0 else "outlet", permissions=permission))
        db.add_all(roles); await db.flush()
        for i in range(7):
            users.append(User(id=uuid4(), tenant_id=tenants[0].id, full_name=f"QA user {i}",
                phone=f"qa-{uuid4().hex}", is_superuser=i == 0, pin_hash=get_pin_hash("135790"),
                role_id=roles[i-2].id if i >= 2 else None))
        users.append(User(id=uuid4(), tenant_id=tenants[1].id, full_name="QA other owner",
            phone=f"qa-{uuid4().hex}", is_superuser=True))
        users[3].google_project_id = "qa-project"
        users[3].google_uid = "qa-google-user"
        foreign_role = Role(id=uuid4(), tenant_id=tenants[1].id, name="QA foreign", scope="tenant", permissions={"hris_manage": True})
        db.add(foreign_role); await db.flush()
        users.append(User(id=uuid4(), tenant_id=tenants[0].id, full_name="QA foreign role user",
            phone=f"qa-{uuid4().hex}", role_id=foreign_role.id))
        db.add_all(users); await db.commit()
    redis = FakeRedis()
    real_now = svc.now
    svc.now = lambda: datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
    try:
        with patch.object(deps, "get_redis_client", AsyncMock(return_value=redis)), \
             patch.object(auth, "get_redis_client", AsyncMock(return_value=redis)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://qa") as client:
                sessions = {}
                async def call(method, path, who=0, status=200, body=None, params=None, tenant=None):
                    headers = {"Authorization": "Bearer " + sessions.get(who, create_access_token(users[who].id)),
                        "X-Tenant-ID": str(tenant or users[who].tenant_id)}
                    response = await client.request(method, "/api/v1" + path, json=body, params=params, headers=headers)
                    assert response.status_code == status, (method, path, who, status, response.status_code, response.text)
                    return response.json()

                owner = (await call("GET", "/auth/access"))["data"]
                assert owner["enforcement_mode"] == "owner" and len(owner["outlets"]) == 2
                managed = (await call("GET", "/auth/access", who=3))["data"]
                assert managed["permissions"] == ["hris.self"] and [o["id"] for o in managed["outlets"]] == [str(outlets[0].id)]
                await call("GET", "/auth/access", who=8, status=403)
                await call("GET", "/auth/access", who=3, tenant=tenants[1].id, status=403)
                await call("POST", "/ai/hpp-setup/sessions", who=0, tenant=tenants[1].id, status=403,
                    body={"outlet_id": str(outlets[2].id)})
                me = (await call("GET", "/auth/me", who=3))["data"]
                assert me["outlet_id"] == str(outlets[0].id)
                with patch.object(auth.settings, "DEMO_PHONE", users[3].phone), patch.object(auth.settings, "DEMO_OTP", "123456"):
                    login = await client.post("/api/v1/auth/otp/verify", json={"phone": users[3].phone, "otp": "123456"})
                    assert login.status_code == 200 and login.json()["data"]["outlet_id"] == str(outlets[0].id)
                pin_login = await client.post("/api/v1/auth/pin/verify", json={"phone": users[3].phone, "pin": "135790"})
                assert pin_login.status_code == 403
                with patch.object(auth, "verify_google_token", AsyncMock(return_value={"project": "qa-project", "uid": "qa-google-user"})):
                    google = await client.post("/api/v1/auth/google", json={"id_token": "qa-token-long-enough-for-schema"})
                    assert google.status_code == 200 and google.json()["data"]["outlet_id"] == str(outlets[0].id)
                print("PASS real JWT, tenant header binding, foreign-role denial, access contract and login outlet")

                profile = {"client_request_id": str(uuid4()), "name": "QA staff", "position": "Kasir",
                    "outlet_id": str(outlets[0].id), "user_id": str(users[3].id), "started_on": "2025-01-01",
                    "notes": "PRIVATE EMPLOYEE NOTE", "phone": "081234567890"}
                employee = (await call("POST", "/hris/employees", body=profile))["data"]
                other = (await call("POST", "/hris/employees", body={**profile, "client_request_id": str(uuid4()),
                    "user_id": None, "name": "QA other", "outlet_id": str(outlets[1].id)}))["data"]
                second = (await call("POST", "/hris/employees", body={**profile, "client_request_id": str(uuid4()),
                    "user_id": None, "name": "QA second"}))["data"]
                setup = (await call("GET", "/hris/setup", who=3))["data"]
                assert len(setup["outlets"]) == 1 and setup["self_employee"]["notes"] is None
                assert setup["self_employee"]["phone"] is None and not setup["accounts"]
                period = {"outlet_id": str(outlets[0].id), "start": "2026-10-06", "end": "2026-10-06"}
                own = (await call("GET", "/hris/workspace", who=3, params=period))["data"]
                assert own["total"] == 1 and own["items"][0]["id"] == employee["id"]
                await call("GET", "/hris/workspace", who=3, params={**period, "outlet_id": str(outlets[1].id)}, status=404)
                await call("GET", "/hris/workspace", who=3, params={**period, "outlet_id": str(outlets[2].id)}, status=404)
                await call("GET", "/hris/employee-choices", who=3, status=403)
                await call("GET", "/hris/workspace", who=4, params=period, status=403)
                choice = (await call("GET", "/hris/employee-choices", who=4))["data"]
                assert {item["id"] for item in choice["items"]} == {employee["id"], second["id"]}
                print("PASS self-only profile privacy, outlet scope, scoped chooser and granular profile read denial")

                schedule = {"client_request_id": str(uuid4()), "employee_id": employee["id"],
                    "outlet_id": str(outlets[0].id), "starts_at": "2026-10-06T11:00:00Z", "ends_at": "2026-10-06T18:00:00Z"}
                a, b = await asyncio.gather(*[call("POST", "/hris/schedules", who=4, body=schedule) for _ in range(2)])
                assert a["data"] == b["data"]
                sid = a["data"]["id"]
                await call("POST", "/hris/schedules", who=6, status=403, body={**schedule, "client_request_id": str(uuid4())})
                await call("POST", "/hris/attendance", who=4, status=403, body={"client_request_id": str(uuid4()),
                    "employee_id": second["id"], "outlet_id": str(outlets[0].id), "work_date": "2026-10-06", "status": "izin", "reason": "QA"})
                await call("POST", "/hris/schedules", who=4, status=404, body={**schedule,
                    "client_request_id": str(uuid4()), "employee_id": other["id"]})
                await call("POST", "/hris/employees", who=5, status=403, body={**profile,
                    "client_request_id": str(uuid4()), "user_id": str(users[1].id)})
                await call("POST", "/hris/employees", status=403, body={**profile,
                    "client_request_id": str(uuid4()), "user_id": str(users[0].id)})
                await call("PUT", "/hris/employees/" + other["id"], who=5, status=404,
                    body={**profile, "client_request_id": str(uuid4()), "user_id": None, "row_version": 1})
                scoped = (await call("GET", "/hris/workspace", who=4, params={**period, "kind": "schedules"}))["data"]
                assert scoped["total"] == 1 and scoped["summary"]["present"] is None
                assert scoped["summary"]["unrecorded_started"] is None
                assert scoped["summary_scopes"]["attendance"] == "no_access"
                print("PASS granular create permissions, concurrent replay, old/new profile outlet checks and summary isolation")

                punch = {"client_request_id": str(uuid4()), "outlet_id": str(outlets[0].id), "action": "in"}
                a, b = await asyncio.gather(*[call("POST", "/hris/punch", who=3, body=punch) for _ in range(2)])
                assert a["data"] == b["data"]
                aid = a["data"]["id"]
                await call("PUT", "/hris/employees/" + employee["id"], body={**profile,
                    "client_request_id": str(uuid4()), "row_version": 1, "is_active": False})
                for path in ("/auth/me", "/auth/access", "/hris/setup", "/products/"):
                    response = await call("GET", path, who=3, status=403)
                    assert response["detail"]["code"] == "EMPLOYEE_INACTIVE"
                await call("POST", "/hris/punch", who=3, status=403, body=punch)
                with patch.object(auth.settings, "DEMO_PHONE", users[3].phone), patch.object(auth.settings, "DEMO_OTP", "123456"):
                    login = await client.post("/api/v1/auth/otp/verify", json={"phone": users[3].phone, "otp": "123456"})
                    assert login.status_code == 403 and login.json()["detail"]["code"] == "EMPLOYEE_INACTIVE"
                pin_login = await client.post("/api/v1/auth/pin/verify", json={"phone": users[3].phone, "pin": "135790"})
                assert pin_login.status_code == 403 and pin_login.json()["detail"]["code"] == "EMPLOYEE_INACTIVE"
                with patch.object(auth, "verify_google_token", AsyncMock(return_value={"project": "qa-project", "uid": "qa-google-user"})):
                    google = await client.post("/api/v1/auth/google", json={"id_token": "qa-token-long-enough-for-schema"})
                    assert google.status_code == 403 and google.json()["detail"]["code"] == "EMPLOYEE_INACTIVE"
                async with Admin() as db:
                    target = await db.get(User, users[3].id)
                    assert target.is_active and not target.is_superuser
                    try:
                        await auth._login_payload(target, db)
                        raise AssertionError("Inactive employee obtained login token")
                    except Exception as error:
                        assert getattr(error, "status_code", None) == 403
                await call("PUT", "/hris/attendance/" + aid, who=6, body={"client_request_id": str(uuid4()),
                    "row_version": 1, "employee_id": employee["id"], "outlet_id": str(outlets[0].id),
                    "work_date": "2026-10-06", "status": "hadir", "clock_in": "2026-10-06T12:00:00Z",
                    "clock_out": "2026-10-06T12:00:00Z", "correction_reason": "Owner confirmed staff left"})
                await call("PUT", "/hris/employees/" + employee["id"], body={**profile,
                    "client_request_id": str(uuid4()), "row_version": 2, "is_active": True})
                await call("GET", "/auth/access", who=3, status=401)
                with patch.object(auth, "verify_google_token", AsyncMock(return_value={"project": "qa-project", "uid": "qa-google-user"})):
                    renewed = await client.post("/api/v1/auth/google", json={"id_token": "qa-token-long-enough-for-schema"})
                    assert renewed.status_code == 200, renewed.text
                    sessions[3] = renewed.json()["data"]["access_token"]
                await call("GET", "/auth/access", who=3)
                print("PASS inactive HRIS revokes existing JWT and login, blocks replay; authorized manager closes attendance")

                async with Admin() as db:
                    role = await db.get(Role, roles[2].id)
                    role.permissions = {"access_policy": {"version": 1, "permissions": {"hris.self": True},
                        "outlet_ids": [str(outlets[0].id)]}}
                    await db.commit()
                denied = await call("POST", "/hris/schedules", who=4, status=403, body=schedule)
                assert denied["detail"]["code"] == "PERMISSION_DENIED"
                async with Admin() as db:
                    assert await db.scalar(select(func.count()).select_from(HrSchedule)) == 1
                    role = await db.get(Role, roles[1].id)
                    role.permissions = {"access_policy": {"version": 1, "permissions": {"hris.self": True},
                        "outlet_ids": [str(outlets[1].id)]}}
                    await db.commit()
                changed = (await call("GET", "/auth/access", who=3))["data"]
                assert changed["access_version"] != managed["access_version"]
                assert [o["id"] for o in changed["outlets"]] == [str(outlets[1].id)]
                await call("POST", "/hris/punch", who=3, status=404, body=punch)
                assert (await call("GET", "/auth/me", who=3))["data"]["outlet_id"] == str(outlets[1].id)
                print("PASS role revocation blocks saved write replay and changed outlet scope blocks attendance replay")

                for method, path, body, params in (
                    ("GET", "/finance/summary", None, {"outlet_id": str(outlets[1].id)}),
                    ("GET", "/customers/workspace", None, None),
                    ("GET", "/purchases/", None, {"outlet_id": str(outlets[1].id)}),
                    ("POST", "/ai/chat", {"outlet_id": str(outlets[1].id), "message": "berapa laba"}, None),
                    ("POST", "/ai/hpp-setup/sessions", {"outlet_id": str(outlets[1].id)}, None),
                    ("POST", "/sync/", {"node_id": "qa", "outlet_id": str(outlets[1].id), "changes": {}}, None),
                    ("POST", "/users/cashier", {"name": "QA", "phone": "628000000001", "pin": "135790"}, None)):
                    result = await call(method, path, who=3, status=403, body=body, params=params)
                    assert result["detail"]["code"] == "ACCESS_ROUTE_NOT_READY"
                legacy = (await call("GET", "/hris/setup", who=2))["data"]
                assert legacy["is_manager"] and len(legacy["outlets"]) == 2
                await call("GET", "/finance/summary", params={"outlet_id": str(outlets[0].id), "month": "2026-10"})
                await call("GET", "/customers/workspace")
                await call("GET", "/purchases/", params={"outlet_id": str(outlets[0].id)})
                await call("GET", "/products/", who=1, params={"outlet_id": str(outlets[0].id)})
                await call("GET", "/recipes/", params={"brand_id": str(brands[0].id)})
                await call("GET", "/ingredients/", params={"brand_id": str(brands[0].id), "outlet_id": str(outlets[0].id)})
                print("PASS managed access blocks unmigrated AI/sync/finance/CRM/account routes; owner and legacy regressions")

                async with Admin() as db:
                    target_role = await db.get(Role, roles[1].id)
                    target_role.scope = "brand"
                    target_role.permissions = {"access_policy": {"version": 1, "permissions": {"hris.self": True},
                        "brand_ids": [str(brands[0].id), str(brands[1].id)]}}
                    await db.commit()
                brand_scope = (await call("GET", "/auth/access", who=3))["data"]
                assert {o["id"] for o in brand_scope["outlets"]} == {str(outlets[0].id), str(outlets[1].id)}
                async with Admin() as db:
                    target_role = await db.get(Role, roles[1].id)
                    target_role.scope = "outlet"
                    target_role.permissions = {"access_policy": {"version": 1, "permissions": {"hris.self": True},
                        "outlet_ids": [str(outlets[2].id)]}}
                    await db.commit()
                empty_scope = (await call("GET", "/auth/access", who=3))["data"]
                assert not empty_scope["outlets"]
                assert (await call("GET", "/auth/me", who=3))["data"]["outlet_id"] is None
                async with Admin() as db:
                    target_role = await db.get(Role, roles[1].id)
                    target_role.permissions = {"hris_manage": True, "access_policy": {"version": 2}}
                    await db.commit()
                invalid = await call("GET", "/auth/access", who=3, status=403)
                assert invalid["detail"]["code"] == "ACCESS_POLICY_INVALID"
                async with Admin() as db:
                    target_role = await db.get(Role, roles[1].id)
                    target_role.deleted_at = datetime.now(timezone.utc)
                    await db.commit()
                missing = await call("GET", "/auth/access", who=3, status=403)
                assert missing["detail"]["code"] == "ROLE_UNAVAILABLE"
                print("PASS brand/empty scope cannot include foreign outlets; malformed and deleted roles fail closed")

                async with AsyncSessionLocal() as db:
                    await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tenants[0].id)})
                    assert not await db.scalar(select(User.id).where(User.id == users[7].id))
                    assert not await db.scalar(select(Role.id).where(Role.id == foreign_role.id))
                    assert not await db.scalar(select(Outlet.id).where(Outlet.id == outlets[2].id))
                    pgrole = (await db.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"))).one()
                    assert not any(pgrole)
                    for table in ("hr_employees", "hr_schedules", "hr_attendance"):
                        assert all((await db.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname=:name"), {"name": table})).one())
                    assert (await db.scalar(select(func.count()).select_from(HrAttendance))) == 1
                    assert await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity == "hris")) == 8
                print("PASS actual non-superuser forced RLS and one attendance result with atomic audits")
    finally:
        svc.now = real_now
        await admin.dispose()
        await engine.dispose()


asyncio.run(main())
