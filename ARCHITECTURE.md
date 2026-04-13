# KASIRA PRO — Architecture Reference
# Baca ini SEBELUM coding fitur apapun yang menyentuh stock, recipe, tab, atau storefront.

## Kenapa File Ini Ada

Setiap sesi coding ketemu bug baru karena:
1. Logic stock ada di 3+ tempat yang harus konsisten
2. Recipe mode vs simple mode diverge di banyak code path
3. Sync Flutter ↔ Backend punya aturan sendiri
4. Gak ada single reference buat "gimana seharusnya"

**Rule: Kalau lo edit code di salah satu tempat yang disebut di sini, cek SEMUA tempat terkait.**

---

## Folder Structure

```
/var/www/kasira/
├── backend/                    # FastAPI (Python)
│   ├── api/routes/             # API endpoints
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic request/response
│   ├── services/               # Business logic
│   └── migrations/versions/    # Alembic migrations
├── app/                        # Next.js 14 Dashboard
│   ├── dashboard/              # Owner dashboard pages
│   ├── [slug]/                 # Public storefront pages
│   └── actions/api.ts          # Server actions → backend API
├── kasir_app/                  # Flutter POS + Dapur app
│   └── lib/
│       ├── core/database/      # Drift (SQLite) tables
│       ├── core/sync/          # CRDT sync engine
│       └── features/           # POS, orders, products, etc
└── .github/workflows/          # GitHub Actions (APK build)
```

---

## Stock System — CRITICAL: 2 Modes, Banyak Code Path

### Mode: `outlet.stock_mode`

| | Simple | Recipe |
|---|---|---|
| Track | `products.stock_qty` | `outlet_stock.computed_stock` per ingredient |
| Deduct on order | products.stock_qty -= qty | outlet_stock -= recipe_qty × order_qty |
| Restore on cancel | products.stock_qty += qty | outlet_stock += recipe_qty × order_qty |
| Display stock | products.stock_qty langsung | `min(ingredient_stock / recipe_qty)` per product |
| Restock | `POST /products/{id}/restock` | `POST /ingredients/{id}/restock` |

### SEMUA Code Path yang Modify Stock

Kalau lo edit salah satu, **cek semua yang lain**.

| Action | Simple Mode | Recipe Mode | File |
|--------|-------------|-------------|------|
| **Order create (online)** | `deduct_stock()` | `deduct_ingredients_for_product()` | `orders.py:182-203` |
| **Order cancel** | `restore_stock_on_cancel()` | `restore_ingredients_on_cancel()` | `orders.py:432-451` |
| **Sync offline order** | `svc_deduct_stock()` | ⚠️ calls `svc_deduct_stock` (simple only!) | `sync.py:76-89` |
| **Flutter offline order** | PNCounter on `products.crdtNegative` | Deduct `outletStocks.computedStock` | `cart_provider.dart:300-327` |
| **Product restock** | `products.stock_qty += qty` | N/A (use ingredient restock) | `products.py:85-` |
| **Ingredient restock** | N/A | `outlet_stock.computed_stock += qty` | `ingredients.py:295-383` |
| **Display stock (API)** | `products.stock_qty` | `compute_recipe_stock()` | `products.py:278-301` |
| **Display stock (storefront)** | `products.stock_qty` | Inline recipe calc | `connect.py:140-199` |
| **Display stock (Flutter offline)** | `products.stockQty` | `_computeRecipeStockLocal()` | `products_provider.dart:108-` |

### ⚠️ KNOWN BUG: sync.py Offline Order Stock

`sync.py:76-89` — saat offline order di-sync ke server, hanya call `svc_deduct_stock` (simple mode). **Recipe mode deduction belum dihandle di sync path.** Ini karena Flutter offline sudah deduct locally, dan sync mengandalkan CRDT merge. Tapi kalau device lain juga transact, bisa drift.

### ⚠️ DUPLICATE LOGIC: compute_recipe_stock

Logic hitung "berapa porsi tersedia" ada di **2 tempat** yang harus identik:
1. `backend/api/routes/products.py:26-81` — `compute_recipe_stock()`
2. `backend/api/routes/connect.py:152-198` — inline di storefront

**RULE**: Kalau edit satu, edit yang lain. Atau lebih baik: refactor ke `services/ingredient_stock_service.py`.

