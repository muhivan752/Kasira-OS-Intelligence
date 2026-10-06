"""HRIS HTTP, role, concurrency and forced-RLS checks on synthetic records."""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Header
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api import deps
from backend.api.routes import hris
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, get_db
from backend.models import AuditLog, Brand, HrAttendance, HrEmployee, HrSchedule, Outlet, Role, Tenant, User
from backend.services import hris as svc

assert settings.POSTGRES_SERVER == 'selaris-hris-qa-db'
assert settings.POSTGRES_APP_USER == 'hris_app'
admin = create_async_engine('postgresql+asyncpg://hris_admin:hris-test-only@selaris-hris-qa-db/hris_qa')
Admin = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI(); app.include_router(hris.router, prefix='/hris')
users, outlets = [], []

@app.middleware('http')
async def request_id(request, call_next):
    request.state.request_id = 'hris-qa'
    return await call_next(request)

async def user(x_qa_user: int = Header(default=0), db=Depends(get_db)):
    current = users[x_qa_user]
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(current.tenant_id)})
    return current
app.dependency_overrides[deps.get_current_user] = user

async def main():
    async with Admin() as db:
        for n in range(2):
            tid = uuid4(); db.add(Tenant(id=tid, name=f'HR QA {n}', schema_name=f'qa_{tid.hex}')); await db.flush()
            brand = Brand(tenant_id=tid, name='QA', type='cafe'); db.add(brand); await db.flush()
            team = [User(tenant_id=tid, phone=f'qa-{uuid4().hex}', full_name=f'QA {n}/{i}', is_superuser=i == 0) for i in range(3)]
            role = Role(tenant_id=tid, name='QA pengelola', scope='tenant', permissions={'hris_manage': True}); db.add(role); await db.flush()
            team[2].role_id = role.id; db.add_all(team); users.extend(team)
            for i in range(2):
                out = Outlet(tenant_id=tid, brand_id=brand.id, name=f'QA {n}/{i}', slug=f'qa-{uuid4().hex}', timezone='Asia/Jayapura' if i else 'Asia/Jakarta')
                db.add(out); outlets.append(out)
        await db.commit()
    real_now = svc.now
    fixed = datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc)
    svc.now = lambda: fixed
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://qa') as client:
        async def send(path, body, status=200, who=0, method='post'):
            r = await getattr(client, method)('/hris' + path, json=body, headers={'x-qa-user': str(who)})
            assert r.status_code == status, (path, status, r.status_code, r.text)
            return r.json().get('data')
        profile = {'client_request_id': str(uuid4()), 'name': 'QA%_ karyawan', 'position': 'Kasir',
            'outlet_id': str(outlets[0].id), 'user_id': str(users[1].id), 'started_on': '2025-01-01', 'notes': 'PRIVATE MANAGER NOTE', 'phone': '081234567890'}
        a, b = await asyncio.gather(*[send('/employees', profile) for _ in range(2)])
        assert a == b; eid = a['id']
        await send('/employees', {**profile, 'name': 'changed'}, 409)
        await send('/employees', {**profile, 'client_request_id': str(uuid4())}, 409)
        await send('/employees', profile, 403, 1)
        await send('/employees', {**profile, 'client_request_id': str(uuid4()), 'outlet_id': str(outlets[2].id)}, 404)
        await send('/employees', {**profile, 'client_request_id': str(uuid4()), 'user_id': str(users[4].id)}, 404)
        other_payload = {**profile, 'client_request_id': str(uuid4()), 'name': 'QA second', 'user_id': None}
        other = await send('/employees', other_payload, who=2)
        other_tenant = await send('/employees', {**profile, 'client_request_id': str(uuid4()), 'user_id': str(users[4].id), 'outlet_id': str(outlets[2].id)}, who=3)
        setup = (await client.get('/hris/setup', headers={'x-qa-user': '1'})).json()['data']
        assert not setup['is_manager'] and not setup['accounts'] and setup['self_employee']['notes'] is None
        assert setup['self_employee']['phone'] is None and setup['self_employee']['id'] == eid
        params = {'outlet_id': str(outlets[0].id), 'start': '2026-10-06', 'end': '2026-10-07'}
        self_list = (await client.get('/hris/workspace', params=params, headers={'x-qa-user': '1'})).json()['data']
        assert self_list['total'] == 1 and self_list['items'][0]['id'] == eid
        assert (await client.get('/hris/employee-choices', headers={'x-qa-user': '1'})).status_code == 403
        print('PASS concurrent employee replay, account uniqueness, manager role and self-only privacy; cross-tenant outlet/account denial')
        edited = await send('/employees/' + eid, {**profile, 'client_request_id': str(uuid4()), 'row_version': 1, 'position': 'Senior'}, method='put')
        await send('/employees/' + eid, {**profile, 'client_request_id': str(uuid4()), 'row_version': 1}, 409, method='put')
        await send('/employees/' + other_tenant['id'], {**profile, 'client_request_id': str(uuid4()), 'row_version': 1}, 404, method='put')
        schedule = {'client_request_id': str(uuid4()), 'employee_id': eid, 'outlet_id': str(outlets[0].id),
                    'starts_at': '2026-10-06T16:00:00Z', 'ends_at': '2026-10-07T00:00:00Z'}
        saved = await send('/schedules', schedule)
        await send('/schedules', {**schedule, 'client_request_id': str(uuid4()), 'outlet_id': str(outlets[1].id), 'starts_at': '2026-10-06T16:30:00Z'}, 409)
        racing = await asyncio.gather(*[client.post('/hris/schedules', json={**schedule, 'client_request_id': str(uuid4()), 'employee_id': other['id']}) for _ in range(2)])
        assert sorted(r.status_code for r in racing) == [200, 409]
        punch = {'client_request_id': str(uuid4()), 'action': 'in', 'outlet_id': str(outlets[0].id)}
        a, b = await asyncio.gather(*[send('/punch', punch, who=1) for _ in range(2)])
        assert a == b
        await send('/punch', {**punch, 'client_request_id': str(uuid4())}, 409, 1)
        await send('/punch', {**punch, 'client_request_id': str(uuid4())}, 403, 2)
        att_id = a['id']
        attendance = (await client.get('/hris/workspace', params={**params, 'kind': 'attendance'})).json()['data']
        assert attendance['items'][0]['work_date'] == '2026-10-06' and attendance['items'][0]['source'] == 'self'
        assert attendance['summary']['open'] == 1 and attendance['summary']['unrecorded_started'] == 1
        await send('/employees/' + eid, {**profile, 'client_request_id': str(uuid4()), 'row_version': edited['row_version'], 'user_id': None}, 409, method='put')
        await send('/schedules/' + saved['id'] + '/void', {'client_request_id': str(uuid4()), 'row_version': 1, 'reason': 'QA'}, 409)
        await send('/employees/' + eid, {**profile, 'client_request_id': str(uuid4()), 'row_version': edited['row_version'], 'is_active': False}, method='put')
        fixed = datetime(2026, 10, 7, 1, 0, tzinfo=timezone.utc)
        await send('/punch', {'client_request_id': str(uuid4()), 'action': 'out', 'outlet_id': str(outlets[0].id)}, 403, 1)
        closed = await send('/attendance/' + att_id, {'client_request_id': str(uuid4()), 'employee_id': eid,
            'outlet_id': str(outlets[0].id), 'work_date': '2026-10-06', 'status': 'hadir',
            'clock_in': '2026-10-06T17:30:00Z', 'clock_out': '2026-10-07T01:00:00Z',
            'row_version': 1, 'correction_reason': 'Pengelola menutup absensi pegawai nonaktif'}, method='put')
        assert closed['id'] == att_id
        attendance = (await client.get('/hris/workspace', params={**params, 'kind': 'attendance'})).json()['data']
        assert attendance['items'][0]['minutes'] == 450 and attendance['items'][0]['work_date'] == '2026-10-06'
        await send('/attendance/' + att_id, {'client_request_id': str(uuid4()), 'employee_id': eid,
            'outlet_id': str(outlets[0].id), 'work_date': '2026-10-06', 'status': 'hadir',
            'clock_in': '2026-10-06T17:30:00Z', 'clock_out': '2026-10-07T00:55:00Z',
            'row_version': 2, 'correction_reason': 'Koreksi jadwal malam QA'}, method='put')
        corrected_night = (await client.get('/hris/workspace', params={**params, 'kind': 'attendance'})).json()['data']['items'][0]
        assert corrected_night['work_date'] == '2026-10-06' and corrected_night['minutes'] == 445
        await send('/punch', {**punch, 'client_request_id': str(uuid4())}, 403, 1)
        await send('/punch', {'client_request_id': str(uuid4()), 'action': 'out', 'outlet_id': str(outlets[0].id)}, 403, 1)
        print('PASS overnight schedule/day and self punch replay, closed duration, inactive staff denied with manager closure; attendance prevents schedule cancellation')
        manual = {'client_request_id': str(uuid4()), 'employee_id': other['id'], 'outlet_id': str(outlets[0].id),
            'work_date': '2026-10-06', 'status': 'izin', 'reason': 'Dikonfirmasi QA'}
        m = await send('/attendance', manual)
        await send('/attendance', {**manual, 'client_request_id': str(uuid4())}, 409)
        await send('/attendance/' + m['id'], {**manual, 'client_request_id': str(uuid4()), 'row_version': 1}, 422, method='put')
        corrected = {**manual, 'client_request_id': str(uuid4()), 'row_version': 1, 'status': 'sakit', 'correction_reason': 'Koreksi konfirmasi QA'}
        first, second = await asyncio.gather(*[send('/attendance/' + m['id'], corrected, method='put') for _ in range(2)])
        assert first == second
        await send('/attendance/' + m['id'], {**corrected, 'client_request_id': str(uuid4()), 'row_version': 1}, 409, method='put')
        cancelled = {'client_request_id': str(uuid4()), 'row_version': 2, 'reason': 'Salah tanggal QA'}
        first, second = await asyncio.gather(*[send('/attendance/' + m['id'] + '/void', cancelled) for _ in range(2)])
        assert first == second
        await send('/attendance', {**manual, 'client_request_id': str(uuid4())})
        await send('/attendance', {**manual, 'client_request_id': str(uuid4()), 'work_date': '2026-10-08', 'status': 'hadir', 'clock_in': '2026-10-08T00:00:00Z'}, 422)
        await send('/attendance', {**manual, 'client_request_id': str(uuid4()), 'employee_id': other_tenant['id']}, 404)
        assert (await client.get('/hris/workspace', params={**params, 'end': '2026-12-06'})).status_code == 422
        literal = (await client.get('/hris/workspace', params={**params, 'search': '%_'})).json()['data']
        assert literal['total'] == 1 and literal['summary']['scheduled'] == 2
        page = (await client.get('/hris/workspace', params={**params, 'limit': 1})).json()['data']
        next_page = (await client.get('/hris/workspace', params={**params, 'limit': 1, 'skip': 1})).json()['data']
        assert page['items'][0]['id'] != next_page['items'][0]['id']
        print('PASS manual leave, correction/void atomic replay and versions; daily uniqueness, future presence rejection, literal search, pagination and period bounds')
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(users[0].tenant_id)})
        assert not await db.scalar(select(HrEmployee.id).where(HrEmployee.id == other_tenant['id']))
        policy = (await db.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='hr_attendance'"))).one()
        assert all(policy)
        db.add(HrAttendance(tenant_id=users[0].tenant_id, employee_id=other_tenant['id'], outlet_id=outlets[0].id,
            work_date=fixed.date(), status='izin', source='manual', recorded_by=users[0].id, updated_by=users[0].id))
        try:
            await db.flush(); raise AssertionError('Cross-tenant employee FK accepted')
        except IntegrityError:
            await db.rollback()
        await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(users[0].tenant_id)})
        db.add(HrEmployee(tenant_id=users[3].tenant_id, outlet_id=outlets[2].id, name='Forbidden', position='QA', code='FORBIDDEN', started_on=fixed.date()))
        try:
            await db.flush(); raise AssertionError('Cross-tenant write accepted')
        except DBAPIError as error:
            assert error.orig.sqlstate == '42501'
            await db.rollback()
    async with Admin() as db:
        assert await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity == 'hris')) >= 10
        assert not (await db.get(User, users[1].id)).is_superuser
        assert (await db.get(User, users[1].id)).is_active
        role = await db.get(Role, users[2].role_id); role.permissions = {}; await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://qa') as client:
        denied = await client.post('/hris/employees', json={**profile, 'client_request_id': str(uuid4()), 'user_id': None}, headers={'x-qa-user': '2'})
        assert denied.status_code == 403
        denied_replay = await client.post('/hris/employees', json=other_payload, headers={'x-qa-user': '2'})
        assert denied_replay.status_code == 403
    svc.now = real_now
    print('PASS forced RLS and composite employee tenant FK; audit history and cashier account unchanged')
    await admin.dispose()

asyncio.run(main())
