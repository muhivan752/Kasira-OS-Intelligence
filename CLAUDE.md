# KASIRA — Claude Entry Point
# BACA SELURUH FILE INI SEBELUM NGODING APAPUN. JANGAN SKIP.

## Project
Kasira = POS + Pilot Otomatis + AI untuk cafe Indonesia
Stack: FastAPI + PostgreSQL + Flutter + Next.js 14 + Redis + Claude API
Owner: Ivan — solo dev, bahasa casual Indonesian, langsung fix+deploy tanpa basa-basi.

## Wajib Baca
- **ARCHITECTURE.md → WAJIB BACA FULL kalau menyentuh stock, recipe, tab, storefront, sync, atau CRDT**
- ROADMAP.md → Master Plan & Build Order

---

## ⛔ STOP — Sebelum Lo Mulai Coding

### Cek dulu: apakah perubahan lo menyentuh salah satu dari ini?

**Stock / Stok:**
→ BACA section "Stock System" + "CRDT Sync Engine" di ARCHITECTURE.md
→ Ada 2 mode (simple & recipe) dan **6+ code path** yang harus konsisten
→ Kalau edit 1 tempat, cek SEMUA tempat (lihat tabel di ARCHITECTURE.md)

**Sync / Offline:**
→ BACA section "CRDT Sync Engine" di ARCHITECTURE.md
→ Pahami: HLC, PNCounter, conflict strategy, idempotency
→ Jangan assume "server always right" — ada LWW dan financial_strict

**Tab / Split Bill:**
→ BACA section "Tab/Split Bill" di ARCHITECTURE.md
→ `row_version` di pay_split itu milik **split**, bukan tab
→ Setelah set `order.tab_id`, HARUS `await db.flush()` sebelum recalculate

**Recipe / Ingredient:**
→ Ingredient yang sudah `deleted_at IS NOT NULL` TETAP bisa di-reference oleh recipe lama
→ Filter recipe ingredients WAJIB 5 kondisi: `ri.deleted_at is None AND not ri.is_optional AND ri.quantity > 0 AND ri.ingredient is not None AND ri.ingredient.deleted_at is None`
→ `compute_recipe_stock` ada di 2 tempat — edit dua-duanya
→ **Unit mismatch gotcha**: `ri.quantity_unit` (misal 'kg') bisa beda dari `ri.ingredient.base_unit` (misal 'gram'). Untuk HPP compute WAJIB pake helper di `backend/services/unit_utils.py` (`normalize_recipe_qty`, `ingredient_cost_contribution`, `cost_from_qty_unit`). Untuk stock deduct/display: pake raw qty (internally consistent antara deduct + compute_recipe_stock, jangan diubah).

**Storefront:**
→ Redis cache `connect:storefront:{slug}` expire 60 detik
→ Semua produk active harus muncul, yang stock=0 pakai `is_available: false`
→ Storefront order pakai field `qty` (bukan `quantity`) + wajib `idempotency_key`

---

## 🔴 JANGAN LAKUIN INI (Pernah Bikin Bug)

