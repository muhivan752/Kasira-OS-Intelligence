"""Synthetic finance API tests on a schema-only QA database with non-superuser RLS."""
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import FastAPI, Depends, Header
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.core.database import get_db, AsyncSessionLocal
from backend.models import Tenant, User, Brand, Outlet, Event
from backend.models.finance import Expense, CashAccount
from backend.models.purchasing import PurchaseOrder, Supplier
from backend.api import deps
from backend.api.routes import finance, purchasing
from backend.services.finance_context import build_finance_context

assert settings.POSTGRES_SERVER == 'selaris-finance-qa-db'
assert settings.POSTGRES_APP_USER == 'finance_app'
admin = create_async_engine('postgresql+asyncpg://finance_admin:finance-test-only@selaris-finance-qa-db/finance_qa')
AdminSession = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(finance.router, prefix='/finance')
app.include_router(purchasing.purchases_router, prefix='/purchases')
users, outlets, suppliers, accounts, notes = [], [], [], [], []


@app.middleware('http')
async def request_id(request, call_next):
    request.state.request_id = 'finance-qa'
    return await call_next(request)


async def current_user(x_qa_user: int = Header(default=0), db=Depends(get_db)):
    user = users[x_qa_user]
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(user.tenant_id)})
    return user


app.dependency_overrides[deps.get_current_user] = current_user


def when(month, day=1):
    return datetime(2026, month, day, tzinfo=timezone.utc)


