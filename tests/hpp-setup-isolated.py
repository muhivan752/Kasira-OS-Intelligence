"""Run only with the schema-only QA database, never against a merchant DB."""
import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4, UUID

import httpx
import uvicorn
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from sqlalchemy import select, text, func, event
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, get_db
from backend.models import Tenant, User, Brand, Outlet, Product, Ingredient, Recipe, RecipeIngredient, OutletStock, Event, AuditLog
from backend.models.hpp_setup import HppSetupSession, HppSetupTurn
from backend.api import deps
from backend.api.routes import hpp_setup, recipes, products, orders, connect
from backend.services import hpp_setup_service as service
from backend.services import embedding_service

assert settings.POSTGRES_SERVER == "selaris-hpp-qa-db", "Refusing a non-QA database"
assert settings.POSTGRES_APP_USER == "hpp_app", "RLS must be tested with non-superuser"
app = FastAPI()
for module, prefix in ((hpp_setup, "/ai/hpp-setup"), (recipes, "/recipes"), (products, "/products"), (orders, "/orders"), (connect, "/connect")):
    app.include_router(module.router, prefix=prefix)


@app.middleware("http")
async def request_id(request: Request, call_next):
    request.state.request_id = "hpp-isolated-test"
    return await call_next(request)


users, tenants, brands, outlets = [], [], [], []