1. **Jangan pakai `&` operator di Drift query** — pakai chained `.where()` calls
2. **Jangan skip `await db.flush()` sebelum query yang depend pada perubahan sebelumnya** — SQLAlchemy gak auto-flush
3. **Jangan edit stock logic di 1 tempat tanpa cek tempat lain** — lihat tabel "SEMUA Code Path" di ARCHITECTURE.md
4. **Jangan filter recipe ingredients tanpa cek ingredient.deleted_at** — ghost stock
5. **Jangan hide produk stock=0 di storefront** — show semua, tandai `is_available: false`
6. **Jangan kirim `quantity` ke storefront order** — field-nya `qty`
7. **Jangan assume `row_version` selalu milik parent** — di split bill, row_version milik TabSplit bukan Tab
8. **Jangan lupa clear Redis cache setelah edit storefront data** — `DEL connect:storefront:{slug}`
9. **Jangan `docker compose up -d`** tanpa re-copy semua docker cp files — container recreate = files hilang. Pakai `docker compose up -d --no-deps frontend` kalau cuma mau recreate frontend.
10. **Jangan edit `compute_recipe_stock` di products.py tanpa edit yang di connect.py** — logic harus identik
11. **Jangan compute HPP pake `ri.quantity * cost_per_base_unit` langsung** — unit mismatch bikin salah 1000x. Pake helper `backend/services/unit_utils.py`. 3 tempat kena bug ini historically: pricing coach, menu_engineering, knowledge_graph.
12. **Jangan query drift di Flutter tanpa scope `SessionCache.instance.outletId`** — multi-outlet switch bisa bikin data leak cross-outlet. Verify `OrderLocal.outletId == SessionCache.outletId` sebelum proceed.
13. **Jangan trigger APK build GitHub Actions sebelum push commit terakhir** — `workflow_dispatch` fire on main HEAD di dispatch time. Kalau ada commit lokal belum push → build jalan di commit lama. Fix: push dulu, verify `git log origin/main` match lokal, baru dispatch. Kalau terlanjur: cancel run + redispatch.
14. **Jangan rebuild frontend tanpa cek image Created time vs commit time** — `docker inspect kasira-frontend-1 --format '{{.Created}}'` harus LEBIH BARU dari commit terakhir yg mau di-deploy. Gap → fitur belum aktif di prod.
15. **Jangan release table di order completion path tanpa cek tab.status** — kalau `order.tab_id IS NOT NULL` AND `tab.status NOT IN ('paid', 'cancelled')`, JANGAN release table. Tab era: order completed = kitchen done, BUKAN "all paid". 2 code path yang HARUS pakai guard ini: `orders.py:519-533` (PUT /orders/status) + `stale_order_cleanup.py:185-220` (janitor orphan heal). Bug ke-discover 2026-04-25 saat split-bill testing — kitchen mark order ready/completed → table di-release prematurely → janitor heal back kalau di-recover manual. Fix: query `Tab.status` + skip release kalau active. Reference: commit `9762674`.
16. **Jangan write background task yang query RLS table tanpa `SET LOCAL app.current_tenant_id = ''`** — RLS policy `tenants` cek `current_setting(..., true) = ''`, dan `current_setting(unset)` return NULL ≠ ''. Background tasks gak ada middleware set context, jadi default unset → query return 0 rows silently. Pattern wajib di awal session: `await db.execute(text("SET LOCAL app.current_tenant_id = ''"))`. Reference: `stale_order_cleanup.py:57`, `payment_reconciliation.py` (fixed 2026-04-25 commit `01910f5` — sebelumnya silent broken). Untuk RLS policy `sync_idempotency_keys` yang hard-cast UUID tanpa bypass clause, pakai per-tenant iteration pattern di `sync_idempotency_cleanup.py`.

---

## ✅ CHECKLIST — Kalau Lo Edit...

### Tambah table baru ke database:
- [ ] Backend: model di `backend/models/`
- [ ] Backend: migration di `backend/migrations/versions/`
- [ ] Backend: schema di `backend/schemas/`
- [ ] Flutter: table di `kasir_app/lib/core/database/tables.dart`
- [ ] Flutter: register di `app_database.dart` (`@DriftDatabase(tables: [...])`)
- [ ] Flutter: bump `schemaVersion` + migration di `app_database.dart`
- [ ] Flutter: apply server data di `sync_service.dart:_applyServerChanges()`
- [ ] Backend: pull di `sync.py` (add to SyncPayload + query)
- [ ] Run `dart run build_runner build` (atau trigger GitHub Actions)

### Edit stock deduction logic:
- [ ] `backend/api/routes/orders.py` — online order create (line ~182)
- [ ] `backend/api/routes/orders.py` — cancel restore (line ~432)
- [ ] `backend/services/stock_service.py` — simple mode deduct + restore
- [ ] `backend/services/ingredient_stock_service.py` — recipe mode deduct + restore
- [ ] `backend/api/routes/sync.py` — offline order sync stock deduction (line ~76)
- [ ] `backend/api/routes/products.py` — `compute_recipe_stock()` display (shared, juga dipakai connect.py storefront)
- [ ] `kasir_app/lib/features/pos/providers/cart_provider.dart` — offline deduction
- [ ] `kasir_app/lib/features/products/providers/products_provider.dart` — offline display

### Edit HPP compute logic:
Tiga tempat pake helper dari `backend/services/unit_utils.py` — kalau edit salah satu, verify konsisten:
- [ ] `backend/services/ai_service.py` — `build_pricing_context()` untuk Pricing Coach
- [ ] `backend/services/menu_engineering_service.py` — `_get_hpp_map()` untuk BCG Matrix
- [ ] `backend/services/knowledge_graph_service.py` — `compute_hpp_for_products()` untuk KG queries
- [ ] Helper API: `normalize_recipe_qty(ri)` → qty in base_unit, `ingredient_cost_contribution(ri)` → cost Rp, `cost_from_qty_unit(qty, unit, ing)` → variant untuk non-RI callers (KG metadata)
- [ ] Semua helper return `None` kalau unresolvable mismatch → caller flag `⚠` / exclude dari sum

