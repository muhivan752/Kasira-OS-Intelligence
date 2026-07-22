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
→ Tab pay endpoints support **cash + QRIS** (B2 — Mei 2026). QRIS pakai async settle via webhook (`payments.py:_handle_tab_payment_webhook_paid` + `_handle_tab_payment_webhook_failed`). Card/transfer masih unsupported di tab path.

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
17. **Jangan trigger order_id branch di webhook untuk Payment yg punya `tab_id`** — tab payments selalu set `payment.order_id = first_order.id` sebagai anchor, tapi `payment.amount_due` itu sisa TAB (bukan first order's total). Webhook order branch akan salah-complete first order based on per-order total comparison. Pattern wajib: `if payment.tab_id: ... handle_tab(); elif payment.order_id: ... handle_order()`. Tab branch handles SEMUA orders, items, splits, tab close, table release, WA receipts. Reference: `payments.py:_handle_tab_payment_webhook_paid/_failed` (B2 ship Mei 2026).
18. **Jangan nanya jumlah tamu di flow baru — pakai `showGuestCountSheet()`** (`kasir_app/lib/features/tabs/presentation/widgets/guest_count_sheet.dart`). Ada DUA jalur buka meja: tab "Meja" (`table_grid_page.dart:_startDineInFromMeja`) dan POS dine-in (`pos_page.dart:_onPosTableSelected`), plus fallback orphan-occupied. Dulu cuma jalur POS yang nanya → tab dari tab Meja selalu `guest_count=1` → bagi rata mati. Kalau nambah entry point ketiga, WAJIB lewat helper yang sama.
19. **Jangan print autoprint tanpa atomic claim via `POST /payments/{id}/claim-print`** — webhook + Flutter poll bisa race ke autoprint, double-print struk. `receipt_printed_at` column (migration 087) jadi mutex. Endpoint `claim-print` returns `claimed=true` only if was NULL → set timestamp. Manual reprint button bypass (intentional cashier action).
20. **Jangan nulis `except Exception: pass` di jalur pembayaran** — dua alasan, dua-duanya kegigit di bug loyalty (fix 2026-07-21):
    - **Tanpa logger = bug abadi.** `_try_earn_loyalty_points` lama nelen `UndefinedColumnError` (kolom `point_transactions.row_version` ada di model tapi gak pernah dibikin migration 059) selama berbulan-bulan. Earn poin rusak 100% di SEMUA jalur, nol jejak di log. Wajib `logger.warning(..., exc_info=True)`.
    - **Nangkep exception TIDAK nyelametin transaksi.** Begitu satu statement ditolak Postgres, seluruh transaksi jadi aborted — commit pembayarannya ikut mati walau error-nya udah ditangkep. Kerjaan sampingan (loyalty, event log, dll) yang nulis ke DB WAJIB dibungkus `async with db.begin_nested()` (SAVEPOINT). Lihat `backend/services/loyalty_service.py`.
21. **Jangan nambah earn poin dari satu titik doang** — loyalty punya 5 call site dan semuanya lewat `backend/services/loyalty_service.py`: `create_payment` cash, webhook Xendit, `POST /payments/send-receipt`, tab close di `tabs.py` (3 tempat: pay-full/pay-split/pay-items) + `_handle_tab_payment_webhook_paid`, dan `POST /sync/` untuk order offline. Yang paling gampang kelewat: **send-receipt**. Kasir nangkep nomor pelanggan DI HALAMAN STRUK, sesudah bayar — jadi waktu `create_payment` jalan, `order.customer_id` masih NULL dan earn ke-skip. Order tab kelunasannya dibaca dari `tab.status == 'paid'`, BUKAN per-order (`require_fully_paid=False`), karena split/pay-items gak pernah bikin Payment per-order.
22. **Jangan pegang `ref` Riverpod lintas `await` kalau ada `Navigator.pop()` di antaranya** (Flutter — fix 2026-07-22). Begitu route-nya di-pop, `ConsumerState` di-dispose, dan `ref.read()` sesudah itu **throw** `StateError('Cannot use "ref" after the widget was disposed')` — lihat `flutter_riverpod-2.6.1/lib/src/consumer.dart:550`. Kalau throw-nya kena `catch (_) {}`, bug-nya jadi tak kelihatan selamanya.
    - **Yang kegigit**: `_autoPrintSplitReceipt` / `_autoPrintFullReceipt` / `_autoPrintItemsReceipt` di `pay_split_modal.dart` + `pay_items_modal.dart`. Pola-nya `unawaited(fn())` → `await dio.get(...)` → pop jalan duluan → resume → `ref.read(printerProvider.notifier)` → throw. **Struk tab/split gak pernah kecetak sekalipun**, printer nyala atau nggak. Jalur QRIS kena juga (callback claim-print jalan sesudah modal pop), plus `ref.read(tabProvider.notifier)` buat refresh tab pasca-QRIS.
    - **Pola wajib**: capture notifier-nya SEBELUM pop — `final printer = ref.read(printerProvider.notifier);`. Objek notifier milik provider container, hidup terus walau widget-nya mati. Sama juga buat `ScaffoldMessenger` + `Navigator` (yang ini emang udah dilakuin).
    - Berlaku buat `widget.xxx` juga: `State.widget` gak throw, tapi baca field-nya sesudah dispose = baca snapshot basi. Snapshot ke variabel lokal sebelum pop.
    - Logika struk tab sekarang ada di `core/services/tab_receipt_service.dart` (terima `PrinterNotifier`, bukan `WidgetRef`) + `core/widgets/tab_receipt_sheet.dart`. Kalau nambah jalur bayar tab baru, lewat situ.
23. **Jangan bikin jalur bayar tanpa pintu ke struk yang permanen** — auto-print itu SEKALI lewat; kalau printer mati atau customer minta struk 5 menit kemudian, harus tetap ada tombol. `tab_bottom_actions.dart` dulu render **kosong** begitu tab `paid` (cabang `isOpen` dan `isSplitting` dua-duanya gak match) → buntu total. Struk split PER-ORANG juga gak ada di Riwayat: `order_detail_modal` cuma punya `buildReprintReceipt()` = struk order penuh. Sekarang: tombol STRUK di snackbar sukses, di kartu split yang lunas, dan di bar bawah tab.
24. **Jangan nentuin "order ini lunas" cuma dari `Payment.order_id`** (fix 2026-07-22). Order yang nempel di tab **nggak punya Payment per-order**: split/pay-items nggak pernah bikin satu pun, dan pay-full cuma bikin SATU Payment dengan `order_id = order pertama` sebagai jangkar (gotcha #17). Predikat yang bener punya DUA cabang: `Payment.order_id` paid **OR** `Order.tab_id` nunjuk Tab berstatus `paid`. Yang kegigit: `customer_stats.compute_stats` — semua order ke-2 dst di satu meja dianggap belum lunas, jadi pelanggan dine-in kunjungannya ke-undercount, yang ordernya bukan yang pertama malah nol total. Helper-nya sekarang `customer_stats._is_paid_order()`. Cerminan `loyalty_service.earn_points_for_tab` yang juga baca kelunasan dari `tab.status`.
25. **Jangan bikin kolom agregat yang cuma keisi kalau ada yang buka halamannya** (fix 2026-07-22). `customers.total_visits` / `total_spent` / `last_visit_at` dibaca LANGSUNG sama `GET /customers/crm` (halaman Pelanggan di dashboard), tapi yang ngisinya cuma `GET /customers/{id}/detail` dan tombol `POST /customers/refresh-stats`. Nol jalur pembayaran yang manggil — jadi buat owner angkanya kelihatan **nggak pernah update**, semua pelanggan nol walau udah transaksi.
    - **Sekarang di-refresh dari 5 jalur yang sama persis dengan loyalty** (gotcha #21): `_try_earn_loyalty_points` (nutup cash + webhook Xendit), `_try_earn_loyalty_points_for_receipt` (send-receipt), `tabs.py` ×3 (pay-full/pay-split/pay-items), `_handle_tab_payment_webhook_paid`, dan `POST /sync/`. Kalau nambah jalur bayar baru, colok juga.
    - **JANGAN taruh di dalam `loyalty_service`.** Loyalty itu Pro+ dan `return 0` duluan buat tenant Starter — agregat CRM harus jalan di SEMUA tier. Makanya dipanggil terpisah, di luar cek tier.
    - Yang paling gampang kelewat sama kayak loyalty: **send-receipt**. Nomor pelanggan baru nempel ke order DI HALAMAN STRUK, sesudah bayar — pas `create_payment` jalan `order.customer_id` masih NULL.
    - Wajib lewat `refresh_customer_safe` / `refresh_for_order` / `refresh_for_tab` / `refresh_for_order_id`: dibungkus `begin_nested()` (SAVEPOINT) + logger, sesuai gotcha #20. Nggak pernah raise, nggak pernah commit.
26. **Varian produk (Hot/Ice, size, level gula) — SHIPPED 2026-07-22, dan aturannya ketat.** Tabel `product_variants` (mig `014`) dulu cuma rangka: nol route, nol UI, nol baris. Sekarang hidup penuh lewat mig `090` (+`is_active`, `sort_order`, index).
    - **`price_adjustment` itu SELISIH dari `product.base_price`, BUKAN harga akhir.** Ice +2000 ditulis `2000`, bukan `27000`. Boleh negatif (size kecil), makanya jangan dikasih `ge=0` / CHECK. Alasannya: harga pokok naik → pemilik ubah SATU angka, semua varian ikut.
    - **Harga final WAJIB lewat `variant_price()`** (`backend/services/variant_utils.py`) di backend dan **`ProductVariantModel.priceFor()`** di Flutter. Jangan tulis `base + adjustment` di tempat lain — ini persis pelajaran HPP unit mismatch (gotcha #11): rumus gampang yang disalin ke banyak tempat itu yang paling sering beda.
    - **`resolve_variant()` WAJIB dipanggil di SETIAP jalur bikin order** (`orders.py`, `connect.py`). Tanpa cek kepemilikan, klien bisa ngirim `product_id` produk murah + `product_variant_id` punya produk lain = celah manipulasi harga. Storefront-nya PUBLIK, ini bukan skenario teoretis.
    - **Identitas baris keranjang berubah**: dari `productId` jadi `lineKey` = `productId::variantId` (`CartItem.lineKey` di Flutter, `cartLineId()` di `app/[slug]/CartContext.tsx`). Kalau ada operasi keranjang baru (tambah/+/−/hapus), pakai lineKey. Pakai productId = tap Dingin nambah qty baris Panas, pelanggan bayar salah.
    - **Nama varian di-SNAPSHOT ke `order_items.modifiers['variant_name']`** pas order dibuat, dan `OrderItem.product_name` yang nyambungnya jadi `"Kopi Susu (Dingin)"`. Digabung di property model, BUKAN di tiap pemakai — yang baca: layar dapur, label split bill, struk WA, struk cetak-ulang, dashboard. Paling gawat kalau kelewat justru **dapur**: barista cuma lihat teks itu, tanpa varian dia bikin yang panas. Baca dari snapshot, bukan relasi, biar struk bulan lalu tetap benar walau variannya udah dihapus.
    - **Relasi `Product.variants` pakai `lazy="selectin"` + `primaryjoin` yang nyaring `deleted_at`.** Disengaja: `ProductResponse.variants` dibaca dari belasan endpoint, dan relasi lazy default bakal meledak `MissingGreenlet` begitu ada satu yang kelewat.
    - **Sync PULL-ONLY.** Varian dikelola dari dashboard; `sync.py` narik baris yang udah di-soft delete juga (`is_deleted: true`) supaya device tahu harus buang — kalau disaring di server, Drift lokal nyimpen varian hantu selamanya. Flutter nyaring `isDeleted` + `isActive` di `productVariantsProvider`.
    - **`PUT /products/{id}/variants` itu "kirim daftar final"**, bukan tambah/hapus per baris — form produk cuma punya satu tombol Simpan. Nyocokin baris lama-baru pakai **nama**: ganti harga = UPDATE (id tetap, order lama tetap nyambung), ganti nama = hapus+bikin baru. Yang hilang dari daftar di-soft delete (Rule #7).
    - **Endpoint ini WAJIB `db.expire(product)` sebelum re-fetch.** Session-nya `expire_on_commit=False` (`backend/core/database.py:27`), jadi `select()` ulang ngasih balik instance identity-map dengan koleksi `variants` versi LAMA — response balik kosong padahal data masuk. Kegigit pas tes pertama.
    - **Semua tier.** Varian itu kebutuhan dasar warung kopi, bukan fitur analitik. Gate ke Pro = merchant Starter balik bikin dua produk terpisah yang bikin resep & stok kembar.
    - **Belum nyambung ke resep/stok** (keputusan sadar, wave berikutnya): Ice butuh es batu, Large butuh susu lebih banyak. Sekarang varian cuma ngubah harga. Kalau nanti disambung, itu nyentuh 6+ stock code path — baca ARCHITECTURE.md dulu.

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
| `PATCH /tabs/{id}/guests` | Ubah jumlah tamu. **400 kalau split udah kebentuk** — batalin split dulu |
| `POST /shifts/open` | `outlet_id` as **query param** |
| `PUT /orders/{id}/status` | Bukan `PUT /orders/{id}/cancel` — kirim `{"status":"cancelled","row_version":N}` |
| `GET /ingredients/` | Pro-only (`require_pro_tier`), perlu brand_id + outlet_id |
| `GET /auth/me` | Returns `subscription_tier` + `stock_mode` |
| `POST /ingredients/{id}/restock` | Butuh `outlet_id` di body |
| `POST /shifts/{id}/close` | Body field `ending_cash` (BUKAN `closing_cash`) |
| `POST /payments/` | Body field `amount_due` + `amount_paid` (BUKAN single `amount`) |
| `POST /connect/{slug}/order` | WAJIB `order_type` di body (selain `qty` + `idempotency_key`) — kalau gak kirim, 422 |

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
