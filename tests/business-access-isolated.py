"""HTTP/JWT and forced-RLS checks; schema-only database, synthetic data, no providers."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.api.api import api_router
from backend.core.config import settings
from backend.core.database import engine, AsyncSessionLocal
from backend.core.security import create_access_token
from backend.models import Tenant, Brand, Outlet, User, Role, Product, Ingredient, Recipe, RecipeIngredient, Order, OrderItem, Payment
from backend.models.finance import Expense, CashAccount
from backend.models.purchasing import Supplier, PurchaseOrder, PurchaseOrderItem
from backend.models.customer import Customer
from backend.models.audit_log import AuditLog
from backend.models.hris import HrEmployee
from backend.services.access import resolve_access

assert settings.POSTGRES_SERVER == 'selaris-business-qa-db'
assert settings.POSTGRES_APP_USER == 'business_app'
assert not any((settings.ANTHROPIC_API_KEY, settings.XENDIT_API_KEY, settings.FONNTE_TOKEN, settings.FCM_PRIVATE_KEY))
admin = create_async_engine('postgresql+asyncpg://business_admin:business-test-only@selaris-business-qa-db/business_qa')
Admin = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(api_router, prefix='/api/v1')


@app.middleware('http')
async def request_id(request, next_handler):
    request.state.request_id = 'synthetic-business-access-qa'
    return await next_handler(request)


async def main():
    now = datetime.now(timezone.utc)
    month = now.astimezone(__import__('zoneinfo').ZoneInfo('Asia/Jakarta')).strftime('%Y-%m')
    async with Admin() as db:
        tenants = [Tenant(id=uuid4(), name='Synthetic business access QA', schema_name='qa_' + uuid4().hex,
                          subscription_tier='pro', subscription_status='active') for _ in range(2)]
        db.add_all(tenants); await db.flush()
        tid = tenants[0].id
        brands = [Brand(id=uuid4(), tenant_id=t, name='Synthetic brand', type='cafe') for t in (tid, tid, tenants[1].id)]
        db.add_all(brands); await db.flush()
        outlets = [Outlet(id=uuid4(), tenant_id=b.tenant_id, brand_id=b.id, name='Synthetic outlet ' + str(i),
                          slug='qa-' + uuid4().hex) for i, b in enumerate([brands[0], brands[1], brands[0], brands[2]])]
        db.add_all(outlets); await db.flush()
        grants = {
            'none': ['hris.self'], 'finance': ['finance.view'], 'finwriter': ['finance.view', 'finance.manage'],
            'purchase': ['purchasing.view'], 'priced': ['purchasing.view', 'supplier.price.view'],
            'buyer': ['purchasing.view', 'purchasing.manage', 'supplier.price.view'],
            'receiver': ['purchasing.view', 'purchasing.manage', 'supplier.price.view', 'stock.receive'],
            'customer': ['customers.view'], 'crmwriter': ['customers.view', 'customers.manage'],
            'exporter': ['customers.view', 'customers.export'], 'hpp': ['hpp.view'],
            'drafter': ['hpp.view', 'hpp.manage'], 'approver': ['hpp.view', 'hpp.approve'],
            'hppwriter': ['hpp.view', 'hpp.manage', 'hpp.approve', 'supplier.price.view'],
            'tenantfinance': ['finance.view', 'finance.manage'],
        }
        users, roles = {}, {}
        for name, permissions in grants.items():
            scope = 'tenant' if name == 'tenantfinance' else 'outlet'
            role = Role(id=uuid4(), tenant_id=tid, name='QA ' + name, scope=scope,
                        permissions={'access_policy': {'version': 1, 'permissions': {p: True for p in permissions},
                         'outlet_ids': [] if scope == 'tenant' else [str(outlets[0].id)]}})
            db.add(role); await db.flush(); roles[name] = role
            users[name] = User(id=uuid4(), tenant_id=tid, phone='qa-' + uuid4().hex, full_name='Synthetic staff', role_id=role.id)
        users['owner'] = User(id=uuid4(), tenant_id=tid, phone='qa-' + uuid4().hex, full_name='QA owner', is_superuser=True)
        users['legacy'] = User(id=uuid4(), tenant_id=tid, phone='qa-' + uuid4().hex, full_name='QA legacy')
        db.add_all(users.values()); await db.flush()
        products = [Product(id=uuid4(), brand_id=b.id, name='Synthetic product', base_price=1000, buy_price=200,
                            stock_enabled=True, stock_qty=50) for b in brands]
        ingredients = [Ingredient(id=uuid4(), brand_id=b.id, name='Synthetic flour', tracking_mode='simple',
                        base_unit='gram', unit_type='WEIGHT', buy_price=5000, buy_qty=100, cost_per_base_unit=50) for b in brands]
        db.add_all(products + ingredients); await db.flush()
        recipes = [Recipe(id=uuid4(), product_id=p.id, is_active=True) for p in products]
        db.add_all(recipes); await db.flush()
        db.add_all([RecipeIngredient(recipe_id=r.id, ingredient_id=i.id, quantity=2, quantity_unit='gram') for r, i in zip(recipes, ingredients)])
        customer = Customer(id=uuid4(), tenant_id=tid, name='Synthetic shared contact', phone='', phone_hmac=uuid4().hex)
        foreign_customer = Customer(id=uuid4(), tenant_id=tenants[1].id, name='Foreign contact', phone='', phone_hmac=uuid4().hex)
        supplier = Supplier(id=uuid4(), tenant_id=tid, name='Synthetic shared supplier')
        foreign_supplier = Supplier(id=uuid4(), tenant_id=tenants[1].id, name='Foreign supplier')
        db.add_all([customer, foreign_customer, supplier, foreign_supplier]); await db.flush()
        accounts = [CashAccount(id=uuid4(), tenant_id=tid, outlet_id=oid, name=name, kind='cash_drawer',
                    default_for=['cash'], opening_balance=99999) for oid, name in
                    [(None, 'Shared cash'), (outlets[0].id, 'Permitted cash'), (outlets[1].id, 'Forbidden cash')]]
        db.add_all(accounts); await db.flush()
        expenses = [Expense(id=uuid4(), tenant_id=tid, outlet_id=oid, amount=amount, category='sewa', paid_at=now,
                    cash_account_id=accounts[0].id, payment_method='cash', note='synthetic expense')
                    for oid, amount in [(outlets[0].id, 10), (outlets[1].id, 20), (None, 9000)]]
        db.add_all(expenses)
        purchases = []
        for i, outlet in enumerate(outlets[:3]):
            order = Order(id=uuid4(), outlet_id=outlet.id, user_id=users['owner'].id, customer_id=customer.id,
                          order_number='QA-' + uuid4().hex, display_number=i + 1, status='completed', subtotal=100, total_amount=100)
            db.add(order); await db.flush()
            db.add(Payment(id=uuid4(), outlet_id=outlet.id, order_id=order.id, amount_due=100, amount_paid=100, status='paid', payment_method='cash'))
            db.add(OrderItem(order_id=order.id, product_id=products[1 if i == 1 else 0].id, quantity=1, unit_price=100, total_price=100))
            po = PurchaseOrder(id=uuid4(), outlet_id=outlet.id, supplier_id=supplier.id, po_number='QA-' + uuid4().hex,
                               status='received', total_amount=1000, paid_amount=100, received_at=now, photo_url='/uploads/secret-invoice.jpg', notes='price: 1000')
            db.add(po); await db.flush(); purchases.append(po)
            db.add(PurchaseOrderItem(purchase_order_id=po.id, product_id=products[1 if i == 1 else 0].id,
                                     quantity=2, unit_price=500, total_price=1000))
        await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://qa') as client:
        async def call(method, path, who='none', body=None, params=None, expected=200):
            res = await client.request(method, '/api/v1' + path, params=params, json=body,
                headers={'Authorization': 'Bearer ' + create_access_token(users[who].id), 'X-Tenant-ID': str(tid)})
            assert res.status_code == expected, (method, path, who, expected, res.status_code, res.text)
            return res.json()

        oid, bid = str(outlets[0].id), str(brands[0].id)
        for path, params in [('/finance/summary', {'outlet_id': oid}), ('/purchases/', {'outlet_id': oid}),
                             ('/customers/workspace', {}), ('/recipes/', {'brand_id': bid})]:
            await call('GET', path, params=params, expected=403)
        for path in ['/ai/chat', '/ai/hpp-setup/sessions', '/invoice-ocr/scan', '/ai/apply-recipe']:
            await call('POST', path, 'hppwriter', {}, expected=403)
        await call('GET', '/customers/crm', 'crmwriter', expected=403)
        await call('PUT', f'/products/{products[0].id}', 'hppwriter', {}, expected=403)
        print('PASS independent domain grants; legacy alternate APIs, OCR and all AI writes remain closed')

        await call('GET', '/finance/summary', 'finance', params=[('outlet_id', str(outlets[1].id)), ('outlet_id', oid)], expected=404)
        await call('GET', '/recipes/', 'hpp', params=[('brand_id', str(brands[1].id)), ('brand_id', bid)], expected=404)
        await call('GET', '/purchases/', 'purchase', params={'outlet_id': oid, 'purchase_id': str(purchases[1].id)}, expected=404)
        for who in ('finance', 'buyer', 'customer', 'hpp'):
            allowed = (await call('GET', '/outlets/', who))['data']
            assert [o['id'] for o in allowed] == [oid]
        report = (await call('GET', '/finance/summary', 'finance', params={'outlet_id': oid, 'month': month}))['data']
        assert report['expenses_total'] == '10.00', report
        assert report['payables_outstanding'] == '900.00', report
        assert all(a['name'] != 'Forbidden cash' for a in report['accounts'])
        acc = (await call('GET', '/finance/accounts', 'finance'))['data']
        assert len(acc) == 2 and all(a['opening_balance'] is None for a in acc)
        all_report = (await call('GET', '/finance/summary', 'tenantfinance', params={'outlet_id': oid, 'month': month}))['data']
        assert all_report['expenses_total'] == '9010.00'
        await call('GET', '/finance/summary', 'finance', params={'outlet_id': str(outlets[2].id)}, expected=404)
        await call('GET', '/finance/summary', 'finance', params={'outlet_id': str(outlets[3].id)}, expected=404)
        expense = {'outlet_id': oid, 'category': 'sewa', 'amount': '12.34', 'client_request_id': str(uuid4())}
        await call('POST', '/finance/expenses', 'finance', expense, expected=403)
        await call('POST', '/finance/expenses', 'finwriter', {**expense, 'outlet_id': None}, expected=403)
        await call('PUT', f'/finance/expenses/{expenses[1].id}', 'finwriter', {'row_version': 0}, expected=404)
        await call('DELETE', f'/finance/expenses/{expenses[2].id}', 'finwriter', expected=403)
        await call('PUT', f'/finance/accounts/{accounts[0].id}', 'finwriter', {'name': 'Illegal', 'row_version': 0}, expected=403)
        await call('POST', '/finance/expenses', 'finwriter', {**expense, 'cash_account_id': str(accounts[2].id)}, expected=404)
        result = (await call('POST', '/finance/expenses', 'finwriter', expense))['data']
        repeated = (await call('POST', '/finance/expenses', 'finwriter', expense))['data']
        assert result['id'] == repeated['id'] and result['amount'] == '12.34'
        print('PASS finance outlet/global expense/account isolation, view cannot write, and one UUID replay result')

        masked = (await call('GET', f'/purchases/{purchases[0].id}', 'purchase'))['data']
        assert masked['total_amount'] is None and masked['photo_url'] is None and masked['notes'] is None
        assert masked['items'][0]['unit_price'] is None and masked['payments'] == []
        priced = (await call('GET', f'/purchases/{purchases[0].id}', 'priced'))['data']
        assert priced['total_amount'] == '1000.00' and priced['items'][0]['unit_price'] == '500.00'
        suppliers = (await call('GET', '/suppliers/', 'priced'))['data']
        assert suppliers[0]['purchase_total'] == '1000.00' and suppliers[0]['purchase_count'] == 1
        for target in purchases[1:]:
            await call('GET', f'/purchases/{target.id}', 'priced', expected=404)
            await call('POST', f'/purchases/{target.id}/pay', 'buyer', {'amount': 1, 'row_version': 0}, expected=404)
        nota = {'outlet_id': oid, 'client_request_id': str(uuid4()), 'paid_amount': 0,
                'items': [{'product_id': str(products[0].id), 'quantity': 2, 'unit_price': '50'}]}
        await call('POST', '/purchases/', 'buyer', nota, expected=403)
        await call('POST', '/purchases/', 'receiver', {**nota, 'items': [{'product_id': str(products[1].id), 'quantity': 1, 'unit_price': 50}]}, expected=404)
        await call('POST', '/purchases/', 'receiver', {**nota, 'supplier_id': str(foreign_supplier.id)}, expected=404)
        await call('POST', '/purchases/', 'receiver', {**nota, 'items': [{'new_product': {'name': 'Illegal', 'sell_price': 50}, 'quantity': 1, 'unit_price': 50}]}, expected=403)
        first = (await call('POST', '/purchases/', 'receiver', nota))['data']
        second = (await call('POST', '/purchases/', 'receiver', nota))['data']
        assert first['id'] == second['id']
        payment = {'client_request_id': str(uuid4()), 'row_version': first['row_version'], 'amount': 10}
        paid = (await call('POST', f'/purchases/{first["id"]}/pay', 'buyer', payment))['data']
        replayed = (await call('POST', f'/purchases/{first["id"]}/pay', 'buyer', payment))['data']
        assert paid['paid_amount'] == replayed['paid_amount'] == '10.00'
        async with Admin() as db:
            assert (await db.get(Product, products[0].id)).stock_qty == 52
        print('PASS purchases price/image/notes masking, parent and same-brand sibling outlet denial, stock grant and atomic replay')

        listing = (await call('GET', '/customers/workspace', 'customer'))['data']
        assert listing['summary']['spent'] == '100.00' and listing['items'][0]['total_visits'] == 1
        assert not listing['can_manage'] and not listing['can_export'] and listing['scope'] == 'allowed_outlets'
        detail = (await call('GET', f'/customers/workspace/{customer.id}', 'customer'))['data']
        assert len(detail['orders']) == 1 and detail['total_spent'] == '100.00' and len(detail['favourites']) == 1
        await call('GET', f'/customers/workspace/{foreign_customer.id}', 'customer', expected=404)
        await call('GET', '/customers/workspace', 'customer', params={'export': 'true'}, expected=403)
        exported = (await call('GET', '/customers/workspace', 'exporter', params={'export': 'true'}))['data']
        assert exported['summary']['spent'] == '100.00'
        profile = {'client_request_id': str(uuid4()), 'name': 'Synthetic contact without number', 'phone': None, 'wa_marketing_consent': False}
        await call('POST', '/customers/workspace', 'customer', profile, expected=403)
        saved = (await call('POST', '/customers/workspace', 'crmwriter', profile))['data']
        assert (await call('POST', '/customers/workspace', 'crmwriter', profile))['data']['id'] == saved['id']
        note = {'client_request_id': str(uuid4()), 'kind': 'note', 'body': 'Synthetic shared service note'}
        await call('POST', f'/customers/workspace/{customer.id}/notes', 'customer', note, expected=403)
        await call('POST', f'/customers/workspace/{customer.id}/notes', 'crmwriter', note)
        print('PASS CRM shared profile but scoped facts/history/favourites/summary/export, separate mutation and replay')

        rows = (await call('GET', '/recipes/', 'hpp'))['data']
        assert len(rows) == 1 and Decimal(rows[0]['total_cost']) == 100, rows
        await call('GET', '/recipes/', 'hpp', params={'brand_id': str(brands[1].id)}, expected=404)
        await call('GET', '/recipes/', 'hpp', params={'product_id': str(products[2].id)}, expected=404)
        body = {'product_id': str(products[0].id), 'ingredients': [{'ingredient_id': str(ingredients[0].id), 'quantity': 3, 'quantity_unit': 'gram'}]}
        for who in ('hpp', 'drafter', 'approver'):
            await call('POST', '/recipes/', who, body, expected=403)
        await call('POST', '/recipes/', 'hppwriter', {**body, 'ingredients': [{'ingredient_id': str(ingredients[1].id), 'quantity': 1, 'quantity_unit': 'gram'}]}, expected=404)
        await call('PUT', f'/recipes/{recipes[0].id}', 'hppwriter', {**body, 'product_id': str(products[1].id)}, expected=404)
        await call('POST', '/recipes/', 'hppwriter', {**body, 'ingredients': None}, expected=422)
        with patch('backend.services.knowledge_graph_service.rebuild_graph', AsyncMock()):
            changed = (await call('POST', '/recipes/', 'hppwriter', body))['data']
        assert Decimal(changed['total_cost']) == 150, changed
        await call('PUT', f'/ingredients/{ingredients[1].id}', 'hppwriter', {'row_version': 0, 'buy_price': 4000}, expected=404)
        await call('PUT', f'/ingredients/{ingredients[0].id}', 'drafter', {'row_version': 0, 'buy_price': 4000}, expected=403)
        print('PASS HPP scoped brand/parent/nested ingredient checks, direct save needs manage+approve, server HPP unchanged')

        async with Admin() as db:
            tenant = await db.get(Tenant, tid)
            tenant.login_username = 'qa-' + uuid4().hex[:16]
            employee = HrEmployee(id=uuid4(), tenant_id=tid, outlet_id=outlets[0].id, code='QA-TENANT',
                                  name='Synthetic tenant staff', position='Finance', started_on=now.date())
            db.add(employee); await db.commit()
        role_body = {'id': str(uuid4()), 'name': 'Synthetic tenant finance', 'scope': 'tenant', 'outlet_ids': [],
                     'client_request_id': str(uuid4()), 'permissions': {'finance.view': True}}
        saved_role = (await call('POST', '/hris/access/roles', 'owner', role_body))['data']
        assert saved_role['scope'] == 'tenant'
        assert (await call('POST', '/hris/access/roles', 'owner', role_body))['data'] == saved_role
        staff_body = {'row_version': 1, 'username': 'synthetic-tenant-staff', 'role_id': role_body['id'], 'client_request_id': str(uuid4())}
        staff = (await call('POST', f'/hris/employees/{employee.id}/account', 'owner', staff_body))['data']
        assert staff['role_id'] == role_body['id']
        assert (await call('POST', f'/hris/employees/{employee.id}/account', 'owner', staff_body))['data'] == staff
        async with Admin() as db:
            employee_account = await db.get(User, __import__('uuid').UUID(staff['id']))
            context = await resolve_access(db, employee_account)
            assert context.scope == 'tenant' and len(context.outlets) == 3
        await call('POST', '/hris/access/roles', 'owner', {**role_body, 'client_request_id': str(uuid4()), 'scope': 'outlet'}, expected=422)
        print('PASS explicit tenant role save/replay and assignment to a real employee account; empty outlet scope rejected')

        old_manifest = (await call('GET', '/auth/access', 'finance'))['data']
        async with Admin() as db:
            role = await db.get(Role, roles['finance'].id)
            role.permissions = {'access_policy': {'version': 1, 'permissions': {}, 'outlet_ids': [oid]}}
            role.row_version += 1
            await db.commit()
        await call('GET', '/finance/summary', 'finance', params={'outlet_id': oid}, expected=403)
        fresh = (await call('GET', '/auth/access', 'finance'))['data']
        assert fresh['access_version'] != old_manifest['access_version']
        for who in ('owner', 'legacy'):
            await call('GET', '/finance/summary', who, params={'outlet_id': oid, 'month': month})
            await call('GET', '/customers/workspace', who)
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(tid)})
            assert not any((await db.execute(text('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user'))).one())
            assert await db.get(Customer, foreign_customer.id) is None
            assert await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.user_id == users['finwriter'].id)) == 1
        malformed = await client.post('/api/v1/recipes/', content='{broken', headers={
            'Authorization': 'Bearer ' + create_access_token(users['hppwriter'].id), 'Content-Type': 'application/json'})
        assert malformed.status_code == 422
        async with Admin() as db:
            brand = await db.get(Brand, brands[0].id); brand.is_active = False; await db.commit()
        await call('GET', '/finance/summary', 'finwriter', params={'outlet_id': oid}, expected=403)
        assert (await call('GET', '/auth/access', 'finwriter'))['data']['outlets'] == []
        print('PASS access revocation on existing JWT, inactive brand removal, owner/legacy compatibility, forced RLS and mutation audit')
    await engine.dispose(); await admin.dispose()


asyncio.run(main())