### Edit product/recipe data:
- [ ] Backend API returns correct data
- [ ] Dashboard fetches + displays correctly
- [ ] Sync endpoint includes data in pull
- [ ] Flutter sync_service applies data locally
- [ ] Flutter provider reads from local DB correctly
- [ ] Storefront reflects changes (clear Redis cache)

### Tambah Pro feature baru:
- [ ] Backend: `dependencies=[Depends(deps.require_pro_tier)]` di router
- [ ] Dashboard: `useProGuard()` hook di page
- [ ] Flutter: check `subscription_tier` dari SecureStorage (bukan cuma `stock_mode`)
- [ ] ARCHITECTURE.md: update tier gating table
- [ ] ROADMAP.md FASE 6 table: update status

### Deploy backend change:
```bash
sudo docker cp <file> kasira-backend-1:/app/<path>
sudo docker restart kasira-backend-1
# Verify: sudo docker logs kasira-backend-1 --tail 10
```

### Deploy frontend (Next.js dashboard) change:
```bash
# File source di /var/www/kasira/app/dashboard/... udah ke-edit.
# Next.js pakai .next/standalone/server.js — WAJIB rebuild image.
sudo docker compose build frontend
sudo docker compose up -d --no-deps frontend  # --no-deps biar backend gak recreate (gotcha #9)
# Verify: image Created time > commit time
sudo docker inspect kasira-frontend-1 --format '{{.Created}}'
# Verify feature text embedded di .next bundle
sudo docker exec kasira-frontend-1 grep -c "NEW_FEATURE_STRING" /app/.next/server/app/<route>/page.js
```

### Deploy Flutter change:
```bash
# 1. Commit + push dulu — pastikan origin/main match HEAD
git add <files> && git commit && git push origin main
git log origin/main --oneline | head -1  # verify latest commit

# 2. Trigger GitHub Actions workflow_dispatch
curl -X POST -H "Authorization: token <PAT>" \
  "https://api.github.com/repos/muhivan752/Kasira-OS-Intelligence/actions/workflows/build-apk.yml/dispatches" \
  -d '{"ref":"main","inputs":{"version":"X.Y.Z"}}'

# 3. Verify build jalan di commit yang bener
curl -H "Authorization: token <PAT>" \
  "https://api.github.com/repos/muhivan752/Kasira-OS-Intelligence/actions/workflows/build-apk.yml/runs?per_page=1" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['status'], r['head_sha'][:7])"
# Kalau head_sha != latest push → cancel + redispatch (gotcha #13)
```

**Auto-bump by CI**: Setelah APK build sukses, GitHub Actions auto-commit `chore: update version.json → vX.Y.Z`. Sebelum push lokal berikutnya, ALWAYS `git pull --rebase origin main` dulu.

### Run standalone Python script (non-HTTP, e.g., unit test atau debug query):
RLS (Row Level Security) aktif di 40+ table. Query tanpa `app.current_tenant_id` → `NoResultFound`. Middleware set context saat HTTP request masuk, tapi standalone script harus manual:
```python
async with AsyncSessionLocal() as db:
    await db.execute(text(
        "SELECT set_config('app.current_tenant_id', '<tenant_uuid>', true)"
    ))
    # Now query works — RLS sees correct tenant
    result = await db.execute(select(Product).where(...))
```

---

## 🧪 TEST — Sebelum Bilang "Done"

### Minimal test setelah edit stock/recipe:
```bash
# 1. Create order → cek ingredient stock berkurang
# 2. Cancel order → cek ingredient stock kembali
# 3. Order melebihi stock → harus error 400
# 4. Storefront → semua produk muncul, stock=0 = is_available:false
# 5. /products/ → recipe mode stock computed correctly
```

### Minimal test setelah edit sync:
```bash
# POST /sync/ dengan node_id dan last_sync_hlc=null → harus return semua data
# Cek: stock_mode ada di response
# Cek: ingredients, recipes, recipe_ingredients, outlet_stock ada di changes
```

### Minimal test setelah edit tab/split:
```bash
# 1. Open tab → add order → verify total > 0
# 2. Split equal → verify amounts sum = total
# 3. Pay each split → verify tab auto-close ke "paid"
# 4. Cancel tab → verify status "cancelled"
```

---

## API Quirks — Endpoint-Specific Gotchas

