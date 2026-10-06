"""Synthetic HTTP/JWT tests on a separate PostgreSQL database with forced RLS."""
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api import deps
from backend.api.api import api_router
from backend.core.config import settings
from backend.core.database import engine, AsyncSessionLocal
from backend.core.security import create_access_token
from backend.models import Brand, Ingredient, Order, OrderItem, Outlet, OutletStock, Payment, Product, Recipe, RecipeIngredient, Role, Tenant, User
from backend.models.event import Event
from backend.models.customer import Customer
from backend.models.tab import Tab
from backend.services import fcm, online_orders
from backend.services.access import resolve_access
from backend.api.routes.orders import stream_orders
from starlette.requests import Request

assert settings.POSTGRES_SERVER == "selaris-pos-access-qa-db"
assert settings.POSTGRES_APP_USER == "pos_app"
admin = create_async_engine("postgresql+asyncpg://pos_admin:pos-test-only@selaris-pos-access-qa-db/pos_qa")
Admin = async_sessionmaker(admin, expire_on_commit=False)
app = FastAPI()
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_id(request, call_next):
    request.state.request_id = "pos-access-qa"
    return await call_next(request)


class Redis:
    async def get(self, key): return None
    async def setex(self, *args): return True
    async def delete(self, *args): return True


async def main():
    async with Admin() as db:
        tid, foreign_tid = uuid4(), uuid4()
        db.add_all([Tenant(id=tid, name="Synthetic POS QA", schema_name=f"qa_{uuid4().hex}", subscription_tier="pro", subscription_status="active"),
                    Tenant(id=foreign_tid, name="Synthetic other QA", schema_name=f"qa_{uuid4().hex}")])
        await db.flush()
        brands = [Brand(id=uuid4(), tenant_id=t, name=f"QA brand {i}", type="cafe") for i, t in enumerate([tid, tid, foreign_tid])]
        db.add_all(brands); await db.flush()
        outlets = [Outlet(id=uuid4(), tenant_id=t, brand_id=b.id, name=f"QA outlet {i}", slug=f"qa-{uuid4().hex}",
            stock_mode="recipe" if i == 1 else "simple", kitchen_mode="display") for i, (t, b) in enumerate(zip([tid, tid, foreign_tid], brands))]
        db.add_all(outlets); await db.flush()
        grants = {
            "cash": ["pos.cash.manage"], "shift": ["pos.shift.manage"], "lookup": ["pos.sell", "customers.lookup"],
            "seller": ["pos.sell", "stock.view"], "viewer": ["stock.view"],
            "receiver": ["stock.view", "stock.receive"], "adjuster": ["stock.view", "stock.adjust"],
            "refund": ["pos.sell", "pos.refund"], "approver": ["pos.sell", "pos.refund.approve"],
            "discount": ["pos.sell", "pos.discount.override"], "history": ["stock.view", "sales.detail.view"],
            "kitchen": ["pos.kitchen"], "hris": ["hris.self"], "recipe": ["stock.view", "stock.receive", "pos.sell"],
        }
        users, roles = {}, {}
        for name, permissions in grants.items():
            role = Role(id=uuid4(), tenant_id=tid, name=f"QA {name}", scope="outlet", permissions={"access_policy": {
                "version": 1, "permissions": {p: True for p in permissions}, "outlet_ids": [str(outlets[1 if name == "recipe" else 0].id)]}})
            db.add(role); await db.flush(); roles[name] = role
            users[name] = User(id=uuid4(), tenant_id=tid, phone=f"qa-{uuid4().hex}", full_name=f"QA {name}", role_id=role.id)
        users["owner"] = User(id=uuid4(), tenant_id=tid, phone=f"qa-{uuid4().hex}", full_name="QA owner", is_superuser=True)
        users["legacy"] = User(id=uuid4(), tenant_id=tid, phone=f"qa-{uuid4().hex}", full_name="QA legacy")
        db.add_all(users.values()); await db.flush()
        products = [Product(id=uuid4(), brand_id=b.id, name=f"QA item {i}", base_price=15000, buy_price=7000,
            stock_enabled=True, stock_qty=100, sold_total=900, sold_today=99) for i, b in enumerate(brands)]
        db.add_all(products); await db.flush()
        ingredient = Ingredient(id=uuid4(), brand_id=brands[1].id, name="QA flour", tracking_mode="simple", base_unit="gram", unit_type="WEIGHT", buy_price=50000, buy_qty=1000, cost_per_base_unit=50)
        db.add(ingredient); await db.flush()
        recipe = Recipe(id=uuid4(), product_id=products[1].id, is_active=True)
        db.add(recipe); await db.flush()
        db.add_all([RecipeIngredient(id=uuid4(), recipe_id=recipe.id, ingredient_id=ingredient.id, quantity=10, quantity_unit="gram"),
            OutletStock(id=uuid4(), outlet_id=outlets[1].id, ingredient_id=ingredient.id, computed_stock=1000, crdt_positive={"qa": 1000}, crdt_negative={})])
        customer = Customer(id=uuid4(), tenant_id=tid, name="Literal%name", phone="628111111111", email="private@example.invalid", notes="private", total_spent=900000)
        foreign_customer = Customer(id=uuid4(), tenant_id=foreign_tid, name="Literal%name", phone="628222222222")
        db.add_all([customer, foreign_customer])
        paid_tab = Tab(id=uuid4(), outlet_id=outlets[0].id, tab_number="QA-" + uuid4().hex, opened_at=datetime.now(timezone.utc),
            opened_by=users["owner"].id, closed_by=users["owner"].id, status="paid", total_amount=50, paid_amount=50)
        db.add(paid_tab); await db.flush()
        tab_payment = Payment(id=uuid4(), outlet_id=outlets[0].id, tab_id=paid_tab.id, amount_due=50, amount_paid=50, payment_method="cash", status="paid")
        handled = Order(id=uuid4(), outlet_id=outlets[0].id, order_number="QA-" + uuid4().hex, display_number=800,
            source="storefront", status="completed", user_id=users["owner"].id, accepted_by=users["lookup"].id, subtotal=0, total_amount=0)
        db.add_all([tab_payment, handled]); await db.flush()
        foreign_payment = Payment(id=uuid4(), outlet_id=outlets[0].id, order_id=handled.id, amount_due=0, amount_paid=0, payment_method="cash", status="paid")
        invoice_id = uuid4()
        await db.execute(text("INSERT INTO invoices (id, tenant_id, invoice_number, amount_due, amount_remaining) VALUES (:id, :tenant, :number, 100, 0)"), {"id": invoice_id, "tenant": tid, "number": "QA-" + uuid4().hex})
        billing_payment = Payment(id=uuid4(), outlet_id=outlets[0].id, invoice_id=invoice_id, amount_due=100, amount_paid=100, payment_method="cash", status="paid")
        db.add_all([foreign_payment, billing_payment]); await db.commit()
    with patch.object(deps, "get_redis_client", AsyncMock(return_value=Redis())):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://qa") as client:
            async def call(method, path, who="seller", body=None, params=None, status=200):
                response = await client.request(method, "/api/v1" + path, json=body, params=params,
                    headers={"Authorization": "Bearer " + create_access_token(users[who].id), "X-Tenant-ID": str(tid)})
                assert response.status_code == status, (method, path, who, status, response.status_code, response.text)
                return response.json()

            oid, bid, pid = str(outlets[0].id), str(brands[0].id), str(products[0].id)
            def order_body(product=pid, outlet=oid, discount=0):
                return {"id": str(uuid4()), "outlet_id": outlet, "order_type": "takeaway", "subtotal": 9999999,
                    "discount_amount": discount, "items": [{"product_id": product, "quantity": 1, "unit_price": 15000, "total_price": 15000}]}
            for who in ("seller", "viewer", "receiver"):
                data = (await call("GET", "/products/", who, params={"outlet_id": oid}))["data"]
                assert len(data) == 1 and data[0]["buy_price"] is None and data[0]["sold_total"] is None
                available = (await call("GET", "/outlets/", who))["data"]
                assert [r["id"] for r in available] == [oid]
                await call("GET", f"/products/{products[1].id}", who, status=404)
                await call("GET", "/products/", who, params={"outlet_id": str(outlets[1].id)}, status=404)
                await call("GET", "/products/", who, status=422)
            await call("POST", "/orders/", "viewer", order_body(), status=403)
            await call("POST", "/orders/", body=order_body(str(products[1].id)), status=404)
            await call("POST", "/orders/", body=order_body(discount=4500), status=403)
            forged = order_body(); forged["items"][0].update(unit_price=1, total_price=1)
            await call("POST", "/orders/", body=forged, status=403)
            await call("POST", "/orders/", "discount", order_body(discount=4500))
            sale_body = order_body()
            sale = (await call("POST", "/orders/", body=sale_body))["data"]
            replay = (await call("POST", "/orders/", body=sale_body))["data"]
            assert sale["id"] == replay["id"] and Decimal(sale["subtotal"]) == 15000
            await call("POST", f"/products/{pid}/restock", body={"outlet_id": oid, "quantity": 5}, status=403)
            await call("POST", f"/products/{pid}/restock", "receiver", {"outlet_id": oid, "quantity": 5, "unit_buy_price": 1}, status=403)
            await call("POST", f"/products/{pid}/restock", "receiver", {"outlet_id": oid, "quantity": 5})
            await call("POST", f"/products/{pid}/stock-count", "receiver", {"outlet_id": oid, "counted_qty": 100}, status=403)
            await call("POST", f"/products/{pid}/stock-count", "adjuster", {"outlet_id": oid, "counted_qty": 100})
            print("PASS read/action grants, canonical price/discount, order replay and stock actions")

            await call("POST", "/payments/", body={"outlet_id": oid, "amount_due": 15000, "amount_paid": 15000, "payment_method": "cash"}, status=403)
            await call("POST", "/payments/", body={"outlet_id": oid, "order_id": sale["id"], "amount_due": 1, "amount_paid": 1, "payment_method": "cash"}, status=422)
            await call("POST", "/payments/", body={"outlet_id": oid, "order_id": sale["id"], "amount_due": 99999, "amount_paid": 99999, "payment_method": "cash"}, status=422)
            own_payment = (await call("POST", "/payments/", body={"outlet_id": oid, "order_id": sale["id"], "amount_due": 15000,
                "amount_paid": 15000, "payment_method": "cash", "idempotency_key": str(uuid4())}))["data"]
            assert own_payment["status"] == "paid"
            await call("GET", f"/orders/{handled.id}", params={"order_id": sale["id"]}, status=404)
            await call("GET", f"/payments/{foreign_payment.id}", params={"order_id": sale["id"]}, status=404)
            await call("GET", f"/payments/{foreign_payment.id}", params={"payment_id": own_payment["id"]}, status=404)
            await call("GET", f"/payments/{billing_payment.id}", "history", status=403)
            await call("POST", "/payments/refunds", "refund", {"payment_id": str(billing_payment.id), "amount": 1, "reason": "QA billing"}, status=403)
            await call("GET", f"/payments/{tab_payment.id}", status=403)
            await call("GET", f"/payments/{tab_payment.id}", "history")
            await call("GET", f"/orders/{handled.id}", "lookup")
            await call("GET", f"/orders/{handled.id}", status=403)
            own_history = (await call("GET", "/orders/", "lookup", params={"outlet_id": oid}))["data"]
            assert any(row["id"] == str(handled.id) for row in own_history)
            await call("GET", f"/orders/{sale['id']}", "viewer", status=403)
            await call("GET", f"/orders/{sale['id']}", "discount", status=403)
            await call("GET", f"/orders/{sale['id']}", "history")
            await call("PUT", f"/orders/{sale['id']}/status", body={"status": "cancelled", "row_version": 0}, status=403)
            await call("POST", "/payments/refunds", body={"payment_id": own_payment["id"], "amount": 1000, "reason": "QA partial"}, status=403)
            refund = (await call("POST", "/payments/refunds", "refund", {"payment_id": own_payment["id"], "amount": 1000, "reason": "QA partial"}))["data"]
            await call("POST", f"/payments/refunds/{refund['id']}/approve", "refund", {"row_version": refund["row_version"]}, status=403)
            await call("POST", f"/payments/refunds/{refund['id']}/approve", "approver", {"row_version": refund["row_version"]})
            shift = (await call("GET", "/shifts/current", params={"outlet_id": oid}))["data"]
            assert shift["starting_cash"] is None and shift["total_cash_sales"] is None and shift["cash_payments"] == []
            await call("POST", f"/shifts/{shift['id']}/close", body={"ending_cash": 15000}, status=403)
            await call("POST", "/devices/register", "viewer", {"outlet_id": oid, "fcm_token": "qa", "device_type": "kasir"}, status=403)
            activity = (await call("POST", f"/shifts/{shift['id']}/activities", "cash", {"activity_type": "expense", "amount": 2000, "description": "QA water"}))["data"]
            assert activity["amount"] == 2000
            cash = (await call("GET", f"/shifts/{shift['id']}/activities", "cash"))["data"]
            assert cash["activities"][0]["amount"] == 2000 and cash["cash_payments"] == []
            await call("POST", f"/shifts/{shift['id']}/activities", "cash", {"activity_type": "expense", "amount": -1, "description": "QA"}, status=422)
            await call("GET", "/shifts/uncounted", "cash", params={"outlet_id": oid}, status=403)
            await call("POST", f"/shifts/{shift['id']}/activities", "shift", {"activity_type": "expense", "amount": 1, "description": "QA"}, status=403)
            assert (await call("GET", f"/shifts/{shift['id']}/review", "shift"))["data"] == []
            await call("GET", "/customers/pos-lookup", params={"outlet_id": oid, "search": "Literal"}, status=403)
            matches = (await call("GET", "/customers/pos-lookup", "lookup", params={"outlet_id": oid, "search": "Literal%"}))["data"]
            assert len(matches) == 1 and set(matches[0]) == {"id", "name", "phone"}
            assert matches[0]["id"] == str(customer.id) and matches[0]["phone"] != customer.phone
            assert (await call("GET", "/customers/pos-lookup", "lookup", params={"outlet_id": oid, "search": "%%%"}))["data"] == []
            await call("GET", "/customers/pos-lookup", "lookup", params={"outlet_id": oid, "search": "Li"}, status=422)
            await call("GET", "/orders/kitchen", params={"outlet_id": oid}, status=403)
            kitchen = (await call("GET", "/orders/kitchen", "kitchen", params={"outlet_id": oid}))["data"]
            assert any(row["id"] == sale["id"] for row in kitchen["active"])
            await call("POST", f"/orders/{sale['id']}/kitchen-status", "kitchen", {"status": "done"})
            await call("POST", "/devices/register", body={"outlet_id": oid, "fcm_token": "qa-" + uuid4().hex, "device_type": "kasir", "device_name": "QA device"})
            sender = AsyncMock(return_value={"ok": ["qa-device"]})
            with patch.object(fcm, "enabled", return_value=True), patch.object(fcm, "send_to_tokens", sender):
                assert await fcm.notify_outlet(outlets[0].id, title="QA", body="QA", data={"type": "pesanan_online", "order_id": sale["id"]}) == 1
                assert sender.await_count == 1
                sender.reset_mock()
                assert await fcm.notify_outlet(outlets[0].id, title="QA", body="QA", data={"type": "reservasi"}) == 0
                sender.assert_not_awaited()
            print("PASS paid-history isolation, refund request/approval separation and blind drawer")

            for table in ("orders", "products", "categories", "payments", "shifts", "outlet_stock", "ingredients", "recipe_hpp"):
                result = await call("POST", "/sync/", body={"node_id": "qa:node", "outlet_id": oid,
                    "changes": {table: [{"id": str(uuid4())}]}}, status=403)
                assert result["detail"]["code"] == "OFFLINE_SYNC_REVIEW_REQUIRED"
            viewer = await call("POST", "/sync/", "viewer", {"node_id": "qa:node", "outlet_id": oid, "changes": {}})
            assert viewer["changes"]["orders"] == viewer["changes"]["payments"] == viewer["changes"]["shifts"] == []
            assert viewer["changes"]["products"][0]["buy_price"] is None and viewer["changes"]["recipe_hpp"] == []
            seller = await call("POST", "/sync/", body={"node_id": "qa:node", "outlet_id": oid, "changes": {}, "limit": 10})
            assert {r["user_id"] for r in seller["changes"]["orders"]} == {str(users["seller"].id)}
            assert seller["access"]["offline_pos_allowed"] is False
            await call("POST", "/sync/", body={"node_id": "qa:node", "outlet_id": str(outlets[1].id), "changes": {}}, status=404)
            await call("POST", "/sync/", body={"node_id": "qa:node", "outlet_id": str(outlets[2].id), "changes": {}}, status=404)
            await call("POST", "/sync/", body={"node_id": "qa:node", "outlet_id": oid, "cursor_hlc": "100:0:qa", "access_version": "stale", "changes": {}}, status=409)
            print("PASS all sync push tables fail before mutation, scoped pull and changed pagination grants")

            recipe_oid = str(outlets[1].id)
            recipe_sale = (await call("POST", "/orders/", "recipe", order_body(str(products[1].id), recipe_oid)))["data"]
            await call("PUT", f"/orders/{recipe_sale['id']}/status", "recipe", {"status": "cancelled", "row_version": recipe_sale["row_version"]})
            await call("POST", f"/ingredients/{ingredient.id}/restock", "recipe", {"outlet_id": recipe_oid, "quantity": 50})
            ingredient_data = (await call("GET", "/ingredients/", "recipe", params={"outlet_id": recipe_oid, "brand_id": str(brands[1].id)}))["data"]
            assert ingredient_data[0]["cost_per_base_unit"] is None and ingredient_data[0]["current_stock"] == 1050
            class PubSub:
                async def subscribe(self, *args): pass
                async def get_message(self, **kwargs): return {"data": '{"type":"private","amount":999}'}
                async def unsubscribe(self, *args): pass
                async def close(self): pass
            class StreamRedis:
                def pubsub(self): return PubSub()
            async with AsyncSessionLocal() as stream_db:
                await stream_db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tid)})
                actor = await stream_db.get(User, users["seller"].id)
                request = Request({"type": "http", "method": "GET", "path": "/orders/stream", "headers": []})
                request.state.access = await resolve_access(stream_db, actor)
                request.state.auth_claims = {"sub": str(actor.id)}
                request.state.auth_token = "synthetic-stream"
                with patch.object(online_orders, "_redis", StreamRedis()):
                    stream = await stream_orders(request, outlets[0].id, stream_db, actor)
                    iterator = stream.body_iterator
                    assert "hello" in await anext(iterator)
            async with Admin() as db:
                stored = await db.get(OutletStock, (await db.scalar(select(OutletStock.id).where(OutletStock.ingredient_id == ingredient.id))))
                assert stored.computed_stock == 1050
                event_count = await db.scalar(select(func.count()).select_from(Event).where(Event.event_type == "stock.ingredient_sale", Event.outlet_id == outlets[1].id))
                assert event_count == 1
                role = await db.get(Role, roles["seller"].id)
                role.permissions = {"access_policy": {"version": 1, "permissions": {"hris.self": True}, "outlet_ids": [oid]}}
                await db.commit()
            with patch.object(online_orders, "_redis", StreamRedis()):
                assert "access_revoked" in await anext(iterator)
                try:
                    await anext(iterator)
                    raise AssertionError("Revoked stream stayed open")
                except StopAsyncIteration:
                    pass
            print("PASS SSE revocation stops before a queued event can disclose payload")
            sender.reset_mock()
            with patch.object(fcm, "enabled", return_value=True), patch.object(fcm, "send_to_tokens", sender):
                assert await fcm.notify_outlet(outlets[0].id, title="QA", body="QA", data={"type": "pesanan_online", "order_id": sale["id"]}) == 0
                sender.assert_not_awaited()
            closed = await call("POST", f"/shifts/{shift['id']}/close", "shift", {"ending_cash": 999})
            assert closed["message"] == "Hitungan kas tercatat" and closed["data"]["variance_status"] is None
            await call("POST", "/orders/", body=order_body(), status=403)
            await call("POST", "/sync/", body={"node_id": "qa:node", "outlet_id": oid, "changes": {}}, status=403)
            for route in ("/finance/accounts", "/recipes/", "/customers/workspace", "/reports/daily"):
                await call("GET", route, "viewer", status=403)
            await call("GET", "/products/", "legacy")
            print("PASS recipe sale/cancel/receive stock invariants, immediate revocation and legacy compatibility")
    await engine.dispose(); await admin.dispose()


asyncio.run(main())
