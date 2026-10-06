"""HTTP and PostgreSQL checks against synthetic customer records only."""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Header
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.core.database import get_db
from backend.models import Tenant, User, Brand, Outlet, Product
from backend.models.customer import Customer
from backend.models.crm import CustomerTimeline
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.tab import Tab
from backend.api import deps
from backend.api.routes import customers, crm
from backend.services.crm_service import needs_refresh, refresh_segments

assert settings.POSTGRES_SERVER == 'selaris-customers-qa-db'
assert settings.POSTGRES_APP_USER == 'customer_app'
admin = create_async_engine('postgresql+asyncpg://customer_admin:customer-test-only@selaris-customers-qa-db/customer_qa')
AdminSession = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(customers.router, prefix='/customers')
app.include_router(crm.router, prefix='/crm')
users, outlets, products = [], [], []

@app.middleware('http')
async def request_id(request, call_next):
    request.state.request_id = 'customers-qa'
    return await call_next(request)

async def current_user(x_qa_user: int = Header(default=0), db=Depends(get_db)):
    user = users[x_qa_user]
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(user.tenant_id)})
    return user
app.dependency_overrides[deps.get_current_user] = current_user

async def main():
    async with AdminSession() as db:
        for n in range(2):
            tid = uuid4(); db.add(Tenant(id=tid, name=f'Customer QA {n}', schema_name=f'qa_{tid.hex}')); await db.flush()
            user = User(tenant_id=tid, phone=f'qa-{uuid4().hex}', full_name='QA'); brand = Brand(tenant_id=tid, name='QA', type='cafe')
            db.add_all([user, brand]); await db.flush()
            outlet = Outlet(tenant_id=tid, brand_id=brand.id, name='QA', slug=f'qa-{uuid4().hex}')
            product = Product(brand_id=brand.id, name='QA Kopi', base_price=10)
            db.add_all([outlet, product]); await db.flush()
            users.append(user); outlets.append(outlet); products.append(product)
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://qa') as client:
        payload = {'client_request_id': str(uuid4()), 'name': 'QA%_ Pelanggan', 'phone': '0812 3456-7890', 'wa_marketing_consent': True}
        a, b = await asyncio.gather(*[client.post('/customers/workspace', json=payload) for _ in range(2)])
        assert a.status_code == b.status_code == 200, (a.text, b.text)
        c = a.json()['data']; assert c == b.json()['data']
        changed = await client.post('/customers/workspace', json={**payload, 'name': 'different'})
        assert changed.status_code == 409, changed.text
        for phone in ('081234567890', '+62 (812) 3456 7890'):
            duplicate = await client.post('/customers/workspace', json={**payload, 'client_request_id': str(uuid4()), 'phone': phone})
            assert duplicate.status_code == 409, duplicate.text
        others = await asyncio.gather(*[client.post('/customers/workspace', json={'client_request_id': str(uuid4()), 'name': f'No phone {n}'}) for n in range(2)])
        assert all(r.status_code == 200 for r in others), [r.text for r in others]
        print('PASS concurrent create/replay, fingerprint conflict, canonical phone duplicate, multiple contacts without phones')
        for n in range(2):
            response = await client.post('/customers/', json={'name': f'Legacy no phone {n}'}, headers={'x-qa-user': '1'})
            assert response.status_code == 200, response.text
        response = await client.post('/customers/', json={'name': 'Legacy international QA', 'phone': '+1 (415) 555-0123'}, headers={'x-qa-user': '1'})
        assert response.status_code == 200, response.text
        print('PASS POS legacy endpoint can add multiple customers without phones')
        cid = c['id']
        detail = (await client.get(f'/customers/workspace/{cid}')).json()['data']
        assert detail['phone'] == '6281234567890' and detail['wa_marketing_consent'] and detail['consent_given_at']
        edit = {**payload, 'client_request_id': str(uuid4()), 'row_version': detail['row_version'], 'email': 'qa@example.com', 'notes': 'Preferensi QA', 'birthday': '1995-01-01'}
        race = await asyncio.gather(*[client.put(f'/customers/workspace/{cid}', json={**edit, 'client_request_id': str(uuid4()), 'name': f'QA%_ edit {n}'}) for n in range(2)])
        assert sorted(r.status_code for r in race) == [200, 409], [r.text for r in race]
        detail = (await client.get(f'/customers/workspace/{cid}')).json()['data']
        edit.update(client_request_id=str(uuid4()), row_version=detail['row_version'], wa_marketing_consent=False)
        a, b = await asyncio.gather(*[client.put(f'/customers/workspace/{cid}', json=edit) for _ in range(2)])
        assert a.status_code == b.status_code == 200 and a.json()['data'] == b.json()['data'], (a.text, b.text)
        note = {'client_request_id': str(uuid4()), 'body': 'Keluhan fixture', 'kind': 'complaint'}
        a, b = await asyncio.gather(*[client.post(f'/customers/workspace/{cid}/notes', json=note) for _ in range(2)])
        assert a.status_code == b.status_code == 200 and a.json()['data'] == b.json()['data'], (a.text, b.text)
        async with AdminSession() as db:
            assert await db.scalar(select(func.count(CustomerTimeline.id)).where(CustomerTimeline.customer_id == cid, CustomerTimeline.kind == 'complaint')) == 1
        print('PASS edit locks/version conflicts, profile and note replay, consent timestamp and a single complaint')
        for path in (f'/customers/workspace/{cid}',):
            response = await client.get(path, headers={'x-qa-user': '1'}); assert response.status_code == 404
        response = await client.put(f'/customers/workspace/{cid}', headers={'x-qa-user': '1'}, json=edit); assert response.status_code == 404
        response = await client.post(f'/customers/workspace/{cid}/notes', headers={'x-qa-user': '1'}, json={**note, 'client_request_id': str(uuid4())}); assert response.status_code == 404
        other = await client.get('/customers/workspace', headers={'x-qa-user': '1'}); assert other.json()['data']['total'] == 3
        for changes in ({'name': ' '}, {'phone': 'invalid'}, {'email': 'x@'}, {'birthday': '2999-01-01'}, {'wa_marketing_consent': True, 'phone': None}):
            response = await client.post('/customers/workspace', json={**payload, 'client_request_id': str(uuid4()), **changes})
            assert response.status_code in (400, 422), response.text
        print('PASS RLS/explicit tenant ownership, invalid names/contact/birthday/consent')
        async with AdminSession() as db:
            now = datetime.now(timezone.utc)
            paid_tab = Tab(outlet_id=outlets[0].id, status='paid', tab_number=f'QA-{uuid4()}', opened_at=now)
            pending_tab = Tab(outlet_id=outlets[0].id, status='open', tab_number=f'QA-{uuid4()}', opened_at=now)
            db.add_all([paid_tab, pending_tab]); await db.flush()
            order_ids = []
            for n in range(26):
                order = Order(outlet_id=outlets[0].id, customer_id=cid, order_number=f'QA-{cid}-{n}', display_number=n+1,
                    status='completed' if n != 23 else 'cancelled', total_amount='10.25', subtotal='10.25',
                    tab_id=paid_tab.id if n in (20,21) else pending_tab.id if n == 22 else None,
                    created_at=now - timedelta(days=n))
                db.add(order); await db.flush(); order_ids.append(order.id)
                db.add(OrderItem(order_id=order.id, product_id=products[0].id, quantity=2, unit_price='5.125', total_price='10.25'))
                if n not in (20,21,24):
                    db.add(Payment(outlet_id=outlets[0].id, order_id=order.id, payment_method='cash', amount_due='10.25', amount_paid='10.25', status='refunded' if n == 25 else 'paid'))
            # Deliberately stale cached counters must not affect the dashboard.
            cust = await db.get(Customer, cid); cust.total_visits = 999; cust.total_spent = 99999
            cust.segment_updated_at = None
            await db.commit()
            assert await needs_refresh(db, users[0].tenant_id)
        response = await client.get(f'/customers/workspace/{cid}'); assert response.status_code == 200, response.text
        detail = response.json()['data']
        assert detail['total_visits'] == 22 and detail['total_spent'] == '225.50', detail
        assert len(detail['orders']) == 20 and detail['favourites'][0]['qty'] == 44
        assert len((await client.get(f'/customers/workspace/{cid}?skip=20')).json()['data']['orders']) == 2
        listing = (await client.get('/customers/workspace')).json()['data']
        assert listing['summary']['spent'] == '225.50' and listing['summary']['repeat'] == 1
        filtered = (await client.get('/customers/workspace?search=%25_')).json()['data']
        assert filtered['total'] == 1 and filtered['summary'] == listing['summary']
        for phone in ('0812', '+62 (812)'):
            found = (await client.get('/customers/workspace', params={'search': phone})).json()['data']
            assert found['total'] == 1
        no_match = (await client.get('/customers/workspace?search=absent')).json()['data']
        assert no_match['total'] == 0 and no_match['summary']['total'] == 3
        unspent = (await client.get('/customers/workspace?segment=unspent')).json()['data']; assert unspent['total'] == 2
        first = (await client.get('/customers/workspace?sort=name&limit=1')).json()['data']
        second = (await client.get('/customers/workspace?sort=name&limit=1&skip=1')).json()['data']
        assert first['items'][0]['id'] != second['items'][0]['id']
        assert (await client.get('/customers/workspace?skip=-1')).status_code == 422
        print('PASS fresh Decimal facts, paid tab orders; pending tab anchors/cancelled/unpaid/refunded excluded; all-history favourites, pagination, literal search, stable global summary')
        # A new transaction appears without touching cached counters or requiring refresh-stats.
        async with AdminSession() as db:
            db.add(Payment(outlet_id=outlets[0].id, order_id=order_ids[24], payment_method='cash', amount_due='10.25', amount_paid='10.25', status='paid'))
            await db.commit()
        detail = (await client.get(f'/customers/workspace/{cid}')).json()['data']
        assert detail['total_visits'] == 23 and detail['total_spent'] == '235.75'
        print('PASS newly settled transaction visible immediately without cached refresh')
        async with AdminSession() as db:
            from sqlalchemy import update
            await db.execute(update(Customer).where(Customer.tenant_id == users[0].tenant_id).values(segment_updated_at=datetime.now(timezone.utc)))
            await db.commit()
            assert not await needs_refresh(db, users[0].tenant_id)
            await db.execute(update(Customer).where(Customer.id == cid).values(segment_updated_at=None))
            await db.commit()
            assert await needs_refresh(db, users[0].tenant_id)
        legacy_edit = await client.put(f'/customers/{cid}', json={'name': 'Legacy edit QA', 'row_version': detail['row_version']})
        assert legacy_edit.status_code == 200, legacy_edit.text
        stale_edit = await client.put(f'/customers/workspace/{cid}', json={**edit, 'client_request_id': str(uuid4()), 'row_version': detail['row_version']})
        assert stale_edit.status_code == 409, stale_edit.text
        print('PASS a single missing segment timestamp triggers refresh; legacy profile edits invalidate a stale workspace edit')
        fresh = (await client.get(f'/customers/workspace/{cid}')).json()['data']
        profile = await client.put(f'/crm/customers/{cid}/profile', json={'birthday': '1995-02-02', 'row_version': fresh['row_version']})
        assert profile.status_code == 200, profile.text
        stale = await client.put(f'/crm/customers/{cid}/profile', json={'birthday': '1995-03-03', 'row_version': fresh['row_version']})
        assert stale.status_code == 409, stale.text
        async with AdminSession() as db:
            unspent_customer = await db.scalar(select(Customer).where(Customer.tenant_id == users[0].tenant_id, Customer.name == 'No phone 0'))
            unspent_customer.favorite_product_id = products[0].id
            await db.flush()
            await refresh_segments(db, users[0].tenant_id)
            await db.commit()
            assert unspent_customer.favorite_product_id is None
        print('PASS legacy CRM profile honors versions; outdated favourite clears when no recent paid purchases exist')
    await admin.dispose()

asyncio.run(main())