### Recipe Ingredient Filter

Saat hitung stock dari recipe, **WAJIB** filter:
```python
ri.deleted_at is None           # recipe_ingredient not deleted
and not ri.is_optional          # skip optional ingredients
and ri.quantity > 0             # has valid quantity
and ri.ingredient is not None   # ingredient exists
and ri.ingredient.deleted_at is None  # ingredient not deleted
```

Bug yang pernah terjadi: ingredient dihapus tapi recipe masih reference → ghost stock.

---

## Sync Architecture (Flutter ↔ Backend)

### Direction

| Data | Direction | Method | Conflict Strategy |
|------|-----------|--------|-------------------|
| Categories | Server → Flutter | Read-only pull | N/A |
| Products | Bidirectional | CRDT merge (PNCounter for stock) | `hlc_lww` + PNCounter merge |
| Orders | Bidirectional | Push unsynced, pull server | `financial_strict` |
| Order Items | Bidirectional | Push unsynced, pull server | `hlc_lww` |
| Payments | Bidirectional | Push, pull | `financial_strict` |
| Shifts | Bidirectional | Push, pull | `financial_strict` |
| Cash Activities | Bidirectional | Push, pull | `financial_strict` |
| **Ingredients** | **Server → Flutter** | **Read-only pull** | N/A |
| **Recipes** | **Server → Flutter** | **Read-only pull** | N/A |
| **Recipe Ingredients** | **Server → Flutter** | **Read-only pull** | N/A |
| **Outlet Stock** | **Server → Flutter** | **Read-only pull** (PNCounter on server) | PNCounter merge |

### Sync Endpoint: `POST /api/v1/sync/`

Request: `{node_id, last_sync_hlc, changes: {categories, products, orders, ...}}`
Response: `{last_sync_hlc, changes: {...}, stock_mode}`

**`stock_mode` direturn di response** supaya Flutter selalu up-to-date kalau owner ganti mode di dashboard.

### Flutter Storage

| Key | Storage | Set When |
|-----|---------|----------|
| `access_token` | SecureStorage | Login |
| `tenant_id` | SecureStorage | Login |
| `outlet_id` | SecureStorage | Login |
| `stock_mode` | SecureStorage | Login + every sync |
| `device_node_id` | SharedPreferences | First launch (format: `device_${timestamp}`) |
| `last_sync_hlc` | SharedPreferences | Every successful sync |

### Drift DB Schema (v4)

Tables: Products, Orders, OrderItems, Payments, Shifts, CashActivities, Ingredients, Recipes, RecipeIngredients, **OutletStocks**

Migration path: v1 → v2 (CRDT columns) → v3 (ingredient/recipe tables) → v4 (outlet_stock table)

---

## CRDT Sync Engine — Deep Reference

### Files yang Terlibat

| File | Apa | Kapan Perlu Baca |
|------|-----|------------------|
| `backend/services/crdt.py` | HLC + PNCounter implementation | Kalau edit sync logic apapun |
| `backend/services/sync.py` | `process_table_sync`, `process_stock_sync`, `get_table_changes` | Kalau edit cara data masuk/keluar |
| `backend/api/routes/sync.py` | Sync endpoint (push+pull orchestration) | Kalau tambah table baru ke sync |
| `kasir_app/lib/core/utils/hlc.dart` | HLC implementation (Flutter) | Kalau edit sync di Flutter |
| `kasir_app/lib/core/utils/pn_counter.dart` | PNCounter implementation (Flutter) | Kalau edit stock logic offline |
| `kasir_app/lib/core/sync/sync_service.dart` | Flutter sync client | Kalau edit apa yang di-push/pull |
| `kasir_app/lib/core/sync/sync_provider.dart` | Riverpod provider for SyncService | Dependency injection |

### HLC (Hybrid Logical Clock)

**Format string:** `timestamp:counter:node_id`
- `timestamp`: milliseconds since epoch (int)
- `counter`: monotonic counter for same-millisecond events (int)
- `node_id`: unique identifier — server: `server:{outlet_id}`, device: `device_{timestamp}`

**Contoh:** `1775895258086:1:server:fbc68df5-5613-4197-929d-395ddb903a9e`

**Operasi penting:**

