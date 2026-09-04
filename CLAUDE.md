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
43. **Pesanan online (storefront) — alur konfirmasi toko, SHIPPED 3 Sep 2026 (mig 101).** Dulu order storefront cuma kirim WA ke pelanggan, langsung `preparing` tanpa ada yang tahu, nol tanda di app kasir. Sekarang:
    - **`orders.source`** `'pos' | 'storefront'`. Storefront SELALU lahir `pending` = "Menunggu konfirmasi toko", apa pun metode bayarnya (tunai pun). QRIS lunas lewat webhook TIDAK mengubah status (`payments.py` cek `order.source`), cuma bikin pesanan muncul ke kasir. Jangan balikin ke "cash langsung preparing".
    - **Satu pintu efek samping: `backend/services/order_lifecycle.py`** (`accept_order`, `mark_ready`, `cancel_order`, plus `restore_stock_for_order`/`recalc_tab_after_cancel`/`release_table_if_idle` yang sekarang juga dipakai `PUT /orders/{id}/status`). Jangan tulis ulang balikin-stok inline lagi; `cancel_order` idempoten (status sudah cancelled = no-op) karena pernah dobel.
    - Endpoint: `POST /orders/{id}/accept {eta_minutes}`, `POST /orders/{id}/reject {reason}`, `GET /orders/online?outlet_id` (QRIS belum lunas DISARING), `GET /orders/stream?outlet_id` (SSE dari Redis pub/sub `orders:{outlet_id}`, heartbeat 15 dtk). Tombol lama app ("Terima & Proses" = PUT preparing, "Tolak" = PUT cancelled) dialihkan ke jalur yang sama di dalam `update_order_status`. **Path literal `/online` dan `/stream` WAJIB dideklarasikan SEBELUM `/{order_id}`**: UUID gagal parse = 422, bukan fallthrough.
    - **Janitor `backend/tasks/online_order_timeout.py`** tiap 60 dtk: QRIS belum dibayar > 16 mnt → batal senyap ("Pembayaran tidak diselesaikan", stok balik, dulu nyangkut selamanya); sudah lunas/tunai tapi toko diam > `outlets.online_auto_cancel_minutes` (default 10, jam dari `paid_at` untuk QRIS) → batal + refund + WA pelanggan. **uvicorn jalan 2 worker → tiap worker punya supervisor → pass jalan dobel.** Kunci Redis `online_order_timeout:lock` (NX EX 50) + `FOR UPDATE SKIP LOCKED`. Kegigit di deploy pertama: 3 order dibatalkan 2x, stok balik 2x. Janitor lain (shift_cutoff, stale_order) punya risiko yang sama, baru aman karena intervalnya jam-jaman.
    - **Refund QRIS otomatis** `backend/services/refund_service.py` → `xendit_service.create_qr_refund` (`POST /qr_codes/payments/{qrpy_id}/refunds`, header `api-version: 2022-07-31`, id dari `xendit_raw.data.id`). Gagal (kunci nggak ada, channel nggak dukung) = baris `payment_refunds` tetap dibuat status `pending` + WA pemilik "refund manual". Belum pernah kena Xendit sungguhan (nol BYOK aktif), anggap belum terverifikasi end-to-end.
    - **Teks WA & label status satu bahasa** di `services/online_orders.py` (pelanggan + pemilik) dan `app/[slug]/_ui.tsx` (halaman lacak). Kirim ke pelanggan dari `outlet.fonnte_token` kalau ada, fallback token platform. WA pemilik ke `whatsapp_number`, fallback `phone`, toggle `online_notify_owner_wa`.
    - Toggle per outlet di Pengaturan web: `online_orders_enabled` (storefront `accepting_orders=false`, POST order 400), `online_notify_owner_wa`, `online_auto_cancel_minutes` (3–60). `kitchen_mode` (ada di DB sejak mig 003) baru dipetakan ke model, belum ada UI: gelombang dapur berikutnya.
    - **Storefront `app/[slug]/**` didesain ulang total 3 Sep**: satu layout semua tier (pelanggan nggak peduli tier), bahan bersama di `_ui.tsx`, catatan pelanggan sekarang beneran tersimpan (`ConnectOrderInput.notes`, dulu dibuang Pydantic), alamat antar di `orders.delivery_address` (bukan diselipkan ke `notes`). Halaman lacak: fase dihitung dari status order + status bayar (`pending` punya dua arti). Dua bug lama ikut mati: tombol WA pakai nomor tersamar, timeline nyari status `processing`.
    - **App kasir (v1.6.18)**: `lib/features/online_orders/` = provider (SSE lewat `package:http` + line buffering `\n\n`, polling 30 dtk sebagai jaring, bel `assets/sounds/order_bell.wav` via `audioplayers` 3x saat masuk + pengingat 45 dtk selama ada yang menunggu, preferensi `online_orders_sound`) + halaman `/online-orders` (segmen Menunggu/Diproses/Selesai, Terima dengan pilihan menit, Tolak dengan alasan, Chat WA ke pelanggan). Dihidupkan dari `_DashboardPageState.initState`, yang sekarang `WidgetsBindingObserver` PERTAMA di app: stream diputus saat app ke belakang, disambung + ditarik ulang saat kembali. Beranda: tombol bel berbadge + banner gradien di luar `statsAsync`. Riwayat: awalan "Online" di baris pesanan storefront.
    - **Dapur (mig 102)**: `orders.kitchen_status` (NULL | preparing | ready | done) TERPISAH dari `orders.status`, karena pesanan kasir yang dibayar langsung `completed` dan dapur nggak pernah melihatnya kalau papan dibaca dari status order. `GET /orders/kitchen` = {active, done}: status preparing/ready/served ATAU completed ≤ 3 jam, belum `done` di dapur; online `pending` SENGAJA nggak masuk (kasir yang memutuskan). `POST /orders/{id}/kitchen-status`; `ready` pada order `preparing` ikut menaikkan status order + WA "siap" ke pelanggan online. Toggle `outlets.kitchen_mode` di Pengaturan web (Pro): `off` = login PIN dapur ditolak 403 dengan pesan arah ke Pengaturan; `display` = app Dapur jalan; `print` masih "Segera". App Dapur diperbaiki: endpoint baru, `display_number` toString, item `quantity`, bel + interval poll tersimpan di SharedPreferences (`dapur_sound`, `dapur_poll_interval`), pesan 403 ditampilkan apa adanya.
    - **Pesanan meja dari storefront WAJIB punya tab.** Dulu kalau meja belum punya tab terbuka, order mendarat tanpa tab dan tanpa Payment: nggak ada yang nagih, dan laporan (yang cuma menghitung order lunas lewat `_paid_order_filter`) nggak pernah melihat uangnya. Kegigit tes Ivan 3 Sep (#5439, #5441: "duitnya gak masuk Beranda"). Sekarang `order_lifecycle.open_tab_for_storefront_order` membuka tab otomatis (`opened_by` NULL, meja jadi occupied); di app kasir pesanan meja berakhir di "Diantar ke meja", pembayarannya lewat tab Meja. Tab otomatis yang jadi kosong karena ditolak ikut `cancelled` dan mejanya dilepas. **`recalc_tab_after_cancel` dan `release_table_if_idle` WAJIB `await db.flush()` dulu**: status order yang baru diubah di memori belum kelihatan oleh query (gotcha #2), tab sempat tetap 63.000 dan meja tetap terisi sesudah reject.
    - **BELUM**: FCM (app tertutup = cuma WA pemilik), cetak tiket dapur, kitchen_mode dari app kasir, tunai storefront ditandai lunas saat dibuat (bukan saat serah terima).

44. **Metode bayar itu PILIHAN TOKO, satu pola di `backend/services/payment_methods.py` (mig 103, 4 Sep 2026).** Latar: 4415 pembayaran lunas di prod, SEMUANYA tunai. QRIS di app cuma jalan lewat Xendit BYOK dan nol toko punya kuncinya, jadi QRIS statis bank/GoPay/DANA (mayoritas UMKM) nggak ada tempat dicatat: dicatat tunai atau nggak dicatat, laci selisih tiap tutup shift.
    - **`outlets.payment_methods`** (JSONB, default `["cash","qris"]`) = yang toko nyalakan. Tunai dipaksa selalu ada (`normalize_methods`). App kasir (modal bayar + 3 modal tab), storefront, dan endpoint bayar cuma pakai `enabled_methods(outlet)`; metode nonaktif ditolak 400 `PAYMENT_METHOD_DISABLED`. Diatur dari Pengaturan web DAN dari app (`payment_methods_settings_page.dart`), dua-duanya `PUT /outlets/{id}`.
    - **`payments.channel`**: `'xendit'` (QR dinamis, `pending` sampai webhook) atau `'manual'` (kasir konfirmasi sendiri, `paid` langsung seperti tunai). `resolve_channel(outlet, method, requested)`: QRIS jatuh ke xendit HANYA kalau toko punya kunci/sub-account; tanpa itu QRIS = manual. **Nggak ada lagi "QRIS tidak tersedia".** Jangan tulis `payment_method == 'cash'` buat nentuin settle-inline, pakai `settles_inline(method, channel)`. NULL di baris lama = manual, KECUALI QRIS lama yang di-backfill `xendit`.
    - **QRIS statis toko** = `outlets.qris_static_image_url` (unggah lewat `/media/upload`, disimpan URL absolut). Kasir nampilin gambar itu (`core/widgets/manual_payment_info.dart`, dipakai 4 modal), tekan Konfirmasi sesudah lihat notifikasi bank. Transfer nampilin `bank_name/bank_account_number/bank_account_name`. App baca semuanya dari `SessionCache` (`paymentMethods`, `qrisChannel`, `qrisStaticImageUrl`, `bank*`), diisi `GET /outlets/{id}` dan di-cache SharedPreferences supaya offline tetap tahu.
    - **Storefront QRIS manual**: Payment `pending` channel manual, order `pending`; halaman lacak nampilin QR toko + tombol "Kirim bukti bayar" ke WA toko; **kasir menerima pesanan = memastikan uang masuk** (`order_lifecycle.accept_order` set paid). Janitor 16 menit "QRIS belum dibayar" HANYA buat channel xendit; manual ikut batas konfirmasi toko seperti tunai. `GET /orders/online` juga nggak menyaring QRIS manual. Refund otomatis Xendit di-skip buat manual (`refund_service`), langsung baris refund manual + WA pemilik.
    - **Offline**: `PaymentLocal` nggak nyimpen channel; `sync.py:_normalize_push` ngisi `channel='manual'` buat QRIS offline (QR dinamis butuh server).
    - Tab: `_enforce_tab_supported_method` (cash+QRIS saja) DIHAPUS, diganti `_tab_payment_channel(outlet, body)`; ketiga endpoint pay pakai variabel `inline`. Tab sekarang terima transfer dan kartu juga.

45. **DP reservasi, bukti bayar, dan peta Google (mig 104, 4 Sep 2026). Tiga hal, satu pola dengan metode bayar (#44).**
    - **DP itu PILIHAN merchant** (`reservation_settings.require_deposit` + `deposit_amount`, kolom ada sejak awal tapi mati). Logika di `backend/services/deposit_service.py`. Storefront: kalau DP wajib DAN toko punya metode non-tunai aktif, reservasi lahir `pending` + satu `Payment` (order_id NULL, `reference_id = reservation:{id}`, channel dari `payment_methods.resolve_channel`). Tanpa metode non-tunai, DP dilewati (jangan blokir pelanggan). Auto-confirm nggak berlaku kalau DP wajib.
    - **Konfirmasi kasir = DP manual dianggap masuk** (`mark_paid_if_manual`), QRIS Xendit nunggu webhook (`payments.py:_handle_deposit_webhook_paid`, cabang baru SEBELUM `elif payment.order_id`). **Seat = DP nempel ke tab meja**: `apply_deposit_to_tab` buka tab lewat `order_lifecycle.open_tab_for_table` (helper yang sama dengan pesanan meja online), set `payment.tab_id` + `tab.paid_amount += DP`, jadi pay-full/split menghitung sisa dengan benar. No-show: DP lunas SENGAJA dibiarkan (hangus). Janitor `expire_unpaid_deposits` (60 menit, di loop `online_order_timeout`) cuma membatalkan yang BELUM kirim bukti.
    - **Bukti bayar** = `payments.proof_image_url` lewat `POST /connect/payments/{payment_id}/proof` (publik, dikunci UUID, hanya channel manual + status pending). Dipakai DP reservasi DAN QRIS statis pesanan online (halaman lacak `app/[slug]/order/[id]`, `app/[slug]/reservation/[id]`). Proxy Next `app/api/proof/[paymentId]/route.ts` tanpa token. Sistem TIDAK menandai lunas dari bukti: kasir lihat thumbnail di kartu Pesanan Online / detail reservasi (dashboard + app) lalu Terima/Konfirmasi. Halaman lacak menampilkan bukti yang terkirim + tombol kirim ulang.
    - **Peta = kunci SERVER, bukan browser.** `GOOGLE_MAPS_SERVER_KEY` di `.env` (kunci yang sama dengan Sefrekuensi `GOOGLE_STATIC_KEY`; env baru = `compose build backend && up -d --no-deps backend`, `docker restart` nggak reload env). `backend/services/geo_service.py`: Places Autocomplete (bias lokasi outlet, `sessiontoken` dari klien supaya ditagih per sesi), Place Details, reverse geocode, Static Maps (proxy `/connect/geo/static`, cache Redis 24 jam). Storefront memanggil `/connect/{slug}/geo/*`; kalau kunci kosong `maps_enabled=false` dan alamat antar jatuh ke textarea biasa. `orders.delivery_lat/lng/distance_km` diisi dari pilihan pelanggan; **radius antar ditegakkan server** (400 kalau `> delivery_radius_km + 0.3`), app kasir dapat tombol Peta. Outlet perlu `latitude/longitude` (Pengaturan web) supaya jarak dihitung.
    - **Notifikasi merchant SATU pintu: `online_orders.wa_owner`** (pesanan online, reservasi baru, bukti masuk, DP lunas). Di dalamnya `push_sefrekuensi` POST ke `SEFREKUENSI_NOTIFY_URL` (Bearer `SEFREKUENSI_NOTIFY_TOKEN`) kalau diisi: `{phone, outlet_id, outlet_name, message, source}`. Strategi Ivan: reservasi online = pintu akuisisi user Sefrekuensi. Kanal baru ditambah di situ, bukan di pemanggil.
    - Bug lama yang ikut mati: `PUT /reservations/settings` 500 karena `audit_log.after_state` dapat `Decimal` (`_jsonable`), dan form Tambah Reservasi web 422 karena `source: walk_in`.

46. **OTP lewat Sefrekuensi: USER YANG MILIH kanalnya, kode nggak loncat kanal (4 Sep 2026, direvisi sore harinya).** `backend/services/sefrekuensi.py` + `auth.py:/otp/send` + `OTPSendRequest.channel` (`whatsapp` default | `sefrekuensi`). Kode tetap dibikin & diverifikasi Selaris; Sefrekuensi cuma KURIR (DM Yasmin + push FCM). Respons `/otp/send` bawa `channel`.
    - **Versi pagi (server nyoba Sefrekuensi diam diam, jatuh ke WA) DIBUANG.** Dua cacatnya: merek Sefrekuensi nggak pernah kelihatan, dan layar app bohong ("Periksa WhatsApp" padahal kodenya di Sefrekuensi). Keputusan Ivan: "WhatsApp ya WhatsApp, Sefrekuensi ya Sefrekuensi."
    - **Layar masuk & daftar = iklan halus Sefrekuensi.** Kartu bersama: web `components/auth/sefrekuensi-otp-card.tsx` (dipakai `app/login`, `app/register`), Flutter `core/widgets/sefrekuensi_otp_card.dart` (dipakai `login_page.dart`, `register_page.dart`). WhatsApp TETAP tombol utama supaya orang baru nggak kepaksa pasang app kedua di tengah daftar. Kalau nambah layar OTP baru (mis. lupa PIN), pakai kartu yang sama.
    - **Minta Sefrekuensi tapi nomornya nggak ada di sana = 404 `{"code":"SEFREKUENSI_NOT_FOUND","message":...}`**, BUKAN diam diam lewat WA. Klien nyalain wujud kedua kartu: Pasang (Play Store) atau "Kirim lewat WhatsApp saja". Jatah 3/30 menit TIDAK kepotong buat percobaan yang gagal ini (`_simpan_dan_hitung` cuma jalan kalau kurir beneran jalan), supaya user bisa langsung ulang lewat WA tanpa kena 429. Sefrekuensi mati/gangguan = 503 `SEFREKUENSI_UNAVAILABLE`.
    - `detail` di sini berbentuk **map**, bukan string. Klien lama yang `detail.toString()` bakal nampilin `{code: ..., message: ...}`; makanya Flutter pakai `otpErrorCode()`/`otpErrorMessage()` dan web `sendOtp()` ngembaliin `{code, message}`. APK lama yang nggak kirim `channel` tetap jalan: default `whatsapp`, perilaku persis seperti sebelumnya.
    - **Kirim ulang pakai kanal yang sama** (`state.channel` / `_channel`), dan layar OTP nulis "Periksa Sefrekuensi Anda, pesan dari Yasmin" atau "Periksa WhatsApp Anda" sesuai `channel` dari respons. Jangan hardcode WhatsApp lagi di teks OTP.
    - **Ekspektasi yang bener**: layar OTP cuma dilihat SEKALI per HP (sesudahnya PIN). Ini pintu branding, bukan mesin akuisisi. Titik akuisisi yang kuat = **langkah 2, notifikasi merchant (LIVE 4 Sep sore)**: `online_orders.wa_owner` → `push_sefrekuensi` → `sefrekuensi.send_notify` → `POST /partner/notify` di Sefrekuensi (`handlers/partner_notify.go`, kunci partner yang sama, DM Yasmin + push walau app kasir ditutup). Nggak butuh env baru: `SEFREKUENSI_NOTIFY_URL/TOKEN` di config sekarang NGANGGUR, kurirnya pakai `SEFREKUENSI_API_URL/PARTNER_KEY`. WA ke pemilik TETAP dikirim juga (jaring); kalau mau hemat Fonnte, keputusan "kalau Sefrekuensi sampai, WA di-skip" belum diambil. Nomor yang dipakai = `whatsapp_number` fallback `phone` outlet.
    - **Jangan panggil `/cek` sebelum kirim.** `/kirim` udah balik 404 sendiri. `check()` cuma buat MEMUTUSKAN TAMPILAN.
    - **Langkah 3, ajakan pasang di titik sakit (LIVE 4 Sep sore), tiga tempat satu status**: `GET /outlets/{id}/sefrekuensi-status` (`sefrekuensi.status_for_phone`, cache Redis `sefre:status:{phone}` 1 jam, dihapus `forget_status` begitu kirim beneran sampai) → kartu Beranda web (`components/dashboard/sefrekuensi-card.tsx`: belum punya = ajakan, sudah = badge terhubung + catatan kalau push mati), banner halaman Pesanan Online app (`core/widgets/sefrekuensi_nudge_banner.dart`, cache prefs 1 jam, tutup = diam 7 hari), dan kaki pesan WA pemilik (`online_orders.wa_owner` + `nudge_line()`, HANYA kalau nomornya belum ada di Sefrekuensi, maks 1x/hari/toko lewat `sefre:nudge:{outlet_id}` NX). Link Play Store satu sumber: `settings.SEFREKUENSI_PLAY_URL`. Jangan nambah ajakan di layar acak: titik sakitnya "pesanan masuk pas app ditutup", ajakan ditaruh di situ.
    - `SEFREKUENSI_API_URL` + `SEFREKUENSI_PARTNER_KEY` di `.env` (env baru = `compose build backend && up -d --no-deps backend`). **Recreate container = berkas `docker cp` hilang**, `version.json` wajib dipasang ulang (gotcha #9).
    - **Kode OTP jangan pernah masuk log**, di sini maupun di Sefrekuensi.
    - **Pelajaran lintas repo (gofiber):** gerbang auth di Sefrekuensi sempat `return c.Status(401).JSON(...)`. Di gofiber `c.JSON()` balik **nil**, jadi `if err := gate(c); err != nil` nggak pernah kepicu dan handler jalan terus: status 401 nempel tapi body ketimpa data asli. Efeknya `/partner/otp/cek` bocorin "nomor ini kedaftar" ke siapa pun dan `/kirim` beneran nganter DM+push tanpa kunci sah. Gerbang WAJIB `return fiber.NewError(...)`. Tes yang cuma ngecek URUTAN teks di source lolos mulus; yang nangkep cuma tes PERILAKU (handler di balik gerbang nggak boleh kesentuh).

47. **Toko bisa ditemukan (4 Sep 2026, mig 105).** Latar: storefront cuma bisa ditemukan kalau pemilik nyebar link-nya sendiri. `app/sitemap.ts` nembak `/outlets/public/list` yang **404 sejak lahir**, jadi nol toko yang pernah dikasih tahu ke Google; nol JSON-LD; nol generator QR.
    - **`GET /outlets/public/list`** (`outlets.py:public_outlet_list`, tanpa auth, cache Redis `outlets:public:list` 5 menit) = satu sumber buat sitemap DAN halaman `/jelajah`. Saring: outlet aktif, `outlets.directory_listed` (mig 105, default true, keputusan pemilik), tenant nggak dihapus & status `active|trial`, punya ≥1 produk aktif. Akun `loadtest-%`/`smoke-%` dimatikan di migrasi. **Path literal `/public/list` WAJIB di atas `/{outlet_id}`** (gotcha #43). Redis helper-nya `backend.services.redis`, BUKAN `backend.core.redis` (kegigit).
    - **JSON-LD LocalBusiness** di `app/[slug]/layout.tsx` (`businessJsonLd`): jenis dari `brands.type` (cafe→CafeOrCoffeeShop, resto/warung→Restaurant, other→Store), alamat, geo, telepon dari `whatsapp_number`, `OrderAction`. Storefront payload sekarang bawa `business_type`, `city`, `province` (clear `connect:storefront:*` sesudah ubah payload). Escape `<` jadi `\u003c` di `dangerouslySetInnerHTML` supaya nama toko nggak bisa nutup tag script.
    - **`/dashboard/toko`** ("Toko Online", nav di bawah Menu): link + QR (`qrcode` npm, client-side), unduh PNG, cetak stiker A5 (window.open + print), bagikan WA, saklar `directory_listed`, daftar periksa kelengkapan profil (cover, alamat, WA, titik lokasi, jam buka, menu), panduan Google Business Profile / Instagram / WA Business. **Nggak ada QR di sisi server**: nol lib Python (`qrcode`/`segno` nggak terpasang).
    - **Link toko di struk**: WA (`payments.py:_build_receipt_text`) udah lama; struk KERTAS lewat `storefront_url` di `GET /orders/{id}/receipt` + `SessionCache.outletSlug` (prefs `c_outlet_slug`) buat jalur offline. 4 pembangun struk di `printer_service.dart` nyetak teks URL LALU **QR** (`EscPos.qr`, perintah bawaan printer GS ( k model 2, modul 5, koreksi M). Teks dulu sengaja: printer tanpa perintah QR ngelewatin perintahnya, URL-nya tetap kebaca. **Belum device test** (nebeng APK berikutnya).
    - `opening_hours` masih TEKS BEBAS (dipajang apa adanya di JSON-LD `openingHours`). Jadwal beneran = delivery gelombang 1.
    - **Halaman Next yang fetch backend saat render WAJIB `force-dynamic` + `cache: 'no-store'`** kalau datanya harus ada dari request pertama. Waktu `next build`, backend nggak kejangkau dari tahap build; dengan ISR (`revalidate`) hasil KOSONG itu ke-cache sampai jendelanya habis. Kegigit `/jelajah` + `sitemap.xml` (kosong sesudah deploy, padahal API-nya 7 toko). Cache taruh di Redis sisi backend. Fallback host dari dalam container = `http://backend:8000`, bukan `127.0.0.1`.

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

42. **Sync order offline nggak pernah jalan sebelum 3 Sep 2026 — lima lapis, semuanya ketutup "200 OK sync biasa".** Ketahuan pas Ivan tes offline sungguhan: 12 order tersimpan rapi di HP, dashboard nol. Urutan gagalnya (tiap lapis baru kelihatan sesudah lapis sebelumnya dibenerin):
    1. `SessionCache.setUserId` nggak pernah dipanggil → `_submitOffline` nulis `user_id: ''` → asyncpg nolak `invalid UUID ''` → **seluruh batch 500**. Fix: `ensureUserId()` di login + server ngisi dari akun yang nge-sync.
    2. id/FK dikirim str → SQLAlchemy 2 insertmanyvalues nyocokin PK RETURNING (objek UUID) dengan parameter → `Can't match sentinel values` → 500. Fix: `_normalize_push` di `routes/sync.py` konversi semua id ke `uuid.UUID`.
    3. Guard "order final nggak boleh diubah" nolak item dari order offline yang datang SUDAH `completed` di batch yang sama → order mendarat tanpa item. Fix: parent yang lahir di push ini (`batch_order_ids`) dikecualikan.
    4. `PaymentLocal` nggak nyimpen kembalian → bayar 50.000 buat tagihan 5.400 kebaca kas masuk 50.000 di laporan shift. Fix: HP kirim `change_amount`, server ngisi kalau kosong.
    5. `DateTime` lokal Dart tanpa zona → server nyimpan 23.30 WIB sebagai 23.30 UTC. Fix: `toUtc()` di `_orderToJson` dkk; server anggap waktu tanpa zona = zona outlet.
    - **Cara verifikasi yang bener** (jangan cuma lihat 200): `orders` dengan `OFFLINE-%` punya item, punya `payments`, nempel ke `shift_session_id`, dan jumlah `events.stock.sale` per order == jumlah item (marker idempotensi `_is_sale_already_recorded`; `stock_events` BUKAN tempatnya, online pun nol di situ).
    - Satu baris rusak = seluruh sync 500, jadi pembersihan paket ada di server (`_normalize_push`), bukan dipercayakan ke versi APK yang terpasang.
    - **Terjual melebihi stok tercatat (dua HP offline) TIDAK boleh diam** (mig 100): `deduct_stock(allow_partial=True)` di jalur sync motong sisa sampai 0, kekurangannya jadi event `stock.oversell` + cache `products.oversell_qty`. Hilang lewat stok opname `POST /products/{id}/stock-count` (event `stock.count`, angka fisik jadi kebenaran). Fisik < tercatat → `expenses` kategori `selisih_stok`, `payment_method='none'` = masuk LABA RUGI, dikecualikan dari ARUS KAS (`_cash_block`). Jangan pernah nulis stok minus: `CHECK (stock_qty >= 0)` tetap berlaku (Rule #47).
    - HP sync berkala tiap 5 menit selama online (`pos_page._periodicSync`) supaya dua kasir cepat lihat penjualan satu sama lain.
    - **Sisi BACA offline-first ada di `core/offline/local_reads.dart`** (3 Sep 2026): Beranda, Riwayat, detail order, stok kritis dihitung dari Drift; laporan margin & daftar meja di-cache SharedPreferences. Aturan gabungnya: online = angka server + transaksi lokal yang `isSynced=false` (nggak dobel, begitu tersinkron pindah ke server). Kalau nambah halaman baca baru, tiru pola `DioException.response == null → lokal`. Tab/buka meja tetap butuh server by design (dua HP nggak boleh bentrok bagi tagihan satu meja).

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
