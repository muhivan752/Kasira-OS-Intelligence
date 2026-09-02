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
23. **Jangan bikin jalur bayar tanpa pintu ke struk yang permanen** — auto-print itu SEKALI lewat; kalau printer mati atau customer minta struk 5 menit kemudian, harus tetap ada tombol. `tab_bottom_actions.dart` dulu render **kosong** begitu tab `paid` (cabang `isOpen` dan `isSplitting` dua-duanya gak match) → buntu total. Struk split PER-ORANG juga gak ada di Riwayat: `order_detail_modal` cuma punya `buildReprintReceipt()` = struk order penuh. Sekarang: tombol STRUK di kartu split yang lunas dan di bar bawah tab, plus **sheet sukses bayar** (`core/widgets/tab_payment_success_sheet.dart`, 2026-09-02) yang muncul sesudah tiap bayar tab/split/sebagian — auto-print jalan DI DALAM sheet dengan status kelihatan, tombol Cetak / Kirim WA / Selesai. **Jangan balikin ke snackbar** — snackbar di halaman tab nimpa bar aksi bawah (kelihatan di device) dan tombol STRUK-nya hilang sendiri 4 detik. Struk split (`buildSplitReceipt`) WAJIB nyetak daftar pesanan meja: versi tanpa item bikin orang gak tau bayar buat apa.
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

27. **Jangan "benerin" app DAPUR jadi Aurora — dia sengaja dark.** Per 2026-09-01 app POS (`kasir_app`) 100% pakai `KasiraDS` (aurora light). `lib/features/dapur/**` (7 file) TETAP pakai `AppColors` dark emerald, dan `app_theme.dart` TETAP nyimpen `lightTheme`/`darkTheme` lama buat `main_dapur.dart`. Itu **keputusan Ivan**, bukan kerjaan yang kelupaan: layar dapur ngadep panas/silau, penggunanya barista yang lihat dari jarak jauh, dan binary-nya emang terpisah dari app kasir.
    - Konsekuensi yang harus diterima apa adanya: `flutter analyze` nyisain 1 warning `_now` unused di `dapur_dashboard_page.dart:21`. Jangan dikejar.
    - **Cara ngukur sisa kerjaan Aurora — pakai grep, JANGAN daftar screen.** Tracker per-screen di memory pernah basi parah: nulis "BELUM" buat 7 layar yang udah kelar berbulan-bulan, dan hampir bikin satu sesi ngerjain ulang semuanya.
      ```bash
      cd /var/www/kasira/kasir_app
      for f in $(find lib/features lib/core/widgets -name "*.dart" | grep -v /dapur/); do
        grep -q "Widget build" $f && ! grep -q KasiraDS $f && echo $f
      done   # kosong = app POS udah full Aurora
      ```