```
generate(node_id)  → HLC(now_ms, 0, node_id)
compare(a, b)      → bandingkan timestamp → counter → node_id (lexicographic)
receive(remote)    → advance clock: max(local, remote) + increment counter
```

**Clock skew protection (backend only):** Kalau client kirim timestamp > 5 menit di masa depan, server cap ke `now + 5min`. Flutter TIDAK punya proteksi ini.

**Kenapa HLC bukan wall clock:**
- Wall clock bisa loncat mundur (NTP sync, timezone change)
- HLC monotonic: timestamp selalu >= previous, counter breaks ties
- Node ID sebagai tiebreaker terakhir (lexicographic)

### PNCounter (Positive-Negative Counter)

**Data structure:**
```json
crdt_positive: {"server:outlet123": 100, "device_abc": 20}   // restock
crdt_negative: {"device_abc": 5, "device_xyz": 8}            // sales
computed_stock = sum(positive) - sum(negative) = 120 - 13 = 107
```

**Merge rule: MAX per node_id**
```
local:  {"device_a": 5, "device_b": 3}
remote: {"device_a": 4, "device_b": 7, "device_c": 2}
merged: {"device_a": 5, "device_b": 7, "device_c": 2}  ← max per key
```

**Kenapa conflict-free:**
- Setiap device HANYA increment counter miliknya sendiri
- Device A: `negative[device_a] += qty`
- Device B: `negative[device_b] += qty`
- Merge ambil max → gak pernah kehilangan increment dari device manapun

**Contoh multi-device:**
```
Server awal: positive={server:100}, negative={}  → stock=100

Device A (offline): sell 5 → negative={device_a:5}  → local stock=95
Device B (offline): sell 3 → negative={device_b:3}  → local stock=97
Server: restock 20 → positive={server:120}          → stock=120

Device A sync:
  push: negative={device_a:5}
  server merge: negative={device_a:5}
  server stock: 120-5=115

Device B sync:
  push: negative={device_b:3}
  server merge: negative={device_a:5, device_b:3}
  server stock: 120-5-3=112  ← BENAR, gak ada yang hilang

Device A pull:
  receive: positive={server:120}, negative={device_a:5, device_b:3}
  local merge: positive={server:120}, negative={device_a:5, device_b:3}
  local stock: 120-5-3=112  ← sama dengan server
```

### Conflict Strategies

**`hlc_lww` (Last-Write-Wins) — default untuk Categories, Products, Order Items:**
```
if client_hlc > server_hlc:
    server record = client data   // client wins
else:
    keep server record            // server wins (silent discard)
```

**`financial_strict` — untuk Orders, Payments, Shifts, Cash Activities:**
```
if server.status in ["paid", "completed", "refunded", "cancelled"]:
    REJECT client changes         // financial record immutable
else:
    apply hlc_lww                 // normal LWW
```

**Kenapa financial_strict:**
- Order sudah dibayar → client offline gak boleh bisa ubah
- Payment completed → gak boleh di-overwrite
- Mencegah financial inconsistency dari stale offline data

### Sync Flow Detail

**PUSH (client → server) — `backend/services/sync.py:process_table_sync`:**

```
1. Parse client HLC dari record
2. Advance server HLC via receive(client_hlc)
3. SELECT existing record FOR UPDATE (row lock)
4. Cek authorization: record.outlet_id == user's outlet_id?
5. Cek financial_strict: server status final? → skip
6. Compare HLC: client > server? → update, else skip
7. Apply field-by-field update (skip created_at, updated_at, row_version, hlc)
8. Map is_deleted → deleted_at
9. Increment row_version
10. Flush (bukan commit — commit di akhir setelah semua table)
```

**Kalau record baru (INSERT):**
```
1. Validate ID gak collision dengan tenant lain
2. Inject filter_kwargs (outlet_id, brand_id)
3. Map is_deleted → deleted_at
4. Set row_version = 1
5. Insert
```

**PUSH stock — `backend/services/sync.py:process_stock_sync`:**
```
1. Parse client PNCounter (crdt_positive, crdt_negative)
2. SELECT existing outlet_stock FOR UPDATE
3. Merge: merged_p = PNCounter.merge(server_p, client_p)
4. Merge: merged_n = PNCounter.merge(server_n, client_n)
5. Recompute: computed_stock = max(0, sum(merged_p) - sum(merged_n))
6. Update row_version
```

