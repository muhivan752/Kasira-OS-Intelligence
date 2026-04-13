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

| Data | Direction | Method |
|------|-----------|--------|
| Categories | Server → Flutter | Read-only pull |
| Products | Bidirectional | CRDT merge (PNCounter for stock) |
| Orders | Flutter → Server | Push unsynced, pull server orders |
| Order Items | Flutter → Server | Push unsynced, pull server items |
| Payments | Flutter → Server | Push, pull |
| Shifts | Flutter → Server | Push, pull |
| Cash Activities | Flutter → Server | Push, pull |
| **Ingredients** | **Server → Flutter** | **Read-only pull** |
| **Recipes** | **Server → Flutter** | **Read-only pull** |
| **Recipe Ingredients** | **Server → Flutter** | **Read-only pull** |
| **Outlet Stock** | **Server → Flutter** | **Read-only pull** |

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
| `device_node_id` | SharedPreferences | First launch |
| `last_sync_hlc` | SharedPreferences | Every sync |

### Drift DB Schema (v4)

Tables: Products, Orders, OrderItems, Payments, Shifts, CashActivities, Ingredients, Recipes, RecipeIngredients, **OutletStocks**

Migration path: v1 → v2 (CRDT columns) → v3 (ingredient/recipe tables) → v4 (outlet_stock table)

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
| Storefront | ✅ | ✅ | ✅ |
| Reservations | ✅ | ✅ | ✅ |
| Recipe/Ingredient/HPP | ❌ | ✅ | ✅ |
| Tab/Split Bill | ❌ | ✅ | ✅ |
| AI Chat | ❌ | ✅ | ✅ |
| Recipe mode stock | ❌ | ✅ | ✅ |

Backend enforces via `deps.require_pro_tier` dependency on route.
Dashboard enforces via `useProGuard()` hook.
Flutter should check `stock_mode` from SecureStorage.

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