async def main():
    async with AdminSession() as db:
        for n in range(3):
            tid = uuid4()
            db.add(Tenant(id=tid, name=f'Finance QA {n}', schema_name=f'qa_{tid.hex}', subscription_tier='pro'))
            await db.flush()
            brand = Brand(tenant_id=tid, name=f'QA {n}', type='cafe')
            user = User(tenant_id=tid, phone=f'qa-{uuid4().hex}', full_name='QA')
            db.add_all([brand, user]); await db.flush()
            outlet = Outlet(tenant_id=tid, brand_id=brand.id, name='QA', slug=f'qa-{uuid4().hex}')
            supplier = Supplier(tenant_id=tid, name='QA supplier')
            db.add_all([outlet, supplier]); await db.flush()
            account = CashAccount(tenant_id=tid, name='Bank', kind='bank', default_for=['transfer'], is_active=True)
            if n < 2:
                db.add(account); await db.flush()
            users.append(user); outlets.append(outlet); suppliers.append(supplier); accounts.append(account)
            po = PurchaseOrder(outlet_id=outlet.id, supplier_id=supplier.id, po_number=f'QA-{n}', status='received', total_amount=1000,
                               paid_amount=1000, received_at=when(9, 30))
            db.add(po); await db.flush(); notes.append(po)
            for kind, timestamp, payload in [('received', when(9, 30), {'paid': '100'}),
                                              ('paid', when(10), {'amount': '300', 'paid_after': '400'}),
                                              ('paid', when(11), {'amount': '9999', 'paid_after': '1000'})]:
                db.add(Event(outlet_id=outlet.id, stream_id=f'purchase:{po.id}', event_type=f'purchase.{kind}', event_data=payload, created_at=timestamp))
        db.add(Expense(tenant_id=users[0].tenant_id, outlet_id=outlets[0].id, category='listrik_air', amount=Decimal('25.50'),
                       paid_at=when(10), payment_method='transfer', cash_account_id=accounts[0].id))
        db.add(Expense(tenant_id=users[0].tenant_id, outlet_id=outlets[0].id, category='perlengkapan', amount=Decimal('50'),
                       paid_at=when(10), payment_method='cash', purchase_id=notes[0].id))
        db.add(Expense(tenant_id=users[0].tenant_id, outlet_id=outlets[0].id, category='selisih_stok', amount=Decimal('10'),
                       paid_at=when(10), payment_method='none'))
        db.add(PurchaseOrder(outlet_id=outlets[0].id, po_number='QA-due', status='received', total_amount=200, paid_amount=0,
                             received_at=when(9), due_at=when(9, 2)))
        await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://qa') as client:
        seeded = await asyncio.gather(*[client.get('/finance/accounts', headers={'x-qa-user': '2'}) for _ in range(2)])
        assert all(s.status_code == 200 for s in seeded), [s.text for s in seeded]
        assert {a['id'] for a in seeded[0].json()['data']} == {a['id'] for a in seeded[1].json()['data']}
        assert len(seeded[0].json()['data']) == 3
        early = await client.get('/finance/summary', params={'outlet_id': str(outlets[0].id), 'month': '2000-01'})
        assert early.status_code == 200, early.text
        print('PASS simultaneous first-use account setup creates only 3 accounts and earliest selectable month works')
        for month, expected in [('2026-09', '100.00'), ('2026-10', '300.00'), ('2026-11', '600.00')]:
            response = await client.get('/finance/summary', params={'outlet_id': str(outlets[0].id), 'month': month})
            assert response.status_code == 200, response.text
            data = response.json()['data']
            assert data['purchases_paid'] == expected, data
            if month == '2026-10':
                assert data['cash_out'] == '325.50' and data['net_profit'] == '-85.50', data
                assert data['payables_outstanding'] == data['payables_overdue'] == '200.00'
                assert data['cash_history_estimated'] is False
                assert any(a['id'] is None and a['outflow'] == '300.00' for a in data['accounts'])
        print('PASS real SQL summary: payment months, old overpayment, purchase expense not doubled, noncash excluded, overdue and unassigned account')

        other = await client.get('/finance/summary', params={'outlet_id': str(outlets[1].id), 'month': '2026-10'})
        assert other.status_code == 404, other.text
        invalid = await client.get('/finance/summary', params={'outlet_id': str(outlets[0].id), 'month': '2026-13'})
        assert invalid.status_code == 400, invalid.text

        payload = {'outlet_id': str(outlets[0].id), 'category': 'listrik_air', 'amount': '12.34', 'payment_method': 'transfer',
                   'cash_account_id': str(accounts[0].id), 'note': 'QA idempotency', 'client_request_id': str(uuid4())}
        a, b = await asyncio.gather(client.post('/finance/expenses', json=payload), client.post('/finance/expenses', json=payload))
        assert a.status_code == b.status_code == 200, (a.text, b.text)
        saved = a.json()['data']
        assert saved['id'] == b.json()['data']['id'] and saved['amount'] == '12.34'
        reused = await client.post('/finance/expenses', json={**payload, 'amount': '99'})
        assert reused.status_code == 409, reused.text
        print('PASS concurrent request replay: one expense, changed payload rejected')

        for key, value in [('cash_account_id', str(accounts[1].id)), ('supplier_id', str(suppliers[1].id))]:
            r = await client.post('/finance/expenses', json={**payload, 'client_request_id': str(uuid4()), key: value})
            assert r.status_code in (400, 404), r.text
        for patch in [{'payment_method': 'bad'}, {'category': None}, {'paid_at': None}, {'amount': '1.001'}]:
            r = await client.put(f"/finance/expenses/{saved['id']}", json={'row_version': 0, **patch})
            assert r.status_code == 422, r.text
        r = await client.put(f"/finance/expenses/{saved['id']}", json={'row_version': 0, 'amount': '13.35', 'cash_account_id': str(accounts[1].id)})
        assert r.status_code == 400, r.text
        a, b = await asyncio.gather(*[client.put(f"/finance/expenses/{saved['id']}", json={'row_version': 0, 'amount': value}) for value in ['13.35', '14.36']])
        assert sorted([a.status_code, b.status_code]) == [200, 409], (a.text, b.text)
        print('PASS tenant references, validation and concurrent edit conflict')

        async with AdminSession() as db:
            count = (await db.execute(select(func.count(Expense.id)).where(Expense.note == 'QA idempotency',
                Expense.tenant_id == users[0].tenant_id))).scalar()
            assert count == 1
            db.add(PurchaseOrder(outlet_id=outlets[0].id, po_number='QA-legacy', status='received', total_amount=200, paid_amount=200, received_at=when(10)))
            for _ in range(2):
                db.add(Expense(tenant_id=users[0].tenant_id, outlet_id=outlets[0].id, category='sewa', note='QA monthly',
                               amount=100, paid_at=when(9), payment_method='transfer', cash_account_id=accounts[0].id, recurring='monthly'))
            await db.commit()
        response = await client.get('/finance/summary', params={'outlet_id': str(outlets[0].id), 'month': '2026-10'})
        assert response.json()['data']['cash_history_estimated'] is True
        copies = await asyncio.gather(*[client.post('/finance/expenses/copy-recurring', params={'outlet_id': str(outlets[0].id), 'month': '2026-10'}) for _ in range(2)])
        assert all(c.status_code == 200 for c in copies), [c.text for c in copies]
        assert sum(len(c.json()['data']) for c in copies) == 1
        print('PASS legacy estimate label and recurring templates cannot double-copy')

        async with AdminSession() as db:
            po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == 'QA-due'))).scalar_one()
            po.paid_amount = Decimal('100'); po.row_version = 0; pay_id = po.id; await db.commit()
        paid = await client.post(f'/purchases/{pay_id}/pay', json={'amount': '9999', 'row_version': 0})
        assert paid.status_code == 200, paid.text
        async with AdminSession() as db:
            evt = (await db.execute(select(Event).where(Event.stream_id == f'purchase:{pay_id}', Event.event_data['paid_before'].astext == '100.00'))).scalar_one()
            assert evt.event_data['amount'] == '100.00' and evt.event_data['paid_after'] == '200.00', evt.event_data
        print('PASS new payment event records actual capped amount and prior paid balance')
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(users[0].tenant_id)})
            context = await build_finance_context('laba dan kas 2026-10', outlets[0].id, users[0].tenant_id, db)
            facts = json.loads(context.splitlines()[3])
            assert facts['month'] == '2026-10' and facts['outlet_id'] == str(outlets[0].id)
            assert 'PERUBAHAN' in context and 'jangan mengaku mencatat pengeluaran' in context
            assert facts['cash_history_estimated'] is True
            unavailable = await build_finance_context('laba 2026-10', outlets[1].id, users[0].tenant_id, db)
            assert 'Jangan menjawab angka keuangan dari cache' in unavailable
            assert (await db.execute(text('SELECT 1'))).scalar() == 1
        print('PASS fresh scoped assistant facts, explicit limits and unavailable data cannot reuse cached numbers')
    print('ALL FINANCE ISOLATED CHECKS PASSED')


asyncio.run(main())