**PULL (server → client) — `backend/services/sync.py:get_table_changes`:**
```
1. Filter by tenant (brand_id, outlet_id)
2. If last_sync_hlc provided:
   WHERE updated_at > hlc.timestamp
      OR (updated_at == hlc.timestamp AND row_version > hlc.counter)
3. Attach HLC to each record: HLC(updated_at_ms, row_version, server_node_id)
4. Return records
```

**Flutter apply server changes — `sync_service.dart:_applyServerChanges`:**
```
1. Transaction start
2. For each product:
   - If exists locally AND stock_enabled → PNCounter merge (max per node)
   - Else → insertOnConflictUpdate (replace)
3. For orders, payments, shifts → insertOnConflictUpdate (server wins)
4. For ingredients, recipes, recipe_ingredients → insertOnConflictUpdate (read-only)
5. For outlet_stock → insertOnConflictUpdate (read-only from server)
6. Transaction commit
```

### Idempotency — Mencegah Double-Deduction

**Problem:** Device sync → network timeout → retry → server deduct stock 2x

**Solution 1 — Event Store Check (backend):**
```python
# stock_service.py
async def _is_sale_already_recorded(db, product_id, order_id):
    return await db.execute(
        select(Event).where(
            Event.stream_id == f"product:{product_id}",
            Event.event_type == "stock.sale",
            Event.event_data["order_id"].astext == str(order_id),
        )
    ).scalar_one_or_none() is not None
```
Sebelum deduct, cek event store: kalau `stock.sale` event dengan `order_id` ini sudah ada → skip.

**Solution 2 — isSynced Flag (Flutter):**
```dart
// Setelah sync berhasil:
await _markAsSynced(products: unsyncedProducts, ...);
// Next sync: hanya kirim record dengan isSynced=false
```

**Solution 3 — Idempotency Key (Storefront orders):**
```json
POST /connect/{slug}/order
{"idempotency_key": "unique-key-123", ...}
```
Server cek: kalau order dengan key ini sudah ada → return existing order.

### Edge Cases yang Harus Dipahami

**1. Device offline 3 hari, sync:**
- Push: semua unsynced changes (bisa ratusan records)
- Pull: semua server changes since last_sync_hlc (bisa ribuan records)
- PNCounter merge tetap benar karena conflict-free
- HLC incremental query efisien — gak full table scan

**2. Dua device edit product yang sama offline:**
- Device A: edit name "Kopi" → "Kopi Premium" at HLC 100
- Device B: edit price 20000 → 25000 at HLC 200
- Device A sync: server updates name (HLC 100)
- Device B sync: server compares HLC 200 > 100 → overwrites SEMUA fields
- **Result: name kembali ke "Kopi" (dari device B yang gak edit name)**
- **Ini LWW limitation — gak ada field-level merge**

**3. Order dibuat offline, sync, tapi stock sudah habis di server:**
- sync.py wraps stock deduction in try-except (line 88-89)
- Kalau stock insufficient → exception caught → sync TETAP berhasil
- Order masuk tapi stock jadi negatif? TIDAK — CHECK constraint di DB level
- **Result: order masuk ke server tapi stock gak di-deduct. Perlu manual reconciliation.**

**4. `financial_strict` reject scenario:**
- Device A offline, edit order status pending→preparing
- Meanwhile server: order sudah dibayar (status=paid)
- Device A sync: server checks status=paid → REJECT client change
- Device A pull: receive order with status=paid (overwrites local)
- **Result: correct — financial state preserved**

### ⚠️ Known Sync Issues

| Issue | Detail | Impact |
|-------|--------|--------|
| **sync.py stock deduction hanya simple mode** | Line 76-89: saat order items sync dari offline, hanya call `svc_deduct_stock` (simple). Recipe mode ingredient deduction gak di-trigger. | Offline order di recipe mode: stock gak di-deduct server-side saat sync. Bergantung pada Flutter local deduction + CRDT merge. |
| **LWW overwrites semua field** | Kalau 2 device edit field berbeda di record yang sama, yang HLC lebih baru menang untuk SEMUA field | Bisa kehilangan edit dari device lain. Gak ada field-level CRDT. |
| **No clock skew protection di Flutter** | Backend punya max 5min cap, Flutter tidak | Kalau device clock salah jauh, bisa bikin HLC yang "dari masa depan" → selalu menang di LWW |
| **outlet_stock hanya read-only pull ke Flutter** | Flutter gak push outlet_stock changes ke server | Offline ingredient deduction di Flutter gak sync balik. Bergantung pada order sync → server re-deduct. |

