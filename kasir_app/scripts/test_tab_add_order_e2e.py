"""E2E jalur "isi meja → tambah pesanan", persis urutan yang dipanggil Flutter.

Mirror dari cart_provider.submitDineInOrder():
  GET  /tabs/by-table/{tableId}   → pakai ulang tab kalau ada
  POST /tabs/                      → kalau belum ada
  POST /orders/                    → bikin order (dine-in wajib table_id)
  POST /tabs/{tabId}/orders        → tempel order ke tab

Yang diuji: setelah pesanan kedua ditambahkan, apakah tab langsung mencerminkan
kedua order dan totalnya benar — ini bagian yang dilaporkan "pesanan terjadi
tapi nggak ke-input di meja".
"""
import asyncio, sys
import httpx
from sqlalchemy import select, text
from backend.core.database import AsyncSessionLocal
from backend.core.security import create_access_token
from backend.models.user import User

TENANT = "c620a7c0-8230-40bb-9327-fa8aa5851063"
OUTLET = "fbc68df5-5613-4197-929d-395ddb903a9e"
B = "http://localhost:8000/api/v1"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  ✅ {label}")
    else:
        fail += 1; print(f"  ❌ {label}  {detail}")


async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.current_tenant_id',:t,true)"), {"t": TENANT})
        u = (await db.execute(select(User).where(
            User.tenant_id == TENANT, User.deleted_at.is_(None)).limit(1))).scalar_one()
        tok = create_access_token(subject=str(u.id))
    H = {"Authorization": f"Bearer {tok}", "X-Tenant-ID": TENANT, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0, headers=H) as c:
        tables = (await c.get(f"{B}/tables/", params={"outlet_id": OUTLET})).json()["data"]
        free = [t for t in tables if t["status"] == "available"]
        if not free:
            print("SKIP: nggak ada meja available"); return
        table = free[0]
        prods = [p for p in (await c.get(f"{B}/products/", params={
            "brand_id": (await c.get(f"{B}/outlets/{OUTLET}")).json()["data"]["brand_id"]})).json()["data"]
            if p.get("is_active")][:2]
        if len(prods) < 2:
            print("SKIP: produk kurang dari 2"); return

        shift = await c.post(f"{B}/shifts/open", params={"outlet_id": OUTLET},
                             json={"starting_cash": 100000})
        shift_id = shift.json()["data"]["id"] if shift.status_code < 400 else None

        print(f"\nMeja: {table['name']}  produk: {prods[0]['name']}, {prods[1]['name']}")

        # ── 1. Buka meja: belum ada tab ──
        r = await c.get(f"{B}/tabs/by-table/{table['id']}", params={"outlet_id": OUTLET})
        check("meja kosong belum punya tab aktif", r.json().get("data") is None)

        r = await c.post(f"{B}/tabs/", params={"outlet_id": OUTLET}, json={
            "outlet_id": OUTLET, "table_id": table["id"], "guest_count": 3})
        check("buka tab", r.status_code < 400, r.text[:120])
        tab = r.json()["data"]; tab_id = tab["id"]
        check("guest_count kesimpan 3", tab["guest_count"] == 3, f"dapat {tab['guest_count']}")

        # ── 2. Pesanan pertama ──
        async def add_order(prod, qty):
            price = float(prod["base_price"]); total = price * qty
            ro = await c.post(f"{B}/orders/", json={
                "outlet_id": OUTLET, "order_type": "dine_in", "table_id": table["id"],
                "subtotal": total, "total_amount": total,
                "items": [{"product_id": prod["id"], "quantity": qty,
                           "unit_price": price, "total_price": total}]})
            if ro.status_code >= 400:
                return None, 0, ro.text[:140]
            oid = ro.json()["data"]["id"]
            rl = await c.post(f"{B}/tabs/{tab_id}/orders", json={"order_id": oid})
            return oid, total, (None if rl.status_code < 400 else rl.text[:140])

        oid1, t1, err = await add_order(prods[0], 2)
        check("pesanan #1 dibuat + ditempel ke tab", oid1 and not err, err or "")

        r = await c.get(f"{B}/tabs/{tab_id}")
        d = r.json()["data"]
        check("total tab = pesanan #1", abs(float(d["total_amount"]) - t1) < 1,
              f"tab={d['total_amount']} harusnya={t1}")
        check("tab mencatat 1 order", len(d.get("order_ids") or []) == 1,
              f"dapat {len(d.get('order_ids') or [])}")

        # ── 3. Pesanan KEDUA — ini skenario yang dilaporkan bug ──
        oid2, t2, err = await add_order(prods[1], 1)
        check("pesanan #2 dibuat + ditempel ke tab", oid2 and not err, err or "")

        r = await c.get(f"{B}/tabs/{tab_id}")
        d = r.json()["data"]
        check("total tab = #1 + #2 (langsung, tanpa perlu buka ulang)",
              abs(float(d["total_amount"]) - (t1 + t2)) < 1,
              f"tab={d['total_amount']} harusnya={t1+t2}")
        check("tab mencatat 2 order", len(d.get("order_ids") or []) == 2,
              f"dapat {len(d.get('order_ids') or [])}")

        # ── 4. Jalur yang dipakai grid Meja & tap meja ──
        r = await c.get(f"{B}/tabs/by-table/{table['id']}", params={"outlet_id": OUTLET})
        bt = r.json().get("data")
        check("by-table balikin tab yang sama", bt and bt["id"] == tab_id)
        check("by-table totalnya udah termasuk 2 pesanan",
              bt and abs(float(bt["total_amount"]) - (t1 + t2)) < 1,
              f"dapat {bt and bt['total_amount']}")

        r = await c.get(f"{B}/tabs/{tab_id}/items")
        items = r.json().get("data") or []
        check("item dua pesanan kebaca di tab", len(items) >= 2, f"dapat {len(items)}")

        r = await c.get(f"{B}/tables/", params={"outlet_id": OUTLET})
        me = [t for t in r.json()["data"] if t["id"] == table["id"]][0]
        check("status meja jadi occupied", me["status"] == "occupied", f"dapat {me['status']}")

        # ── Bersih-bersih ──
        await c.post(f"{B}/tabs/{tab_id}/cancel")
        if shift_id:
            await c.post(f"{B}/shifts/{shift_id}/close", json={"ending_cash": 100000})

    print(f"\n══ {ok} lolos, {fail} gagal ══")
    sys.exit(1 if fail else 0)

asyncio.run(main())