| Endpoint | Gotcha |
|----------|--------|
| `POST /reservations/` | `outlet_id` as **query param**, bukan body |
| `POST /connect/{slug}/order` | Items pakai `qty` bukan `quantity`, wajib `idempotency_key` |
| `GET /connect/{slug}/reservation/slots` | Param: `reservation_date` bukan `date` |
| `POST /tabs/{id}/splits/{split_id}/pay` | `row_version` milik **split**, bukan tab |
| `POST /shifts/open` | `outlet_id` as **query param** |
| `PUT /orders/{id}/status` | Bukan `PUT /orders/{id}/cancel` — kirim `{"status":"cancelled","row_version":N}` |
| `GET /ingredients/` | Pro-only (`require_pro_tier`), perlu brand_id + outlet_id |
| `GET /auth/me` | Returns `subscription_tier` + `stock_mode` |
| `POST /ingredients/{id}/restock` | Butuh `outlet_id` di body |

---

## Tier Gating — Endpoint Spec

### 🆓 ALL TIERS (Starter, Pro, Business, Enterprise)
| Endpoint | Catatan |
|----------|---------|
| `/auth/*`, `/health`, `/webhooks/*` | Public / infrastructure |
| `/products/*`, `/categories/*`, `/orders/*`, `/payments/*` (non-refund/partial) | Basic POS |
| `/refunds/*` | Semua tier (customer batal beli = reality semua cafe) |
| `/shifts/*` | Basic shift management |
| `/customers/*`, `/connect/{slug}/*` | Storefront + customer CRUD |
| `/reports/summary`, `/reports/daily` | Basic reports (revenue, payment breakdown, top products) |
| `/embeddings/status` | Read-only info |
| `/ai/context/{outlet_id}` (DELETE) | Cache clear — safe for all |