---

## Tab/Split Bill Flow

### Status Flow
```
open → asking_bill → splitting → paid
  ↓                      ↓
cancelled           (auto-close when all splits paid)
```

### Split Methods
| Method | Endpoint | Logic |
|--------|----------|-------|
| Equal | `POST /tabs/{id}/split/equal` | total ÷ num_people, remainder distributed |
| Per-Item | `POST /tabs/{id}/split/per-item` | Assign order items to people, proportional tax/service |
| Custom | `POST /tabs/{id}/split/custom` | Manual amounts, must sum to total |
| Full | `POST /tabs/{id}/pay-full` | 1 person pays all |

### Pay Split: `POST /tabs/{id}/splits/{split_id}/pay`
- `row_version` = **split's row_version**, bukan tab's
- Saat semua splits paid → tab auto-close ke `paid`
- Semua linked orders auto-complete

### ⚠️ KNOWN: Tab Add Order Needs Flush
`tabs.py` — setelah `order.tab_id = tab.id`, **HARUS `await db.flush()`** sebelum `_recalculate_tab()`. Tanpa flush, query gak lihat order baru → total=0.

---

## Reservation System

### Status Flow
```
pending → confirmed → seated → completed
  ↓          ↓          ↓
cancelled  cancelled  no_show
```

### Key Endpoints
| Action | Endpoint | Note |
|--------|----------|------|
| Create (staff) | `POST /reservations/?outlet_id=` | outlet_id as query param |
| Create (public) | `POST /connect/{slug}/reservation` | Auto-assign table |
| Slots | `GET /connect/{slug}/reservation/slots?reservation_date=` | Returns 30min slots |
| Confirm | `PUT /reservations/{id}/confirm` | Skipped if auto_confirm=true |
| Seat | `PUT /reservations/{id}/seat` | |
| Complete | `PUT /reservations/{id}/complete` | |
| Cancel | `PUT /reservations/{id}/cancel` | |
| No-show | `PUT /reservations/{id}/no-show` | |

### Settings: `GET/PUT /reservations/settings/{outlet_id}`
- `auto_confirm` — kalau true, reservasi langsung confirmed (skip pending)
- `slot_duration_minutes` — default 120
- `opening_hour` / `closing_hour` — slot range

---

## Storefront (Connect)

### Public Endpoints (no auth)
| Endpoint | Purpose |
|----------|---------|
| `GET /connect/{slug}` | Full storefront data (cached 60s Redis) |
| `POST /connect/{slug}/order` | Create order (needs `idempotency_key`, items use `qty` not `quantity`) |
| `GET /connect/{slug}/tables` | Available tables |
| `POST /connect/{slug}/booking` | Legacy booking |
| `POST /connect/{slug}/reservation` | Create reservation |
| `GET /connect/{slug}/reservation/slots?reservation_date=` | Available slots |
| `GET /connect/orders/{order_id}` | Order status |
| `GET /connect/bookings/{booking_id}` | Booking status |

### Storefront Product Visibility

**Semua produk active muncul**. Yang stock=0 diberi `is_available: false`.
Frontend harus handle: show semua, grey-out/label "Habis" untuk `is_available=false`.

**⚠️ Redis cache `connect:storefront:{slug}`** — expire 60 detik. Kalau update data dan mau instant reflect, harus clear cache manual atau tunggu expire.

---

## /me Endpoint

`GET /api/v1/auth/me` returns:
```json
{
  "id", "full_name", "phone", "tenant_id", "outlet_id",
  "is_active", "subscription_tier", "stock_mode"
}
```
Flutter dan Dashboard pakai ini buat tier gating dan stock mode detection.

---

## Tier Gating