29. **Purchasing (nota belanja) — SHIPPED 2026-09-02, gelombang 1 "ERP yang ngisi sendiri".** Tabel `suppliers`/`ingredient_suppliers`/`purchase_orders`/`purchase_order_items`/`supplier_price_history` udah ada sejak mig 008–044 tapi nol model/route/baris sampai mig `091` (kasus persis `product_variants`). Kalau nemu tabel di DB yang gak ada modelnya, cek `\d` dulu sebelum bikin tabel baru.
    - **Nota = `PurchaseOrder` status `received` yang dibuat langsung.** `supplier_id` nullable (beli di pasar). Baris boleh `ingredient_id` ATAU `product_id` (CHECK). Starter non-F&B nyatet produk jadi; baris bahan ditolak 403 buat Starter.
    - **HPP = rata-rata bergerak** (`purchasing_service.moving_average`): stok lama × cost lama + qty baru × cost baru. Stok lama 0 / cost lama 0 → harga baru dipakai apa adanya. `ingredient.buy_price/buy_qty` = "terakhir beli". Konversi satuan nota → base_unit pakai `unit_utils.UNIT_ALIASES` yang sama dengan HPP compute (gotcha #11) — jangan bikin tabel konversi kedua.
    - **Restock bahan lewat `restock_ingredient_stock()`** (ditarik dari route `/ingredients/{id}/restock`, dua jalur satu kode). Restock produk lewat `stock_service.restock_product` (bug drift CRDT simple-mode di ARCHITECTURE.md tetap berlaku).
    - Event `purchase.received` / `purchase.paid` di stream `purchase:{id}` = bahan projector ledger gelombang 2. Utang = `total_amount − paid_amount`, `due_at` dari `supplier.payment_terms_days` (default 7).
    - **Baris nota punya 5 bentuk** (mig `092`): `ingredient_id` / `product_id` (udah ada), `new_ingredient{name,base_unit?}` / `new_product{name,sell_price}` (dibikin on-the-fly, dedup by nama), atau `name` doang = **"Lainnya"** (gas, plastik, tisu): `is_other`, nol efek stok, tetap masuk total + utang → bahan pengeluaran gelombang 2. CHECK: salah satu dari ingredient_id / product_id / name_snapshot.
    - Dashboard `/dashboard/pembelian`, actions di `app/actions/api.ts` (getPurchases/createPurchase/payPurchase/getSuppliers/scanInvoice). OCR pakai `/invoice-ocr/scan` yang lama — `apply` lama (update harga tanpa stok) sekarang jalur kedua, jangan dipakai dari UI baru.
30. **Rebrand Kasira → Selaris (2026-09-02) — domain lama JANGAN dimatiin.** Nama & URL kanonik cuma dari `lib/brand.ts` (web) dan `settings.BRAND_NAME`/`settings.SITE_URL` (backend, dari `.env`). Jangan hardcode "Kasira"/"Selaris"/domain di string user-facing baru. `kasira.online` WAJIB tetap ngelayanin `/api/*`, `/uploads/`, `/webhook*` selamanya: APK terpasang hardcode base URL lama, webhook Xendit tiap tenant (BYOK) didaftarin ke sana. Yang boleh di-redirect ke selaris.id cuma halaman web. Status + runbook go-live: memory `project_selaris_rebrand`. Yang sengaja gak diganti: `pulsa.kasira.online` (produk KasiraPay), nama repo/container/DB, slug demo `kasira-coffee`.
31. **Jangan taruh hook React sesudah `return` awal (loading / not found)** — storefront `/{slug}` crash "Terjadi Kesalahan" buat SEMUA pelanggan dari 22 Jul sampai 2 Sep karena `useState(variantProduct)` diselipin di bawah `if (loading) return`. React #310 cuma muncul di browser (bukan di log server, bukan di `tsc`), jadi nggak kelihatan dari curl. **Cara reproduksi error client-side**: Chromium headless Playwright ada di `/var/www/antidetect/node_modules` — `NODE_PATH=/var/www/antidetect/node_modules node repro.js` (tangkap `pageerror` + console error), contoh skrip di memory `project_session_20260902_tab_sukses_erp`.
32. **Keuangan (gelombang 2, SHIPPED 2026-09-02, semua tier) — laba rugi & arus kas DIHITUNG, bukan disimpan.** Nggak ada tabel ledger/journal; `finance_service.summary()` ngitung dari payments, payment_refunds, purchase_orders, expenses, cash_activities. Kalau nambah jalur uang baru (metode bayar baru, jenis pengeluaran baru, refund jalur lain), cek `_pnl_block` / `_cash_block` / `_expense_block` — bukan nambah tabel.
    - **Nota belanja ≠ beban.** Belanja stok masuk ARUS KAS (keluar) tapi masuk LABA RUGI baru waktu terjual (HPP). Cuma baris "Lainnya" di nota yang jadi `expenses` (dengan `purchase_id`) — dan di arus kas baris itu SENGAJA di-skip karena pembayaran notanya udah dihitung. Kalau lo lihat expense dengan purchase_id di arus kas = dobel.
    - HPP per produk: `_get_hpp_map` (resep) → fallback `product.buy_price` (Starter). `cogs_coverage` < 1 = ada item terjual tanpa HPP; UI ngasih peringatan di < 70%.
    - Akun kas auto-seed 3 akun per tenant di GET /finance/accounts (`ensure_accounts`). Pemetaan metode → akun lewat `default_for`.
    - `recurring='monthly'` cuma TEMPLATE; nggak ada cron. `copy-recurring` nyalin dari bulan lalu yang belum ada padanannya (cocok by kategori+catatan).
    - Semua bulan = WIB (`month_bounds`). Tren 6 bulan = 12 query tambahan per summary; kalau lambat, materialisasi per bulan — jangan bikin background projector tanpa baca gotcha #16.
33. **CRM & promo WA (gelombang 3, SHIPPED 2026-09-02).** Segmen pelanggan DIHITUNG (`crm_service.refresh_segments`, lazy 6 jam dari `GET /crm/segments/summary`) — jangan nulis `customers.segment` manual. Promo WA (`/campaigns`) HANYA ke `wa_marketing_consent=true`, dikirim dari `outlets.fonnte_token` (BYO per toko, mirror BYOK Xendit) lewat `send_whatsapp_with_token`; OTP + struk tetap `settings.FONNTE_TOKEN`. Pengirim jalan di BackgroundTasks dengan session sendiri + `SET LOCAL app.current_tenant_id` (gotcha #16) dan jeda 1,2 dtk antar pesan — jangan dipercepat, WhatsApp ngeblokir nomor yang nyembur. Template wajib berakhir "Balas STOP". Actions web CRM ada di `app/actions/crm.ts`, bukan `api.ts`.
34. **Shift itu PER OUTLET (laci bersama), bukan per kasir** (keputusan Ivan 2026-09-02: "di resto nyata modal jadi satu"). `POST /shifts/open`: ada shift open di outlet → kasir lain GABUNG (audit `JOIN_SHIFT`), akun sama → resume; shift ≥ 20 jam → ditutup otomatis + buka baru (dulu 400 "Shift sudah terbuka" = deadlock buat app yang baru di-install). `GET /shifts/current` per outlet, pakai `scalars().first()` — bisa ada >1 open dari data lama. Tutup shift boleh kasir mana pun di tenant. Siapa input apa = `orders.user_id`, bukan shift. Multi laci (shift per kasir) = setting outlet, belum ada.
37. **Angka `Decimal` dari backend datang sebagai STRING — jangan `as num`** (fix 2 Sep 2026, v1.6.10). Pydantic nyerialisasi `Decimal` jadi `"15000.00"`, bukan `15000.0`. Di `sync_service._applyServerChanges` ada `(p['base_price'] as num).toDouble()` → `TypeError` di baris PERTAMA yang di-apply.
    - **Sekali gagal = SEMUA gagal.** Apply jalan dalam satu `db.transaction`, jadi satu baris meledak bikin seluruh sync di-rollback. Gejalanya menyesatkan: server balas **200 OK** (kelihatan sehat di log nginx), tapi Drift tetap kosong. Kasir cuma lihat "Sinkronisasi gagal, coba lagi nanti", dan halaman Stok, bahan baku, sama **picker varian** kosong selamanya walau API-nya penuh.
    - Semua angka WAJIB lewat `_toDouble` / `_toDoubleOrNull` (string-safe). Yang aman dari awal: ingredients, recipes, product_variants, `tab_provider`. Yang kegigit: products, orders, order_items, payments, shifts, cash_activities.
    - Cara ngecek cepat: `curl` sync full pull, terus lihat tipe field — `python3 -c "print(type(row['base_price']))"`. `str` = harus `_toDouble`.
    - Jangan percaya "200 OK" di log sebagai bukti sync berhasil. Bukti yang bener: baris kebaca di Drift, atau layar Stok keisi.
36. **selaris.id di belakang Cloudflare (proxied) sejak 2 Sep 2026.** NS `nick`/`tricia.ns.cloudflare.com` (akun yang sama dengan kasira.online), A `@` + `www` → 139.180.188.88 Proxied, SSL **Full (strict)** (sertifikat certbot di origin tetap dipakai dan tetap auto-renew — `certbot renew --dry-run --cert-name selaris.id` lolos lewat proxy karena 301 ke HTTPS diikuti certbot).
    - **Jeda Universal SSL itu nyata**: begitu zona jadi Active, TLS ke edge sempat `handshake failure` ~10 menit sampai sertifikat edge terbit. HTTPS domain benar-benar mati selama itu. Kalau nggak boleh ada jeda, taruh record di **DNS only** dulu, tunggu Universal SSL terbit, baru nyalain oranye.
    - **`/etc/nginx/conf.d/cloudflare-realip.conf`** wajib ada, kalau nggak `$remote_addr` jadi IP edge → rate limit `limit_req zone=auth_limit` ngitung SEMUA pengunjung sebagai satu orang. Refresh range: `curl https://www.cloudflare.com/ips-v4`.
    - `/etc/hosts` masih nge-pin selaris.id → IP origin. **Sengaja**: curl dari VPS nggak muter lewat edge. Konsekuensinya buat verifikasi lewat edge harus `curl --resolve selaris.id:443:<IP CF>`.
    - Udah dites lewat edge dan lolos: API (gzip, `cf-cache-status: DYNAMIC`), sync 82 KB dengan User-Agent `Dart/3.13` (nggak kena bot protection), SSE `/ai/chat` ngalir per token (nggak di-buffer), storefront, unduh APK 70 MB, `/uploads/` ke-cache di edge. Kalau nanti Bot Fight Mode dinyalain, app Flutter yang pertama mati — jangan disentuh.
35. **Jalur bayar & bikin order WAJIB idempotent dari sisi HP** (fix 2 Sep 2026, v1.6.9). Kasus nyata: bayar 37.800 lunas di server dalam 3 dtk, respons hilang di data seluler, HP bilang "Gagal memproses", kasir tekan lagi → 400 "sudah dibayar" → mentok; retry order bikin `pending` yatim (ORD-5404/5406). Server-nya cepat (cek `rt=`/`urt=` di nginx access.log, format `timed`), yang rapuh itu jaringan HP.
    - `POST /orders/` terima `id` opsional (uuid v4 dari `CartNotifier._clientOrderId`, dipakai ulang sampai order kebentuk / keranjang dikosongin) → retry balikin order yang sama, stok nggak kepotong 2x.
    - `POST /payments/` udah lama support `idempotency_key` (Rule #5) tapi app **nggak pernah ngirim**. Sekarang `payment_modal` kirim satu key per modal per metode (`_cashIdemKey` / `_qrisIdemKey`).
    - Di modal bayar: 400 "sudah dibayar" = SUKSES (jangan ditampilin sebagai error); timeout tanpa respons → `GET /orders/{id}` dulu, kalau `completed` = sukses. Timeout terima 30 dtk. Kalau nambah jalur bayar baru (tab, riwayat), tiru pola ini.
    - **Sync jalan sekali tiap app dibuka** (`pos_page._syncedThisSession`). Dulu cuma waktu HP pindah offline→online → install baru / login ulang dengan sinyal stabil nggak pernah sync → Drift kosong → Stok, bahan baku, dan **picker varian** (baca dari Drift) semua "Belum ada" walau API penuh. Workaround lama: Pengaturan → Sinkronisasi.
    - nginx: gzip buat JSON proxied (`gzip_proxied any`) + `http2` aktif sejak 2 Sep — `/products/` 17 KB → 3,4 KB. Dart `HttpClient` kirim `Accept-Encoding: gzip` otomatis.
28. **`flutter analyze` di VPS SELALU keluar 9 error `productVariants` — itu BUKAN bug.** `lib/core/database/app_database.g.dart` (drift generated) belum di-regenerate lokal sejak kerjaan varian. CI jalanin `dart run build_runner build` di step 49 **sebelum** `flutter analyze` di step 122, jadi di CI bersih. Flutter ADA di VPS (`/opt/flutter/bin`) — analyze lokal dulu sebelum bakar CI run, tapi saring dulu:
    ```bash
    /opt/flutter/bin/flutter analyze 2>&1 | grep 'error •' \
      | grep -v 'productVariants\|ProductVariantLocal\|HasResultSet'
    ```
    Kosong = aman. Kalau lo panik lihat "9 errors" mentah, lo bakal ngejar hantu.

38. **Mode POS itu state TERPISAH dari isi keranjang — kalau salah satu dibuang, buang dua-duanya** (fix 2 Sep 2026, v1.6.12). `clearCart()` ngereset `CartState` (meja ikut hilang) tapi `posModeProvider` nggak ikut. Ikon tong sampah di keranjang cuma manggil `clearCart()`, jadi kasir mendarat di kondisi "dine-in tanpa meja": tombol **Simpan ke meja** tetap muncul tapi `submitDineInOrder()` selalu nolak `Pilih meja terlebih dahulu`, sementara tombol pilih mejanya (`Ganti`) cuma dirender kalau meja UDAH kepilih. Buntu total, dan dari layar itu nggak ada jalan balik.
    - Gejala yang dilaporin Ivan: "di tab meja gak bisa pesan". Ciri di layar: header Kasir ada panah balik (mode dine-in) tapi pill-nya nulis **Take away** (`cart.tableId == null`).
    - Tiap `clearCart()` di luar jalur bayar WAJIB dibarengin `posModeProvider = PosMode.selection`. Jalur bayar dan simpan-ke-meja udah bener dari dulu.
    - `Ganti`/`Pilih meja` WAJIB nutup bottom sheet keranjang dulu (`ModalRoute.of(context) is PopupRoute` → pop). Tanpa itu pemilih mejanya kebuka DI BAWAH sheet dan layar kelihatan beku. Di tablet keranjang nempel di halaman (bukan route), makanya cek PopupRoute-nya wajib.
    - Halaman yang duduk di IndexedStack dashboard **nggak punya AppBar**, jadi header-nya wajib `SafeArea(top: ...)` sendiri (tab Meja + tab Stok kegigit). Tapi `TableGridPage` juga dipakai EMBED di POS buat pilih meja — di situ `top` harus false, kalau nggak ada pita kosong di atas grid.
    - Padding "ruang buat bar keranjang" WAJIB di dalam `GridView.padding`, bukan `Padding` di luar. Di luar, dia motong tinggi viewport: pita kosong permanen dan baris terakhir nggak pernah kebuka.

40. **Offline-first itu belum selesai kalau cuma ordernya yang disimpan — pembayarannya juga harus** (fix 2 Sep 2026, v1.6.13). `cart_provider._submitOffline()` udah lama nyimpen order ke Drift, tapi `payment_modal` nggak punya jalur offline sama sekali: dia selalu `POST /payments/`, gagal, lalu nampilin "Koneksi lambat, pembayaran belum terkonfirmasi". Hasilnya transaksi TUNAI nggak bisa ditutup pas jaringan mati, padahal itu justru alasan fitur offline ada.
    - Sisi server udah siap dari dulu: `sync.py` nerima `changes.payments` dan punya cabang khusus buat order offline (poin loyalti + agregat CRM). Yang hilang cuma penulisan lokalnya.
    - Sekarang lewat `CartNotifier.savePaymentOffline()`: insert `PaymentLocal` (`status: 'paid'`, `isSynced: false`) + update order lokal jadi `completed`. Modal manggilnya lewat callback `onOfflineCash` dari `cart_panel`, karena `PaymentModal` itu StatefulWidget biasa tanpa `ref`.
    - **Cek online DULUAN, jangan sesudah request gagal.** Kalau requestnya sempat berangkat, server bisa aja udah nerima; nyimpen salinan lokal sesudah itu = pembayaran dobel waktu sync. Cabang timeout yang lama (tanya `GET /orders/{id}` dulu) tetap dipertahankan apa adanya.
    - QRIS SENGAJA nggak punya jalur offline: QR-nya diterbitkan server.
    - Struk aman offline: `payment_success_page` ngebangun `ReceiptData` dari data di memori + SharedPreferences, nggak nembak server (Rule #53).
    - `Connectivity().checkConnectivity()` cuma baca status antarmuka, bukan jangkauan internet beneran. WiFi nyambung ke router tanpa internet tetap kebaca "online" dan bakal jatuh ke cabang timeout. Itu diterima apa adanya, jangan diganti ping ke server (nambah latensi di tiap transaksi).

41. **Shift/sesi kas itu OTOMATIS sejak 3 Sep 2026 (mig 097–098). Jangan pernah lagi nulis kode yang nolak transaksi dengan "buka shift dulu".** Latar: 25 dari 27 shift produksi terbuka >1 hari, satu di antaranya 4 bulan; tiga jalur transaksi nyari shift dengan caranya sendiri sampai Beranda nulis "Shift aktif" tapi simpan ke meja ditolak. Rujukan desain: cash drawer Toast (business-day cutoff 04.00, paused drawer, blind close, lockdown opsional).
    - **Satu pintu**: `shift_service.ensure_open_shift(db, outlet_id, user_id, tenant_id, source=...)`. Nggak ada yang terbuka → dibuka sendiri (`opened_by='auto'`, modal awal = sisa penutupan terakhir). Dipakai `orders.py`, `payments.py`, `tab_service.find_active_shift`, dan `sync.py` (order/payment offline yang `shift_session_id` NULL ditempelin di sini). Id basi dari cache HP = diperlakukan seperti nggak ngirim, BUKAN 400.
    - **Janitor `backend/tasks/shift_cutoff.py`** tiap 10 menit nutup sesi `open`/`paused` yang mulai sebelum 04.00 waktu outlet (`outlets.timezone`). `closed_reason='auto_cutoff'`, `end_time` = 04.00-nya, `ending_cash`/`counted_at` NULL. **Sistem nggak boleh mengaku kas cocok** — `counted_at IS NULL` = belum dihitung, jangan pernah isi `ending_cash = 0` biar rapi. Gotcha #16 (RLS bypass) berlaku.
    - Status `paused` = "hitung nanti" (`POST /shifts/{id}/pause`): laci lama dijeda, laci baru langsung jalan dengan modal = perkiraan sisa yang dijeda. Yang dijeda dihitung lewat `/close` biasa. `GET /shifts/uncounted` = bahan pengingat Beranda (`reports/daily` → `uncounted_shifts`, `uncounted_since`).
    - `POST /shifts/open` di atas sesi `auto` = **KLAIM** (isi modal awal ke sesi yang sama), bukan bikin sesi baru.
    - **Profil per OUTLET, bukan tier**: `outlets.shift_mode` ringan/standar/ketat, default ikut tier saat mig 098 (Starter→ringan, Pro+→standar), pemilik ganti dari Pengaturan web. Mesinnya satu; yang beda cuma ketatnya hitungan.
    - **Blind close** (standar/ketat, bukan pemilik): `shift_service.blind_view()` ngosongin expected/total/starting di `/current`, `/close`, `/uncounted`; app nggak render baris sistem; pesan tutup jadi "Hitungan kas tercatat" tanpa selisih. Selisih cuma buat pemilik (dashboard web Kelola Kasir). Pemilik = `is_superuser` ATAU role bernama Owner (`shift_service.is_owner`). Data loadtest semua user-nya role Owner — bukan bug, seed-nya begitu.
    - **Daftar hadir DIHITUNG**, bukan disimpan: `shift_participants()` dari `orders.user_id` + pembuka + penutup. Sama prinsipnya dengan laba rugi & segmen: nggak ada tabel yang bisa basi.
    - App: login tanpa sesi → tetap ke Beranda; kartu Beranda "Kasir siap / Sesi terbuka otomatis"; `setShiftSessionId(null)` sekarang HAPUS dari secure storage (dulu id lama bangkit lagi tiap app start). Id shift diambil dari respons `POST /orders/` (`_rememberShiftFrom`).
    - **Profil `ketat` (gelombang 3, mig 099)**: satu-satunya profil di mana `ensure_open_shift` BOLEH nolak (400 `SHIFT_REQUIRED`) — serah terima modal awal itu intinya. `POST /shifts/open` di Ketat ngunci laci ke pembuka (`locked_user_id`); kasir lain kena 403 `SHIFT_LOCKED` (nama pemegang di pesan), pemilik menerobos. Jeda di Ketat TIDAK bikin sesi lanjutan. Sync offline pakai `strict=False` (penjualannya udah kejadian). `GET /shifts/{id}/review` = rekap per kasir (pesanan, tunai, QRIS) dari orders+payments, dikosongkan saat blind. `/current` tanpa sesi balik `{status: null, shift_mode}` — app Ketat ngarahin ke `/shift/open`, web ngecek `cur.id`.

39. **Teks yang kelihatan user: JANGAN pakai em dash (—) dan JANGAN pakai garis miring sebagai pemisah kata** (keputusan Ivan 2 Sep 2026: "itu terlalu AI slop"). Berlaku di web (`app/**`, `components/**`) dan Flutter (string di `lib/**`), bukan di komentar kode.
    - Ganti em dash dengan kalimat yang bener: titik, koma, titik dua, atau kurung. "Catat nota belanja — stok naik, ..." jadi "Catat nota belanja. Stok naik, ...".
    - Garis miring jadi kata: "Pilih bahan / produk" jadi "Pilih bahan atau produk"; "Diskon / promo" jadi "Diskon atau promo".
    - Placeholder sel tabel kosong pakai `-` biasa, bukan `—`.
    - `·` boleh buat metadata pendek (`Rab, 2 Sep · 21:18`) dan judul halaman (`Selaris · POS Digital`). `&` juga boleh (`Listrik & air`).
    - Cek cepat sebelum bilang selesai: `grep -rn "—" app components --include=*.tsx | grep -vE ":[0-9]+:\s*(//|\*|\{/\*)"` harus kosong.

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
- [ ] `backend/services/purchasing_service.py` — nota belanja: restock bahan (via `restock_ingredient_stock`) + produk (via `restock_product`) + HPP rata-rata bergerak
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
