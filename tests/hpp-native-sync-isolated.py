"""Synthetic HTTP sync regression in an isolated PostgreSQL with non-superuser RLS."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import FastAPI, Depends, Header
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.core.database import get_db
from backend.models import Tenant, User, Brand, Outlet, Product, Ingredient, Recipe, RecipeIngredient, OutletStock
from backend.api import deps
from backend.api.routes import sync
from backend.services.recipe_hpp_sync import get_recipe_hpp_changes
from backend.schemas.sync import SyncPayload

assert settings.POSTGRES_SERVER == 'selaris-hpp-native-db'
assert settings.POSTGRES_APP_USER == 'hpp_app'
admin = create_async_engine('postgresql+asyncpg://hpp_admin:hpp-test-only@selaris-hpp-native-db/hpp_native')
AdminSession = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(sync.router, prefix='/sync')
users, brands, outlets, products, ingredients, recipes = [], [], [], [], [], []
old = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def current_user(x_qa_user: int = Header(default=0), db=Depends(get_db)):
    user = users[x_qa_user]
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(user.tenant_id)})
    return user


app.dependency_overrides[deps.get_current_user] = current_user


async def main():
    async with AdminSession() as db:
        for n in range(2):
            tid = uuid4()
            tenant = Tenant(id=tid, name=f'HPP QA {n}', schema_name=f'qa_{tid.hex}', subscription_tier='pro')
            db.add(tenant); await db.flush()
            brand = Brand(tenant_id=tid, name=f'QA {n}', type='cafe')
            user = User(tenant_id=tid, phone=f'qa-{uuid4().hex}', full_name='QA')
            db.add_all([brand, user]); await db.flush()
            outlet = Outlet(tenant_id=tid, brand_id=brand.id, name='QA', slug=f'qa-{uuid4().hex}', stock_mode='recipe')
            db.add(outlet); await db.flush()
            users.append(user); brands.append(brand); outlets.append(outlet)
            ing = Ingredient(brand_id=brand.id, name='Beras', base_unit='gram', unit_type='WEIGHT',
                             tracking_mode='detail', cost_per_base_unit=Decimal('17'), needs_review=True, updated_at=old)
            db.add(ing); await db.flush(); ingredients.append(ing)
            for j in range(13):
                p = Product(brand_id=brand.id, name=f'Menu {n}-{j}', base_price=5000, updated_at=old)
                db.add(p); await db.flush(); products.append(p)
                r = Recipe(product_id=p.id, is_estimated=True, updated_at=old)
                db.add(r); await db.flush(); recipes.append(r)
                db.add(RecipeIngredient(recipe_id=r.id, ingredient_id=ing.id, quantity=0.1, quantity_unit='kg', updated_at=old))
            db.add(OutletStock(outlet_id=outlet.id, ingredient_id=ing.id, computed_stock=250))
        await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://qa') as client:
        payload = {'node_id': 'qa:device', 'outlet_id': str(outlets[0].id), 'changes': {}, 'limit': 10}
        snapshots, pulled, pages = {}, set(), 0
        response = await client.post('/sync/', json=payload)
        assert response.status_code == 200, response.text
        watermark = response.json()['last_sync_hlc']
        while True:
            data = response.json(); pages += 1
            assert data['stock_mode'] == 'recipe'
            for s in data['changes']['recipe_hpp']:
                assert s['product_id'] in {str(p.id) for p in products[:13]}
                assert s['total_cost'] == '1700.00' and s['is_estimated'] and s['needs_review']
                snapshots[s['recipe_id']] = s
            pulled.update(r['id'] for r in data['changes']['recipes'])
            if not data['has_more']: break
            assert pages < 30
            response = await client.post('/sync/', json={**payload,
                'last_sync_hlc': watermark, 'cursor_hlc': data['next_cursor_hlc'],
                'cursor_last_id': data['next_cursor_last_id']})
            assert response.status_code == 200, response.text
        assert len(pulled) == len(snapshots) == 13
        print(f'PASS full paginated HTTP pull: {pages} pages, all 13 recipes, brand-scoped snapshots')

        async with AdminSession() as db:
            ing = await db.get(Ingredient, ingredients[0].id)
            ing.cost_per_base_unit = Decimal('19'); ing.needs_review = False
            ing.updated_at = datetime.now(timezone.utc); ing.row_version += 1
            await db.commit()
        delta = await client.post('/sync/', json={**payload, 'last_sync_hlc': watermark})
        assert delta.status_code == 200, delta.text
        d = delta.json()['changes']
        assert d['recipes'] == [] and d['recipe_ingredients'] == []
        assert len(d['ingredients']) == 1 and len(d['recipe_hpp']) == 13
        assert all(s['total_cost'] == '1900.00' and not s['needs_review'] for s in d['recipe_hpp'])
        print('PASS ingredient-only delta refreshes every dependent recipe without parent timestamp changes')

        # Attempts to push derived financial values are ignored.
        tampered = await client.post('/sync/', json={**payload, 'last_sync_hlc': delta.json()['last_sync_hlc'],
            'changes': {'recipe_hpp': [{'recipe_id': str(recipes[0].id), 'total_cost': '1'}]}})
        assert tampered.status_code == 200
        forbidden = await client.post('/sync/', json={**payload, 'outlet_id': str(outlets[1].id)})
        assert forbidden.status_code == 403
        async for db in get_db():
            await db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {'tid': str(users[0].tenant_id)})
            assert not (await db.execute(select(Ingredient).where(Ingredient.brand_id == brands[1].id))).scalars().all()
            hidden = await get_recipe_hpp_changes(db, brands[1].id,
                SyncPayload(ingredients=[{'id': str(ingredients[1].id)}]))
            assert hidden == []
            role = (await db.execute(text('SELECT rolsuper FROM pg_roles WHERE rolname=current_user'))).scalar()
            assert role is False
            break
        print('PASS non-superuser RLS, other outlet rejected, derived HPP push ignored')

        async with AdminSession() as db:
            stock = (await db.execute(select(OutletStock).where(OutletStock.outlet_id == outlets[0].id))).scalar_one()
            assert stock.computed_stock == 250
            ri = (await db.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipes[0].id))).scalar_one()
            assert ri.quantity == 0.1
            ri.quantity_unit = 'ml'; ri.updated_at = datetime.now(timezone.utc)
            await db.commit()
        invalid = await client.post('/sync/', json={**payload, 'last_sync_hlc': delta.json()['last_sync_hlc']})
        assert invalid.status_code == 200
        s = next(s for s in invalid.json()['changes']['recipe_hpp'] if s['recipe_id'] == str(recipes[0].id))
        assert s['total_cost'] is None and s['ingredients'][0]['line_cost'] is None
        print('PASS invalid unit produces incomplete HPP, raw quantity and physical stock unchanged')
    await admin.dispose()


asyncio.run(main())
