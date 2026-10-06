"""Real HTTP/SQL purchasing checks using synthetic tenants and non-superuser RLS."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import FastAPI, Depends, Header
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.core.database import get_db
from backend.models import Tenant, User, Brand, Outlet, Event, Product, Ingredient, OutletStock
from backend.models.purchasing import Supplier, PurchaseOrder
from backend.models.finance import Expense
from backend.api import deps
from backend.api.routes import purchasing, finance, invoice_ocr

assert settings.POSTGRES_SERVER == 'selaris-purchasing-qa-db'
assert settings.POSTGRES_APP_USER == 'purchase_app'
admin = create_async_engine('postgresql+asyncpg://purchase_admin:purchase-test-only@selaris-purchasing-qa-db/purchase_qa')
AdminSession = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(purchasing.purchases_router,prefix='/purchases')
app.include_router(purchasing.suppliers_router,prefix='/suppliers')
app.include_router(finance.router,prefix='/finance')
users,outlets,products,ingredients,suppliers=[],[],[],[],[]

@app.middleware('http')
async def request_id(request,call_next):
    request.state.request_id='purchase-qa'
    return await call_next(request)

async def current_user(x_qa_user:int=Header(default=0),db=Depends(get_db)):
    user=users[x_qa_user]
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"),{'tid':str(user.tenant_id)})
    return user
app.dependency_overrides[deps.get_current_user]=current_user

async def main():
    async with AdminSession() as db:
        for n in range(2):
            tid=uuid4(); db.add(Tenant(id=tid,name=f'Purchase QA {n}',schema_name=f'qa_{tid.hex}',subscription_tier='pro' if n==0 else 'starter')); await db.flush()
            brand=Brand(tenant_id=tid,name=f'QA {n}',type='cafe'); user=User(tenant_id=tid,phone=f'qa-{uuid4().hex}',full_name='QA'); db.add_all([brand,user]); await db.flush()
            outlet=Outlet(tenant_id=tid,brand_id=brand.id,name='QA',slug=f'qa-{uuid4().hex}')
            product=Product(brand_id=brand.id,name='QA product',base_price=100,buy_price=10,stock_enabled=True,stock_qty=10)
            ingredient=Ingredient(brand_id=brand.id,name='QA sugar',base_unit='gram',unit_type='WEIGHT',tracking_mode='simple',buy_price=10,buy_qty=1000,cost_per_base_unit=Decimal('.01'))
            supplier=Supplier(tenant_id=tid,name='QA supplier',payment_terms_days=7); db.add_all([outlet,product,ingredient,supplier]); await db.flush()
            db.add(OutletStock(outlet_id=outlet.id,ingredient_id=ingredient.id,computed_stock=1000))
            users.append(user); outlets.append(outlet); products.append(product); ingredients.append(ingredient); suppliers.append(supplier)
        other_brand=Brand(tenant_id=users[0].tenant_id,name='Second brand',type='cafe'); db.add(other_brand); await db.flush()
        cross_brand=Product(brand_id=other_brand.id,name='Other brand product',base_price=100,stock_enabled=True,stock_qty=0); db.add(cross_brand)
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://qa',timeout=60) as client:
        payload={'client_request_id':str(uuid4()),'outlet_id':str(outlets[0].id),'supplier_id':str(suppliers[0].id),
                 'received_at':'2026-09-01T12:00:00+07:00','paid_amount':'20.00','invoice_no':'QA%_invoice',
                 'items':[{'product_id':str(products[0].id),'quantity':2,'unit':'pcs','unit_price':'50.00','total_price':'90.00'},
                          {'name':'Gas','quantity':1,'unit_price':'10.25'}]}
        a,b=await asyncio.gather(*[client.post('/purchases/',json=payload) for _ in range(2)])
        assert a.status_code==b.status_code==200,(a.text,b.text)
        po=a.json()['data']; assert po['id']==b.json()['data']['id'] and po['total_amount']=='100.25'
        async with AdminSession() as db:
            product=await db.get(Product,products[0].id)
            assert product.stock_qty==12 and product.buy_price==Decimal('15.83'),(product.stock_qty,product.buy_price)
            assert await db.scalar(select(func.count(Expense.id)).where(Expense.purchase_id==po['id']))==1
        changed=await client.post('/purchases/',json={**payload,'invoice_no':'changed'})
        assert changed.status_code==409,changed.text
        print('PASS simultaneous receipt replay: one note, one restock, one expense; HPP follows discounted total')
        pay={'client_request_id':str(uuid4()),'row_version':po['row_version'],'amount':'25.50'}
        a,b=await asyncio.gather(*[client.post(f"/purchases/{po['id']}/pay",json=pay) for _ in range(2)])
        assert a.status_code==b.status_code==200,(a.text,b.text)
        paid=a.json()['data']; assert paid['paid_amount']=='45.50' and paid['outstanding_amount']=='54.75'
        assert sum(Decimal(p['amount']) for p in paid['payments'])==Decimal('45.50')
        async with AdminSession() as db:
            assert await db.scalar(select(func.count(Event.id)).where(Event.stream_id==f"purchase:{po['id']}",Event.event_type=='purchase.paid'))==1
            assert (await db.get(Product,products[0].id)).stock_qty==12
        details=await client.get(f"/purchases/{po['id']}"); assert details.status_code==200 and details.json()['data']['items'][0]['cost_after']=='15.83'
        for month,expected in [('2026-09','20.00'),('2026-10','25.50')]:
            response=await client.get('/finance/summary',params={'outlet_id':str(outlets[0].id),'month':month}); assert response.status_code==200,response.text
            assert response.json()['data']['purchases_paid']==expected,response.text
        print('PASS payment replay one immutable event, no stock change, persistent HPP effects/history; finance agrees across months')
        race=await asyncio.gather(*[client.post(f"/purchases/{po['id']}/pay",json={'client_request_id':str(uuid4()),'row_version':paid['row_version'],'amount':'1.00'}) for _ in range(2)])
        assert sorted(r.status_code for r in race)==[200,409],[r.text for r in race]
        print('PASS distinct concurrent installments conflict by version')
        ing_payload={**payload,'client_request_id':str(uuid4()),'invoice_no':'QA ingredients','paid_amount':None,
                     'items':[{'ingredient_id':str(ingredients[0].id),'quantity':2,'unit':'kg','unit_price':'20','total_price':'30'}]}
        received=await client.post('/purchases/',json=ing_payload); assert received.status_code==200,received.text
        async with AdminSession() as db:
            stock=await db.scalar(select(OutletStock).where(OutletStock.outlet_id==outlets[0].id,OutletStock.ingredient_id==ingredients[0].id))
            ing=await db.get(Ingredient,ingredients[0].id)
            assert stock.computed_stock==3000 and ing.cost_per_base_unit==Decimal('.01333333'),(stock.computed_stock,ing.cost_per_base_unit)
        print('PASS kg conversion and eight-decimal weighted ingredient cost')
        bad={**ing_payload,'client_request_id':str(uuid4()),'items':[
            {'product_id':str(products[0].id),'quantity':1,'unit_price':'20'},
            {'ingredient_id':str(ingredients[0].id),'quantity':1,'unit':'liter','unit_price':'20'}]}
        rejected=await client.post('/purchases/',json=bad); assert rejected.status_code==400,rejected.text
        async with AdminSession() as db:
            assert (await db.get(Product,products[0].id)).stock_qty==12
        for line in [ {'product_id':str(products[1].id),'quantity':1,'unit_price':'20'},
                      {'product_id':str(cross_brand.id),'quantity':1,'unit_price':'20'} ]:
            response=await client.post('/purchases/',json={**ing_payload,'client_request_id':str(uuid4()),'items':[line]})
            assert response.status_code==404,response.text
        starter=await client.post('/purchases/',headers={'x-qa-user':'1'},json={**ing_payload,'client_request_id':str(uuid4()),'outlet_id':str(outlets[1].id),'supplier_id':str(suppliers[1].id),'items':[{'ingredient_id':str(ingredients[1].id),'quantity':1,'unit_price':'20'}]})
        assert starter.status_code==403,starter.text
        print('PASS invalid later line rolls back earlier stock; tenant/brand boundaries and Starter ingredient gate')
        for patch in [{'received_at':'2026-10-07T12:00:00+07:00'}, {'received_at':'2026-09-01T12:00:00'}, {'paid_amount':'1000'}, {'items':[{'name':'x','quantity':1,'unit_price':'1.001'}]}]:
            response=await client.post('/purchases/',json={**payload,'client_request_id':str(uuid4()),**patch}); assert response.status_code in (400,422),response.text
        summary=await client.get('/purchases/summary',params={'outlet_id':str(outlets[0].id),'month':'2026-09'})
        assert summary.status_code==200 and summary.json()['data']['month_total']=='130.25',summary.text
        assert summary.json()['data']['overdue_total']=='53.75'
        literal=await client.get('/purchases/',params={'outlet_id':str(outlets[0].id),'month':'2026-09','search':'%_'})
        assert literal.status_code==200 and len(literal.json()['data'])==1,literal.text
        for params in [{'limit':-1},{'skip':-1},{'month':'2026-13'}]:
            response=await client.get('/purchases/',params={'outlet_id':str(outlets[0].id),**params}); assert response.status_code in (400,422),response.text
        print('PASS WIB month bounds, overdue and literal search; invalid pagination/dates/money rejected')
        supplier_payload={'client_request_id':str(uuid4()),'name':'  QA new supplier  ','payment_terms_days':14}
        a,b=await asyncio.gather(*[client.post('/suppliers/',json=supplier_payload) for _ in range(2)])
        assert a.status_code==b.status_code==200 and a.json()['data']['id']==b.json()['data']['id'],(a.text,b.text)
        sup=a.json()['data']
        updates=await asyncio.gather(*[client.put(f"/suppliers/{sup['id']}",json={'row_version':0,'notes':str(n)}) for n in range(2)])
        assert sorted(r.status_code for r in updates)==[200,409],[r.text for r in updates]
        inactive=await client.put(f"/suppliers/{sup['id']}",json={'row_version':1,'is_active':False}); assert inactive.status_code==200,inactive.text
        response=await client.post('/purchases/',json={**payload,'client_request_id':str(uuid4()),'supplier_id':sup['id']}); assert response.status_code==404,response.text
        async with AdminSession() as db:
            assert await invoice_ocr._get_brand_id(users[0].tenant_id,db,outlets[0].id)==outlets[0].brand_id
        print('PASS supplier replay, edit race, active references and OCR brand selection')
        # Different requests in parallel must receive different sequential note numbers.
        both=await asyncio.gather(*[client.post('/purchases/',json={**payload,'client_request_id':str(uuid4()),'items':[{'product_id':str(products[0].id),'quantity':1,'unit_price':'20'}]}) for _ in range(2)])
        assert all(r.status_code==200 for r in both),[r.text for r in both]
        assert len({r.json()['data']['po_number'] for r in both})==2
        repeated={**payload,'client_request_id':str(uuid4()),'paid_amount':None,'items':[
            {'product_id':str(products[0].id),'quantity':1,'unit_price':'30'},
            {'product_id':str(products[0].id),'quantity':1,'unit_price':'40'},
            {'ingredient_id':str(ingredients[0].id),'quantity':1,'unit':'kg','unit_price':'20'},
            {'ingredient_id':str(ingredients[0].id),'quantity':1,'unit':'kg','unit_price':'30'}]}
        response=await client.post('/purchases/',json=repeated); assert response.status_code==200,response.text
        lines=response.json()['data']['items']
        assert lines[2]['cost_after']=='0.01500000' and lines[3]['cost_before']=='0.01500000' and lines[3]['cost_after']=='0.01800000',lines
        async with AdminSession() as db:
            assert (await db.get(Product,products[0].id)).stock_qty==16
            assert (await db.get(Ingredient,ingredients[0].id)).cost_per_base_unit==Decimal('.01800000')
        package=await client.post('/purchases/',json={**payload,'client_request_id':str(uuid4()),'paid_amount':None,
            'items':[{'product_id':str(products[0].id),'quantity':2,'unit':'dus','unit_price':'120'}]})
        assert package.status_code==200 and package.json()['data']['items'][0]['qty_base']==24,package.text
        async with AdminSession() as db:
            assert (await db.get(Product,products[0].id)).stock_qty==40
            legacy=PurchaseOrder(outlet_id=outlets[0].id,po_number='QA-incomplete',status='received',total_amount=200,paid_amount=200,received_at=datetime(2026,9,1,tzinfo=timezone.utc))
            db.add(legacy); await db.flush()
            db.add(Event(outlet_id=outlets[0].id,stream_id=f'purchase:{legacy.id}',event_type='purchase.paid',event_data={'paid_after':'200','amount':'9999'}))
            await db.commit()
        incomplete=await client.get(f'/purchases/{legacy.id}')
        assert incomplete.status_code==200 and incomplete.json()['data']['payment_history_incomplete'] and incomplete.json()['data']['payments']==[],incomplete.text
        print('PASS parallel distinct receipts, repeated targets with distinct HPP snapshots, package units, incomplete legacy history; ALL PURCHASING INTEGRATION CHECKS PASSED')
    await admin.dispose()

asyncio.run(main())
