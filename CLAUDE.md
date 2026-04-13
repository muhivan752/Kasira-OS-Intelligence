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
→ Filter recipe ingredients WAJIB cek `ri.ingredient.deleted_at is None`
→ `compute_recipe_stock` ada di 2 tempat — edit dua-duanya

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
9. **Jangan `docker compose up -d`** tanpa re-copy semua docker cp files — container recreate = files hilang
10. **Jangan edit `compute_recipe_stock` di products.py tanpa edit yang di connect.py** — logic harus identik

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
- [ ] `backend/api/routes/products.py` — `compute_recipe_stock()` display
- [ ] `backend/api/routes/connect.py` — storefront inline recipe calc
- [ ] `kasir_app/lib/features/pos/providers/cart_provider.dart` — offline deduction
- [ ] `kasir_app/lib/features/products/providers/products_provider.dart` — offline display

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
- [ ] Flutter: check `stock_mode` / tier dari SecureStorage
- [ ] ARCHITECTURE.md: update tier gating table

### Deploy backend change:
```bash
sudo docker cp <file> kasira-backend-1:/app/<path>
sudo docker restart kasira-backend-1
# Verify: sudo docker logs kasira-backend-1 --tail 10
```

### Deploy Flutter change:
```bash
git add <files> && git commit && git push origin main
# Trigger GitHub Actions: Build & Release Kasira Flutter APK
curl -X POST -H "Authorization: token <PAT>" \
  "https://api.github.com/repos/muhivan752/Kasira-OS-Intelligence/actions/workflows/build-apk.yml/dispatches" \
  -d '{"ref":"main","inputs":{"version":"X.Y.Z"}}'
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
| 25 | Claude API model dipilih via `get_model_for_tier(tier, task)` |
| 26 | Starter = Haiku, Pro+ = Sonnet untuk task kompleks |
| 55 | System prompt max 800 token, di-cache Redis 5 menit |

### 📱 MOBILE (Flutter)
| # | Rule |
|---|------|
| 14 | APK hosted di GitHub Releases, cek versi setiap app dibuka |
| 15 | `is_mandatory=true` → force update, block app sampai update |
| 49 | Printer disconnect TIDAK BOLEH block transaksi |

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