### 🔒 PRO+ ONLY (`require_pro_tier` dep)
| Endpoint | Gating Mechanism |
|----------|-----------------|
| `/ingredients/*`, `/recipes/*`, `/recipe-ingredients/*` | Router-level |
| `/tables/*`, `/tabs/*`, `/reservations/*` | Router-level |
| `/loyalty/*` | Router-level |
| `/knowledge-graph/*` | Router-level |
| `/analytics/*` (menu-engineering, combos, hourly) | Router-level |
| `/embeddings/generate` | Endpoint-level |
| `/ai/chat` | Endpoint-level (via `tenant: Tenant = Depends(require_pro_tier)`) |
| `/payments` partial_payment fields | Inline check (Rule #43) |

### ⚠️ Gotcha untuk tier gating
1. Jangan pakai **manual tier check inline** — pakai `Depends(deps.require_pro_tier)` dep untuk consistency.
2. `require_pro_tier` butuh header `X-Tenant-ID` (via `get_current_tenant`). Pastiin Flutter/dashboard kirim header ini di semua request auth.
3. Kalau endpoint butuh **tier VALUE** (bukan cuma check), inject `tenant: Tenant = Depends(require_pro_tier)` lalu extract: `tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)`.
4. Router-level gate lebih aman daripada per-endpoint — 1 miss endpoint = bug silent.

---

## GOLDEN RULES — Dikelompokkan per Domain

### 🗄️ DATA LAYER
| # | Rule |
|---|------|
| 1 | UUID untuk semua PK — TIDAK BOLEH integer auto-increment |
| 7 | Soft delete via `deleted_at`, TIDAK BOLEH hard delete |
| 8 | Event store append-only — TIDAK BOLEH update/delete event yang sudah ada |
| 29 | SEMUA tabel kritikal WAJIB `row_version` |
| 30 | Optimistic lock: `UPDATE ... WHERE row_version = :expected` → retry max 3x |
| 47 | `CHECK (stock_qty >= 0)` dan `CHECK (computed_stock >= 0)` — wajib di DB level |

### 🌐 API LAYER
| # | Rule |
|---|------|
| 2 | Setiap WRITE endpoint WAJIB tulis audit log |
| 3 | Response format: `{success, data, meta, request_id}` |
| 5 | Idempotency key wajib untuk semua payment endpoint |
| 6 | Timezone: simpan UTC di DB, tampilkan Asia/Jakarta ke user |
| 9 | FastAPI async ONLY — tidak boleh ada sync blocking call |

### 🔐 AUTH
| # | Rule |
|---|------|
| 11 | Auth WAJIB via OTP WA — tidak ada email+password |
| 12 | JWT: httpOnly cookie (web), Flutter SecureStorage (mobile) |
| 13 | OTP expire 5 menit, max 3x resend per 15 menit |

### 📦 STOCK
| # | Rule |
|---|------|
| 19 | Stok deduct otomatis dari transaksi. Restock manual HANYA saat terima barang |
| 20 | Stok = 0 → produk `is_available: false`, tapi TETAP MUNCUL (jangan hide) |
| 28 | `order_display_number` WAJIB dari PostgreSQL SEQUENCE |

### 💳 PAYMENT
| # | Rule |
|---|------|
| 31 | Payment endpoint WAJIB `SELECT FOR UPDATE` |
| 34 | `connect_orders` WAJIB `idempotency_key` |
| 35 | `point_transactions` WAJIB `UNIQUE(order_id, type)` |
| 40 | `payments.status` ENUM: `pending/paid/partial/expired/cancelled/refunded/failed` |
| 43 | `partial_payments` = Pro+ only — linked ke tab/bon feature |
| 44 | `xendit_raw` (JSONB) WAJIB disimpan |

### 🤖 AI
| # | Rule |
|---|------|
| 25 | AI chat (`/ai/chat`) = **Pro+ only**. Starter TIDAK punya akses AI chatbot (gated via `require_pro_tier`). |
| 26 | Model routing via `get_model_for_tier(tier, task, tenant_id, intent)` di `ai_service.py`. **Intent-aware**: PRICING_COACH → Sonnet 4.5 (`claude-sonnet-4-5-20250929`), lainnya → Haiku 4.5 (`claude-haiku-4-5-20251001`). Model ID constants: `SONNET_MODEL_ID`, `HAIKU_MODEL_ID`. |
| 26a | Sonnet quota: **5x/hari/tenant** via redis key `ai_sonnet:{tenant_id}:{date}`. Exceeded = return chunk "Analisa pricing udah dipakai 5x hari ini" + done event. Increment `ai_spend` +1 (total 2 cent per Sonnet call). |
| 26b | Intent classifier di `classify_intent()` urutan: MENU_BULK > SETUP_RECIPE > RESTOCK > **PRICING_COACH** > CHAT. PRICING_COACH keyword fokus DIFFERENTIATING: "hpp", "margin", "wajar harga", "rekomendasi harga", bukan ambigu kayak "untung" sendiri. |
| 27 | Domain detection via `detect_domain(outlet_id, db)` — 10 bucket UMKM (kopi_cafe, resto_makanan, warteg, bakery, vape_liquid, laundry, salon_barber, minimarket, pet_shop, apotik_herbal). Signal priority: product names ×3 > category names ×2 > outlet name ×1. Fallback ke Brand.type → "generic". Result inject ke MENU_BULK + SETUP_RECIPE prompts. |
| 55 | System prompt max 800 token, di-cache Redis 5 menit |

### 📱 MOBILE (Flutter)
| # | Rule |
|---|------|
| 14 | APK hosted di GitHub Releases, cek versi setiap app dibuka |
| 15 | `is_mandatory=true` → force update, block app sampai update |
| 49 | Printer disconnect TIDAK BOLEH block transaksi |
| 50 | Query drift WAJIB scope ke `SessionCache.instance.outletId` — multi-outlet switch bisa leak data. Pattern: load `OrderLocal` dulu, verify `outletId == SessionCache.outletId`, baru proceed. |
| 53 | Receipt bytes ESC/POS di-build DI FLUTTER, bukan backend. Backend `GET /orders/{id}/receipt` return **structured JSON** (outlet, items, totals, NPWP, footer). Flutter parse + `buildReceipt(ReceiptData)` → ESC/POS bytes. Ini bikin offline reprint bisa rebuild dari drift DB pake data yang sama. |
| 54 | Auto-print sampingan (refund receipt setelah POST success) WAJIB `unawaited()` — jangan block snackbar success user. Print gagal = silent, bukan block flow. |

### 🛒 CONNECT / STOREFRONT
| # | Rule |
|---|------|
| 16 | Kasira Connect: zero komisi selamanya |
| 21 | Storefront otomatis aktif saat outlet register |
| 22 | `connect_orders` WAJIB link ke `orders` table |
| 33 | `reservations` WAJIB `row_version` |

### 🏢 BISNIS
| # | Rule |
|---|------|
| 45 | pg_dump ke R2 cron tiap 6 jam |
| 51 | Upgrade tier = efektif hari itu setelah Ivan konfirmasi manual |
| 52 | Suspend flow: H-7 WA → H-3 WA → H+7 suspend → H+60 deletion |