async def current_user(request: Request, x_test_user: str = Header(default=""), db=Depends(get_db)):
    if not x_test_user:
        raise HTTPException(401)
    user = next((u for u in users if str(u.id) == x_test_user), None)
    if not user:
        raise HTTPException(401)
    await hpp_setup.scope(db, user)
    from backend.services.access import resolve_access
    from backend.core.security import create_access_token
    from jose import jwt
    request.state.access = await resolve_access(db, user)
    request.state.auth_token = create_access_token(user.id)
    request.state.auth_claims = jwt.decode(request.state.auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return user


async def current_tenant(user=Depends(current_user)):
    return next(t for t in tenants if t.id == user.tenant_id)


app.dependency_overrides[deps.get_current_user] = current_user
app.dependency_overrides[deps.get_current_tenant] = current_tenant
responses, seen_history = [], []
gate = None


async def fake_generate(draft, turns, ctx, mode, references="", status="draft"):
    seen_history.append([t.message for t in turns])
    if gate:
        await gate.wait()
    output = responses.pop(0)
    if isinstance(output, Exception):
        raise output
    if isinstance(output, service.ModelReply):
        return output, {"input_tokens": 100, "output_tokens": 300, "model": "isolated-fixture"}
    return service.ModelReply(reply="Periksa sumber dan takaran pada draft.", draft=output), {"input_tokens": 100, "output_tokens": 300, "model": "isolated-fixture"}


async def no_reference(*args, **kwargs):
    return ""


service.generate = fake_generate
embedding_service.enrich_ai_context = no_reference


def draft(name, ingredient="Beras fixture", estimate=False, quantity=100):
    return service.Draft.model_validate({"product_name": name, "servings": 1,
        "servings_source": "estimate" if estimate else "user", "servings_evidence": "satu porsi",
        "ingredients": [{"name": ingredient, "quantity": quantity, "quantity_unit": "gram",
            "quantity_source": "estimate" if estimate else "user", "quantity_evidence": "beras 100 gram",
            "buy_price": 15000, "buy_qty": 1, "buy_unit": "kg",
            "price_source": "estimate" if estimate else "user", "price_evidence": "beli 1 kg 15000"}]})


async def counts():
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        return {model.__tablename__: (await db.execute(select(func.count()).select_from(model))).scalar()
            for model in (Product, Ingredient, Recipe, OutletStock, Event, AuditLog)}


async def main():
    global gate
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        for n, tier in enumerate(("pro", "pro", "starter")):
            tenant = Tenant(id=uuid4(), name=f"HPP QA {n}", schema_name=f"hpp_qa_{uuid4().hex}",
                subscription_tier=tier, subscription_status="active", is_demo=True)
            db.add(tenant); await db.flush(); tenants.append(tenant)
            brand = Brand(id=uuid4(), tenant_id=tenant.id, name=f"QA brand {n}", type="resto")
            user = User(id=uuid4(), tenant_id=tenant.id, full_name="HPP QA", phone=f"hpp-qa-{uuid4().hex}", is_superuser=True)
            db.add_all([brand, user]); await db.flush(); brands.append(brand); users.append(user)
            outlet = Outlet(id=uuid4(), tenant_id=tenant.id, brand_id=brand.id, name=f"QA {n}", slug=f"hpp-qa-{uuid4().hex}", stock_mode="simple")
            db.add(outlet); outlets.append(outlet)
        await db.commit()
    user = users[0]
    header = {"X-Test-User": str(user.id)}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://qa", headers=header) as client:
        async def create(mode="manual"):
            r = await client.post("/ai/hpp-setup/sessions", json={"outlet_id": str(outlets[0].id), "mode": mode})
            assert r.status_code == 200, r.text
            return r.json()["data"]
        async def send(chat, output, content="satu porsi beras 100 gram beli 1 kg 15000", request=None, mode=None):
            responses.append(output)
            payload = {"outlet_id": str(outlets[0].id), "request_id": request or str(uuid4()), "revision": chat["revision"], "mode": mode or chat["mode"], "message": content}
            r = await client.post(f'/ai/hpp-setup/sessions/{chat["id"]}/messages', json=payload)
            assert r.status_code == 202, r.text
            saved = await client.get(f'/ai/hpp-setup/sessions/{chat["id"]}')
            return saved.json()["data"], payload
        def approval(chat, replace=False):
            return {"outlet_id": str(outlets[0].id), "revision": chat["revision"], "fingerprint": chat["preview"]["fingerprint"], "replace_recipe": replace}
        async def apply(chat, replace=False):
            return await client.post(f'/ai/hpp-setup/sessions/{chat["id"]}/approve', json=approval(chat, replace))

        assert (await client.post("/ai/hpp-setup/sessions", json={"outlet_id": str(outlets[1].id)})).status_code == 404
        assert (await client.post("/ai/hpp-setup/sessions", headers={"X-Test-User": str(users[2].id)}, json={"outlet_id": str(outlets[2].id)})).status_code == 403
        chat = await create()
        start = await counts()
        long_story = "satu porsi beras 100 gram beli 1 kg 15000\n" + "Cerita persiapan dapur dan pembelian bahan. " * 1100 + "Koreksi penting: satu porsi."
        chat, payload = await send(chat, draft("Nasi fixture"), long_story)
        assert chat["preview"]["total_cost"] == "1500.00"
        assert (await counts())["ingredients"] == start["ingredients"]
        replay = await client.post(f'/ai/hpp-setup/sessions/{chat["id"]}/messages', json=payload)
        assert replay.status_code == 202 and len(seen_history) == 1
        assert (await client.post(f'/ai/hpp-setup/sessions/{chat["id"]}/messages', json={**payload, "message": "different"})).status_code == 409
        stale = approval(chat)
        for n in range(11):
            chat, _ = await send(chat, draft("Nasi fixture"), f"Catatan dapur {n}: pertahankan data sebelumnya.")
        assert len(chat["turns"]) == 12 and len(seen_history[-1]) == 12
        assert seen_history[-1][0] == long_story
        assert (await client.post(f'/ai/hpp-setup/sessions/{chat["id"]}/approve', json=stale)).status_code == 409
        assert (await client.get(f'/ai/hpp-setup/sessions/{chat["id"]}', headers={"X-Test-User": str(users[1].id)})).status_code == 404
        resumed = (await client.get(f'/ai/hpp-setup/sessions/{chat["id"]}')).json()["data"]
        assert resumed["turns"][0]["message"] == long_story
        results = await asyncio.gather(apply(chat), apply(chat))
        assert all(r.status_code == 200 for r in results), [r.text for r in results]
        assert results[0].json()["data"]["result"] == results[1].json()["data"]["result"]
        applied = results[0].json()["data"]
        after = await counts()
        assert after["recipes"] == start["recipes"] + 1
        assert after["ingredients"] == start["ingredients"] + 1
        assert after["outlet_stock"] == start["outlet_stock"]
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            product = await db.get(Product, UUID(applied["result"]["product_id"]))
            assert not product.is_active and product.base_price == 0 and not product.stock_enabled
            ing = (await db.execute(select(Ingredient).where(Ingredient.brand_id == brands[0].id))).scalar_one()
            assert ing.base_unit == "gram" and ing.cost_per_base_unit == 15
            ri = (await db.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == UUID(applied["result"]["recipe_id"])))).scalar_one()
            assert ri.quantity == 100 and ri.quantity_unit == ing.base_unit
            await hpp_setup.scope(db, users[1])
            assert (await db.execute(select(HppSetupSession).where(HppSetupSession.id == UUID(chat["id"])))).scalar_one_or_none() is None
        recipe_response = await client.get(f'/recipes/?product_id={applied["result"]["product_id"]}')
        assert recipe_response.status_code == 200, recipe_response.text
        assert Decimal(str(recipe_response.json()["data"][0]["total_cost"])) == 1500

        # The canonical recipe must match actual POS deduction, restoration and storefront stock.
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            product = await db.get(Product, UUID(applied["result"]["product_id"]))
            product.is_active = True; product.stock_enabled = True; product.base_price = 10000
            outlet = await db.get(Outlet, outlets[0].id); outlet.stock_mode = "recipe"
            db.add(OutletStock(outlet_id=outlet.id, ingredient_id=ing.id, computed_stock=500,
                crdt_positive={"test": 500}, crdt_negative={}, min_stock_base=0, row_version=0))
            await db.commit()
        response = await client.get(f'/products/?brand_id={brands[0].id}')
        assert response.status_code == 200, response.text
        assert next(p for p in response.json()["data"] if p["id"] == applied["result"]["product_id"])["stock_qty"] == 5
        storefront = await client.get(f'/connect/{outlets[0].slug}')
        assert storefront.status_code == 200, storefront.text
        assert next(p for p in storefront.json()["data"]["products"] if p["id"] == applied["result"]["product_id"])["stock"] == 5
        def order_payload(quantity):
            return {"outlet_id": str(outlets[0].id), "order_type": "takeaway", "items": [{
                "product_id": applied["result"]["product_id"], "quantity": quantity,
                "unit_price": 10000, "total_price": quantity * 10000}]}
        insufficient = await client.post("/orders/", json=order_payload(6))
        assert insufficient.status_code == 400 and insufficient.json()["detail"]["code"] == "STOCK_INSUFFICIENT", insufficient.text
        order = await client.post("/orders/", json=order_payload(2))
        assert order.status_code == 200, order.text
        created_order = order.json()["data"]
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            stock = (await db.execute(select(OutletStock).where(OutletStock.outlet_id == outlets[0].id, OutletStock.ingredient_id == ing.id))).scalar_one()
            assert stock.computed_stock == 300
        cancelled = await client.put(f'/orders/{created_order["id"]}/status', json={"status": "cancelled", "row_version": created_order["row_version"]})
        assert cancelled.status_code == 200, cancelled.text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            stock = (await db.execute(select(OutletStock).where(OutletStock.outlet_id == outlets[0].id, OutletStock.ingredient_id == ing.id))).scalar_one()
            assert stock.computed_stock == 500
        print("PASS: real POS order/insufficient/cancel, canonical recipe stock and all-products storefront")

        # Approval conflicts reconcile current price without writing the old draft.
        second = await create()
        second, _ = await send(second, draft("Nasi fixture"))
        assert second["preview"]["replaces_recipe"]
        assert (await apply(second)).status_code == 409
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            ing = await db.get(Ingredient, ing.id)
            ing.cost_per_base_unit = 16; ing.row_version += 1
            await db.commit()
        assert (await apply(second, True)).status_code == 409
        second = (await client.get(f'/ai/hpp-setup/sessions/{second["id"]}')).json()["data"]
        assert second["preview"]["total_cost"] == "1600.00"
        assert (await apply(second, True)).status_code == 200

        # Failed corrections block approval; a same-ID retry cannot duplicate turns.
        failing = await create()
        failing, _ = await send(failing, draft("Failure fixture", "Bahan failure"))
        previous_revision = failing["revision"]
        failing, failed_payload = await send(failing, RuntimeError("Provider unavailable"), "Ubah takaran menjadi 200 gram")
        assert failing["error"] and failing["revision"] == previous_revision
        assert (await apply(failing)).status_code == 409
        responses.append(draft("Failure fixture", "Bahan failure", quantity=200))
        retried = await client.post(f'/ai/hpp-setup/sessions/{failing["id"]}/messages', json=failed_payload)
        assert retried.status_code == 202 and len(retried.json()["data"]["turns"]) == 2

        # No partial ingredient/recipe/audit/event commit when the final flush fails.
        atomic = await create("estimate")
        atomic, _ = await send(atomic, draft("Atomic fixture", "Bahan atomic", estimate=True))
        baseline = await counts()
        def fail_commit(db, *_):
            if any(isinstance(obj, AuditLog) and obj.action == "HPP_SETUP_APPROVED" for obj in db.new):
                raise RuntimeError("Injected final flush failure")
        event.listen(Session, "before_flush", fail_commit)
        try:
            assert (await apply(atomic)).status_code == 500
        finally:
            event.remove(Session, "before_flush", fail_commit)
        assert await counts() == baseline
        assert (await apply(atomic)).status_code == 200
        atomic = (await client.get(f'/ai/hpp-setup/sessions/{atomic["id"]}')).json()["data"]
        assert atomic["result"]["is_estimated"]
        response = await client.get(f'/recipes/?product_id={atomic["result"]["product_id"]}')
        assert response.json()["data"][0]["is_estimated"]

        # Two different sessions proposing the same new ingredient cannot duplicate it.
        a, b = await create("estimate"), await create("estimate")
        a, _ = await send(a, draft("Concurrent A", "Bahan bersama", True))
        b, _ = await send(b, draft("Concurrent B", "Bahan bersama", True))
        r1, r2 = await asyncio.gather(apply(a), apply(b))
        assert sorted([r1.status_code, r2.status_code]) == [200, 409], (r1.text, r2.text)
        loser = b if r2.status_code == 409 else a
        loser = (await client.get(f'/ai/hpp-setup/sessions/{loser["id"]}')).json()["data"]
        assert (await apply(loser)).status_code == 200
        async with AsyncSessionLocal() as db:
            await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
            assert (await db.execute(select(func.count()).select_from(Ingredient).where(Ingredient.name == "Bahan bersama", Ingredient.brand_id == brands[0].id))).scalar() == 1

        # Network work holds no session lock; concurrent messages see a lease.
        pending = await create("estimate")
        gate = asyncio.Event()
        responses.append(draft("Pending fixture", "Bahan pending", True))
        payload = {"outlet_id": str(outlets[0].id), "request_id": str(uuid4()), "revision": 0, "mode": "estimate", "message": "aku bingung"}
        task = asyncio.create_task(client.post(f'/ai/hpp-setup/sessions/{pending["id"]}/messages', json=payload))
        for _ in range(100):
            await asyncio.sleep(.02)
            fetched = (await client.get(f'/ai/hpp-setup/sessions/{pending["id"]}')).json()["data"]
            if fetched["pending"]: break
        assert fetched["pending"]
        assert (await client.post(f'/ai/hpp-setup/sessions/{pending["id"]}/messages', json={**payload, "request_id": str(uuid4())})).status_code == 409
        gate.set(); assert (await task).status_code == 202; gate = None
        implicit = await create('manual')
        implicit, request = await send(implicit, draft('Mie Bangladesh fixture', 'Mie fixture', True),
            content='Kasi estimasi lah', mode='manual')
        assert implicit['mode'] == 'estimate' and implicit['preview']['ready']
        assert implicit['turns'][0]['mode'] == 'manual', 'Original mode must preserve request replay identity'
        replay = await client.post(f'/ai/hpp-setup/sessions/{implicit["id"]}/messages', json=request)
        assert replay.status_code == 202 and len(replay.json()['data']['turns']) == 1
        implicit, _ = await send(implicit, draft('Mie Bangladesh fixture', 'Mie fixture', True),
            content='pakai manual saja', mode='estimate')
        assert implicit['mode'] == 'manual' and not implicit['preview']['ready']
        assert 'bantu estimasikan' in implicit['turns'][-1]['reply']
        print('PASS: explicit chat estimation changes effective mode; original request replay stays idempotent; Manual still blocks estimates')
        before = await counts()
        question = service.ModelReply(reply='Ada bahan yang dikarang model', action='answer',
            lookup=service.catalog.CatalogQuery(kind='overview'), draft=draft('Unwanted draft'))
        fresh = await create('manual')
        fresh, request = await send(fresh, question, content='Bahan dan resep apa yang sudah ada di toko?', mode='estimate')
        assert fresh['revision'] == 0 and fresh['preview'] is None and fresh['mode'] == 'manual'
        assert 'Di toko sekarang' in fresh['turns'][-1]['reply'] and 'dikarang' not in fresh['turns'][-1]['reply']
        replay = await client.post(f'/ai/hpp-setup/sessions/{fresh["id"]}/messages', json=request)
        assert replay.status_code == 202 and len(replay.json()['data']['turns']) == 1
        snapshot = (implicit['revision'], implicit['preview'], implicit['mode'])
        implicit, _ = await send(implicit, question, content='Apa saja bahan yang ada?', mode='estimate')
        assert (implicit['revision'], implicit['preview'], implicit['mode']) == snapshot
        assert 'masih draft' in implicit['turns'][-1]['reply']
        saved_snapshot = (atomic['revision'], atomic['preview'], atomic['result'], atomic['mode'])
        atomic, _ = await send(atomic, question, content='Lihat bahan dan resep yang sudah tersimpan', mode='manual')
        assert (atomic['revision'], atomic['preview'], atomic['result'], atomic['mode']) == saved_snapshot
        assert (await apply(atomic)).status_code == 200
        atomic, _ = await send(atomic, service.ModelReply(action='answer', reply='Bilang saja lalu aku otomatis lanjut'),
            content='Bagaimana lanjut menu lainnya setelah approve?', mode='estimate')
        assert 'Resep baru' in atomic['turns'][-1]['reply'] and 'sudah tersimpan' in atomic['turns'][-1]['reply']
        assert (atomic['revision'], atomic['preview'], atomic['result'], atomic['mode']) == saved_snapshot
        atomic, _ = await send(atomic, draft('Must not overwrite approved', 'Unwanted ingredient', True), content='ubah resep ini', mode='estimate')
        assert atomic['status'] == 'applied' and (atomic['revision'], atomic['preview'], atomic['result'], atomic['mode']) == saved_snapshot
        assert 'Resep baru' in atomic['turns'][-1]['reply']
        other = await client.post('/ai/hpp-setup/sessions', headers={'X-Test-User': str(users[1].id)},
            json={'outlet_id': str(outlets[1].id), 'mode': 'estimate'})
        assert other.status_code == 200
        other = other.json()['data']
        responses.append(question)
        queried = await client.post(f'/ai/hpp-setup/sessions/{other["id"]}/messages',
            headers={'X-Test-User': str(users[1].id)}, json={'outlet_id': str(outlets[1].id),
                'request_id': str(uuid4()), 'revision': 0, 'mode': 'estimate', 'message': 'Lihat semua bahan dan resep'})
        assert queried.status_code == 202
        other = (await client.get(f'/ai/hpp-setup/sessions/{other["id"]}',
            headers={'X-Test-User': str(users[1].id)})).json()['data']
        assert '0 bahan, 0 resep aktif, dan 0 menu' in other['turns'][-1]['reply']
        assert 'Beras fixture' not in other['turns'][-1]['reply']
        implicit, _ = await send(implicit, draft('Mie Bangladesh fixture', 'Mie fixture', True),
            content='lanjut lengkapi estimasi resep sebelumnya', mode='estimate')
        assert implicit['revision'] == snapshot[0] + 1 and implicit['preview']['ready']
        assert implicit['preview']['product_name'] == 'Mie Bangladesh fixture'
        after = await counts()
        for table in ('products', 'ingredients', 'recipes', 'outlet_stock', 'events'):
            assert before[table] == after[table], (table, before, after)
        print('PASS: catalog questions preserve empty/current/approved drafts, modes and fingerprints; replay and repeat approval safe; no operational writes')
        print("PASS: durable long chat, source labels, RLS/Pro/owner scope, replay, exact approval, conflict reconciliation, atomic rollback, concurrent approval/name reuse, and pending lease")

    # A real HTTP client must receive 202 while generation is still blocked.
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8189, log_level="warning", lifespan="off"))
    server_task = asyncio.create_task(server.serve())
    try:
        for _ in range(100):
            if server.started: break
            await asyncio.sleep(.02)
        assert server.started
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8189", headers=header) as network:
            chat = (await network.post("/ai/hpp-setup/sessions", json={"outlet_id": str(outlets[0].id), "mode": "estimate"})).json()["data"]
            gate = asyncio.Event()
            responses.append(draft("HTTP background fixture", "Bahan HTTP", True))
            r = await asyncio.wait_for(network.post(f'/ai/hpp-setup/sessions/{chat["id"]}/messages', json={
                "outlet_id": str(outlets[0].id), "request_id": str(uuid4()), "revision": 0, "mode": "estimate", "message": "Aku bingung, tolong estimasikan."}), timeout=2)
            assert r.status_code == 202 and r.json()["data"]["pending"]
            pending = (await network.get(f'/ai/hpp-setup/sessions/{chat["id"]}')).json()["data"]
            assert pending["pending"] and not pending["turns"][0]["reply"]
            gate.set()
            for _ in range(100):
                await asyncio.sleep(.05)
                completed = (await network.get(f'/ai/hpp-setup/sessions/{chat["id"]}')).json()["data"]
                if not completed["pending"]: break
            assert completed["preview"]["ready"] and completed["preview"]["total_cost"] == "1500.00"
            gate = None
        print("PASS: real HTTP receives 202 before model completion; fresh-session background worker persists the draft and polling resumes it")
    finally:
        if gate: gate.set()
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    asyncio.run(main())