| Feature | Starter | Pro | Business |
|---------|---------|-----|----------|
| POS, Orders, Payments | ✅ | ✅ | ✅ |
| Storefront (basic) | ✅ | ✅ | ✅ |
| Products, Categories CRUD | ✅ | ✅ | ✅ |
| Simple stock (deduct/restock) | ✅ | ✅ | ✅ |
| Shifts (buka/tutup + rekap) | ✅ | ✅ | ✅ |
| Basic reporting (revenue, daily) | ✅ | ✅ | ✅ |
| Reservasi + Booking | ❌ | ✅ | ✅ |
| Tab / Split Bill | ❌ | ✅ | ✅ |
| Recipe / Ingredient / HPP | ❌ | ✅ | ✅ |
| Recipe mode stock | ❌ | ✅ | ✅ |
| AI Chat (owner) | ❌ | ✅ | ✅ |
| Knowledge Graph | ❌ | ✅ | ✅ |
| Loyalty Points | ❌ | ✅ | ✅ |
| Multi-outlet | ❌ | ❌ | ✅ |

**Source of truth: ROADMAP.md FASE 2 = Starter, FASE 6 = Pro, Multi-outlet = Business.**

Backend enforces via `deps.require_pro_tier` dependency on route.
Dashboard enforces via `useProGuard()` hook.
Flutter should check `subscription_tier` from SecureStorage (bukan hanya `stock_mode`).

---

## Deploy Workflow

### Backend
```bash
# Edit file di /var/www/kasira/backend/
sudo docker cp <file> kasira-backend-1:/app/<file>
sudo docker restart kasira-backend-1
```
**⚠️** `docker compose up -d` recreates container → semua docker cp hilang → harus re-copy.

### Frontend (Dashboard)
```bash
docker compose build frontend
docker compose up -d frontend
```

### Flutter (APK)
```bash
git push origin main
# Trigger GitHub Actions: Build & Release Kasira Flutter APK
# Workflow runs: pub get → build_runner → flutter build apk
```

### Redis Cache Clear
```bash
sudo docker exec kasira-redis-1 redis-cli DEL "connect:storefront:{slug}"
sudo docker exec kasira-redis-1 redis-cli DEL "ai:context:{outlet_id}"
```

---

## Event Store

Semua stock mutation WAJIB append event ke `events` table:

| event_type | When |
|------------|------|
| `stock.sale` | Simple mode: order deducts product stock |
| `stock.ingredient_sale` | Recipe mode: order deducts ingredient stock |
| `stock.cancel_return` | Simple mode: order cancelled, stock restored |
| `stock.ingredient_cancel_return` | Recipe mode: order cancelled, ingredients restored |
| `stock.restock` | Product restocked |
| `stock.ingredient_restock` | Ingredient restocked |
| `ingredient.created` | New ingredient created |
| `ingredient.price_updated` | Ingredient buy price changed |
| `order.created` | New order |
| `payment.completed` | Payment successful |

---

## Bugs yang Pernah Ditemukan dan Diperbaiki

Daftar ini supaya gak terulang:

| Bug | Root Cause | Fix | Date |
|-----|-----------|-----|------|
| Tab add_order total=0 | `order.tab_id` belum flush sebelum recalculate query | `await db.flush()` sebelum `_recalculate_tab()` | 2026-04-13 |
| Cancel order gak restore ingredient stock | `restore_stock_on_cancel` cuma handle simple mode | Buat `restore_ingredients_on_cancel()` + branch di cancel handler | 2026-04-13 |
| Storefront show ghost stock dari deleted ingredients | `compute_recipe_stock` gak check `ingredient.deleted_at` | Add filter `ri.ingredient.deleted_at is None` | 2026-04-13 |
| `/me` gak return subscription_tier | Endpoint cuma return user fields | Add tenant query + return tier + stock_mode | 2026-04-13 |
| Flutter Drift query `&` operator error | Drift Expression<bool> gak support `&` | Use chained `.where()` calls | 2026-04-13 |
| Flutter gak tau recipe mode | `stock_mode` gak disimpan di Flutter | Save dari login response + sync response | 2026-04-13 |
| Flutter offline gak deduct ingredients | Cart provider cuma deduct product CRDT | Add `_deductIngredientStockOffline()` | 2026-04-13 |
| Storefront hide semua produk stok 0 | Filter `s > 0` exclude valid products | Show all, use `is_available` flag | 2026-04-13 |
