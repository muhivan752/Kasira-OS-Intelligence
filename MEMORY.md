# KASIRA — Long-Term Memory
# Update ini setiap selesai satu task!

## 🗺️ ROADMAP PROGRESS (Menuju Tier Starter)
- ✅ **FASE 0: Fondasi** (Semua Migration, Docker, VPS, Backend Core)
- ✅ **FASE 1: Auth** (OTP WA, JWT, Device Binding, Role Check)
- ✅ **FASE 2: Core POS Starter** (Products, Orders, Payment QRIS **Xendit xenPlatform**, Stock Deduct)
- ✅ **FASE 3: Flutter Kasir App** (15 layar + Inventory Powerhouse, GoRouter, Sync Engine, Offline Mode)
- ✅ **FASE 4: Owner Dashboard Next.js** (Owner Login, Laporan, Menu, Margin Tracking)
- 🟡 **FASE 5: Pilot** (Pre-launch hardening DONE 2026-04-25, monitoring DONE, Xendit live pending)
- 🟡 **FASE 6: Pro Features** (AI Chatbot multi-turn, Tab/Bon split bill, Warkop ad-hoc, Reservasi, Loyalty, Recipe/HPP, Knowledge Graph DONE; Multi-outlet pending)

## ✅ SELESAI
- [x] Migration Batch 1–8 (semua tabel, row_version, Golden Rules compliant)
- [x] CRDT Bug Fixes (HLC.receive & PNCounter.get_value)
- [x] Flutter Login OTP Flow (4 states with Riverpod)
- [x] Flutter QRIS Screen (Payment Modal, QrImageView, Timer, Polling)
- [x] Flutter Offline Mode (Connectivity monitoring, UI banner, CachedNetworkImage)
- [x] Backend Reporting Endpoint (`GET /reports/daily`)
- [x] Setup Alembic (alembic.ini, env.py) - CRITICAL FIX
- [x] Create Customer model and update models/__init__.py - CRITICAL FIX
- [x] Fix auth router prefix in api.py
- [x] Fix order items cascade to delete-orphan
- [x] Verify missing row versions in migrations
- [x] Update config.py (remove Midtrans keys, make ENCRYPTION_KEY required)
- [x] Create Storefront Connect API (GET /connect/{slug}, POST /connect/{slug}/order, GET /connect/order/{order_id})
- [x] Create Next.js Owner Dashboard (login, dashboard, menu, kasir, laporan, settings, payment, onboarding)
- [x] Create Next.js Storefront Public (menu, cart, order status)
- [x] Docker + VPS Ready (Dockerfile, docker-compose.yml, .env.example)
- [x] Create backend/scripts/seed_demo.py (idempotent, timezone, sequence)
- [x] Fix Connect API bugs (product fields, order sequence, error messages)
- [x] Fix Dockerfile.next for Next.js frontend
- [x] Fix Next.js auth (save tenant_id & outlet_id to cookies, X-Tenant-ID header)
- [x] Fix backend auth response to include tenant_id & outlet_id
- [x] Fix Flutter app entry point (DashboardPage -> LoginPage)
- [x] Audit Alembic migrations – 100% Golden Rules compliance
- [x] Fix Midtrans webhook multi-tenant (custom_field2, dynamic search_path)
- [x] Pre-deployment checks (CORS, Dockerfile, env vars, docker-compose)
- [x] Flutter Sync Engine (Drift Database, HLC, Dio API Client, Riverpod Integration)
- [x] Fix Storefront Payment Edge Cases (CRDT stock, outlet validation, online order status)
- [x] **FASE 3: Flutter Kasir App — 15 Layar Lengkap**
  - SplashPage + version checker | LoginPage | TableGridPage | PosPage | PaymentModal
  - PaymentSuccessPage | ReceiptPreviewPage | OrderListPage + OrderDetailModal
  - ShiftOpenPage | ShiftPage | LowStockAlertPage | SettingsPage + PrinterSettings
  - GoRouter setup | package_info_plus | build-apk.yml → GitHub Releases
- [x] **Migrasi Payment Gateway: Midtrans → Xendit xenPlatform**
  - Migration 057–058 (drop midtrans_*, add xendit_business_id, rename xendit_raw)
  - backend/services/xendit.py (create_sub_account, create_qris_transaction, verify_webhook)
  - Update payments + outlets route: QRIS via Xendit, platform fee 0.2%
- [x] **AppConfig + Real API Integration**
  - `AppConfig` singleton (SharedPreferences, first-launch flow)
  - `ServerSetupPage` (input URL VPS + ping test)
  - `CartProvider` + `ProductsProvider` dengan real API call
  - Save `tenant_id`, `outlet_id`, `phone` ke FlutterSecureStorage saat login
- [x] **VPS Deployment**
  - `kasira-setup.sh` (one-command: Docker, UFW, clone repo, .env, pg_dump cron, systemd service)
  - `backend/scripts/seed_admin.py` (idempotent: Tenant + Brand + Outlet + User admin)
- [x] **Offline-First Pure CRDT Stock** — selesai 2026-04-03
  - `tables.dart`: Products tambah crdtPositive + crdtNegative (G-Counter JSON)
  - `app_database.dart`: schemaVersion 2, migration addColumn crdtPositive+crdtNegative
  - `pn_counter.dart`: PNCounter utility (increment, merge, getValue, fromJson, toJson)
  - `cart_provider.dart`: offline deduct = PNCounter.increment(crdtNegative, nodeId, qty) — bukan LWW
  - `sync_service.dart`: kirim + terima crdt_positive/crdt_negative saat sync
  - Backend sync: merge PNCounter via process_stock_sync (sudah ada di sync.py)
  - Merge rule: max per nodeId → commutative, associative, idempoten — tidak ada conflict
  - `cart_provider.dart`: submitOrder() cek koneksi → online=backend, offline=Drift SQLite
  - Offline: order+items disimpan lokal (isSynced:false), stockQty deduct di Drift sebagai guard anti-oversell
  - Backend sync: setelah order_items diproses, trigger deduct_stock (idempoten via stock.sale event check)
  - `stock_service.py`: _is_sale_already_recorded() — skip deduct jika stock.sale event sudah ada untuk order_id ini
  - Starter: offline jalan penuh, source of truth tetap events table saat sync ke server
  - `backend/models/event.py` — Event model (append-only, partitioned by outlet_id)
  - `backend/services/stock_service.py` — deduct_stock, restock_product, get_stock_history, recompute_stock_from_events
  - `orders.py` — stock deduct sekarang lewat stock_service (tulis stock.sale event dulu)
  - `products.py` restock — sekarang lewat stock_service (tulis stock.restock event dulu)
  - `schemas/stock.py` — tambah outlet_id di ProductRestock
  - Starter: events table = source of truth, products.stock_qty = cache
  - Pro (future): + outlet_stock CRDT untuk offline sync
- [x] **Tier Gating Pro Features** — selesai 2026-04-03
  - `deps.py`: `require_pro_tier` dependency, PRO_TIERS = {pro, business, enterprise}
  - `loyalty.py` + `reservations.py`: router-level gate, 403 untuk Starter
  - `auth.py /pin/verify`: cek tier tenant → 403 Starter (Dapur App = Pro only)
  - Starter: POS, Stock, Shift, Laporan, Connect | Pro+: Dapur, Loyalty, Reservasi, Partial Payment
- [x] **Feature D: Loyalty Points** — selesai 2026-04-02
  - Migration 059: `customer_points` + `point_transactions` (UNIQUE order_id+type, row_version)
  - `backend/api/routes/loyalty.py` — 4 endpoint: balance, earn (idempoten), redeem (optimistic lock), history
  - `backend/api/api.py` — include loyalty router
  - Flutter: `loyalty_provider.dart` (FutureProvider.family), `loyalty_redeem_widget.dart` (slider),
    `loyalty_history_page.dart` (gradient card), `cart_panel.dart` (integrated redeem + grand total)
  - `main.dart` — route `/loyalty/:customerId`
  - Aturan: 1 poin/Rp10.000, 1 poin=Rp100, min 10 poin untuk redeem
- [x] **Feature B: Kasira Connect Storefront** — selesai 2026-04-02
  - `connect.py`: ganti Midtrans → Xendit QRIS (reference_id = tenant_id::payment_id, platform_fee 0.2%)
  - `connect.py`: payment_method di ConnectOrderInput (cash/qris), cash → langsung paid+preparing
  - `connect.py`: POST response + GET /orders/{id} sekarang include full payment + items data
  - `payments.py` webhook: setelah order confirmed → update connect_orders.status = 'confirmed'
  - `app/actions/storefront.ts`: error handling real, mock data include payment object
  - `app/[slug]/order/[id]/page.tsx`: QRIS display + countdown MM:SS + auto-refresh saat expired
- [x] **Feature A: Flutter Dapur App (Kitchen Display)** — selesai 2026-04-02
  - Entry point terpisah: `kasir_app/lib/main_dapur.dart`
    → build dengan `flutter build apk --target lib/main_dapur.dart`
  - `features/dapur/providers/dapur_provider.dart`
    → DapurNotifier: auto-polling Timer setiap 8 detik (configurable)
    → fetchOrders: GET /orders/?status=pending,preparing,ready + GET /orders/?status=done&today=true
    → updateStatus: optimistic update + conflict detection row_version (409 → auto-refresh)
    → dapurStatsProvider: computed stats dari state
  - 6 halaman dapur:
    1. `dapur_splash_page.dart` — dark mode splash, cek AppConfig → /dapur/login atau /dapur/dashboard
    2. `dapur_login_page.dart` — numpad PIN 6 digit, tanpa OTP, panggil POST /auth/pin/verify
    3. `dapur_dashboard_page.dart` — grid 3 tab (Antrian/Dimasak/Siap Saji), badge "PESANAN BARU!" real-time,
       bottom sheet detail per order, auto-refresh indicator, PESANAN BARU flash indicator
    4. `dapur_completed_page.dart` — list pesanan selesai hari ini
    5. `dapur_statistik_page.dart` — stat cards + progress bar per status + alert urgent orders (>15 menit)
    6. `dapur_settings_page.dart` — toggle suara, interval refresh slider (5–30 detik), logout
  - `widgets/order_queue_card.dart` — card per order: timer merah >15 menit kuning >10 menit,
    status badge, 1-tap aksi (Mulai Masak → Siap Saji → Selesai)
  - Backend: `POST /auth/pin/verify` — standalone login phone+PIN (untuk dapur, tanpa OTP)
    → audit log setiap login, return JWT + tenant_id + outlet_id
  - `login_page.dart` — simpan `phone` ke FlutterSecureStorage saat OTP verify (dibutuhkan dapur)
  - `build-apk.yml` — build 2 APK: `kasira-pos-v*.apk` + `kasira-dapur-v*.apk`
  - GoRouter dapur: /dapur → /dapur/login → /dapur/dashboard → /dapur/completed,statistik,settings

- [x] **Feature E: Reservasi + Booking via Connect** — selesai 2026-04-03
  - `backend/models/reservation.py` — Table + Reservation models (row_version, ENUM)
  - `backend/api/routes/reservations.py` — owner CRUD: list/get/confirm/cancel/complete
    → confirm: set meja reserved (Golden Rule #24)
    → cancel/complete: release meja (Golden Rule #24)
    → log_audit setiap WRITE (Rule #2), optimistic lock row_version (Rule #33)
  - `backend/api/routes/connect.py` — tambah 3 endpoint:
    → GET /{slug}/tables → meja tersedia untuk booking form
    → POST /{slug}/booking → buat booking (tanpa login, WA confirmation)
    → GET /bookings/{id} → status polling
  - `backend/api/api.py` — include reservations + loyalty router
  - `app/actions/storefront.ts` — getAvailableTables, createBooking, getBookingStatus
  - `app/[slug]/booking/page.tsx` — form: nama, telepon, tanggal, jam, tamu, meja, catatan
  - `app/[slug]/booking/[id]/page.tsx` — status polling (pending/confirmed/cancelled)
  - `app/[slug]/page.tsx` — tombol "Reservasi Meja" saat cart kosong
- [x] **Feature D (Loyalty) — file yang hilang dibuat ulang** — 2026-04-03
  - `backend/migrations/versions/059_loyalty_points.py` — customer_points + point_transactions
  - `backend/models/loyalty.py` — CustomerPoints + PointTransaction models
  - `backend/api/routes/loyalty.py` — 4 endpoint: balance, earn (idempoten), redeem (optimistic lock), history

- [x] **Feature F: FASE 5 Pre-Pilot** — selesai 2026-04-03
  - Sentry Backend: `sentry-sdk[fastapi]>=2.0.0` di requirements.txt
    + init di `backend/main.py` (only if SENTRY_DSN set, traces_sample_rate=0.1, send_default_pii=False)
    + `SENTRY_DSN` di config.py + .env.example
  - Sentry Frontend: `@sentry/nextjs` di package.json
    + `sentry.client.config.ts` + `sentry.server.config.ts`
    + `instrumentation.ts` (Next.js 14+ native, no experimental flag)
    + `next.config.ts` wrapped dengan `withSentryConfig` (conditional on NEXT_PUBLIC_SENTRY_DSN)
  - APK ke R2: `build-apk.yml` tambah step upload ke Cloudflare R2 (S3-compatible API)
    + Upload kedua APK (pos + dapur) ke `s3://{R2_BUCKET}/apk/`
    + Generate + upload `version.json` ke R2 (Flutter baca ini saat startup — Golden Rule #14 + #15)
    + GitHub Secrets: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL
  - `.env.example` update: ANTHROPIC_API_KEY, SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN, R2 vars (commented)
  - `kasira-setup.sh` update: prompt ANTHROPIC_API_KEY + SENTRY_DSN saat setup VPS
  - pg_dump cron: sudah ada di kasira-setup.sh (tiap 6 jam ke /var/backups/kasira) — ✅ verified OK
  - UptimeRobot: manual setup di dashboard — monitor http://VPS_IP:8000/ dan http://VPS_IP:3000/

## ⏳ IN PROGRESS (per 2026-04-26)
- VPS sudah live: Ubuntu 22.04, semua container running (backend:8000, frontend:3000, db:5432, redis:6379)
- Admin: phone 6285270782220, outlet slug: kasira-coffee (MASTER_OTP sudah dihapus 2026-04-25 — production OTP WA only)
- APK terbaru: **v1.0.51** (POS + Dapur, fix split-bill float vs Decimal), download via GitHub Releases
- Migration terakhir: **086** (`outlets.xendit_callback_token` — BYOK Phase 2)
- Telegram healthcheck cron LIVE (state-change throttle, anti-spam)
- 25 tenant siap pilot (90% confidence cap, 30 conservative cap per `project_publish_readiness.md`)

## ✅ MAJOR MILESTONES 2026-04-12 → 2026-04-26

### Senior Audit + 17 CRITICAL Fixes (2026-04-19)
- 17/17 CRITICAL findings RESOLVED — sync idempotency dedup, HPP unification (4 raw-multiply sites), PRICING_COACH fail-closed Sonnet→Haiku fallback, Fonnte singleton + retry + circuit breaker, Xendit retry+webhook idempotency, async supervisor auto-restart, subscription tier lifecycle + cascade downgrade, sync cursor-based pagination
- Disaster Recovery: R2 restore automation + runbook (CRITICAL #9)
- Observability: Prometheus metrics + structured logging + health aggregate (#10)

### Flutter UX Hardening Batch #14-#18 (2026-04-20)
- Rule #50 outlet scope (anti cross-outlet leak)
- Multi-outlet sync + phone normalize + modal protection
- Printer lock + sync resilience + async boundary
- Node ID isolation `sha256(device|user)` + orphan cleanup + hardened logout
- v1.0.32 published

### Adaptive UI + AI Multi-Turn (2026-04-21)
- Batch #22-#23: AI multi-turn chat via Redis-only session store + Flutter wire + HLC merge + persistent idempotency
- Batch #24: backend hardening & hygiene
- Batch #25: AI chat UX polish v1.0.35
- Batch #26-#27: Adaptive domain classify endpoint + waitlist + AI guardrail + adaptive upgrade sheet + coming soon
- Migration 081 (`sync_idempotency`), 082 (`sync_pagination_indexes`), 083 (`xendit_reliability`)

### Inventory Powerhouse + KG Price Events (2026-04-22)
- Batch #28: POS stock visual guard (isAvailable + isOutOfStock gate)
- Batch #29: Inventory Powerhouse — tabbed Produk & Stok (Flutter v1.0.36)
- Backend: KG Price Events (margin drift WA alert)
- Backend: superadmin waitlist monitoring endpoint

### Starter Margin Tracking (2026-04-24 → 2026-04-25)
- Migration 084: `products.buy_price` untuk Starter margin tracking
- Backend Fase 2: restock unit_buy_price + `GET /reports/margin`
- Flutter Fase 3: Drift v5 + restock buy_price + Untung-Rugi tab
- Dashboard: buy_price form + `/laporan/margin` page (close margin tracking gap)
- UX: clarify "modal" vs "stok" untuk merchant non-technical
- v1.0.39 published

### Split-Bill Float-vs-Decimal Hotfix (2026-04-26 EOD)
- Bug: `pay_items_modal.dart:_selectedTotal` pake double float multiply tanpa quantize-per-share, sementara backend `tab_service.py:items_proportional_due()` quantize via `Decimal('0.01')`. Drift Rp 0.0045/share → backend reject "Nominal pembayaran kurang" walau display match.
- Reproduced: tab cappucino real merchant tax-inclusive ratio non-integer (5K/55K=0.0909..)
- Fix `72f1fff`: `_q2()` helper di Flutter mirror backend quantize. APK v1.0.51 built+deployed kasira.online.
- Sweep agent scheduled: `trig_01PsJEKFr2KEDJF5SBm8opu5` fires 2026-05-03 — audit other proportional compute sites.

### Pre-Launch Hardening (2026-04-25)
- Remove MASTER_OTP bypass (production OTP WA only)
- Xendit reconciliation hardening
- Flutter QRIS polling 30s timeout + retry dialog (FIX #2 security audit)
- RLS bypass added to payment_reconciliation (FIX #3 follow-up — RLS background task gotcha)
- v1.0.40 published

### Split-Bill Humanity + Warkop Ad-Hoc (2026-04-25)
- Split-bill data integrity — table release guard untuk active tab (commit `9762674`, gotcha #15)
- Flutter v1.0.42-v1.0.45: split-bill UX gaps — table tap, info card, grid sub-badge, flow & dashboard nav, active list missing, per-split receipt
- **Migration 085**: warkop ad-hoc per-item payment (`order_items.paid_at` + pay-items endpoint)
- Phase A SHIPPED: pay_items_modal + table_actions_sheet
- Source-of-truth split: `tab.paid_amount` (split/full) vs `items.paid_at` (pay-items adhoc)

### Telegram Healthcheck (2026-04-25)
- `/health` monitor → Telegram bot self-alert via cron (LIVE)
- Replace healthchecks.io plan, pivot karena signup difficulty + Fonnte self-send block
- State-change throttle (anti-spam)

## ✅ AI CHATBOT OWNER (2026-04-09) — Pro Feature
- [x] Chat UI: `app/dashboard/ai/page.tsx` (SSE streaming, suggestion buttons, purple theme)
- [x] SSE Proxy: `app/api/ai/route.ts` (Next.js proxy, httpOnly cookie auth)
- [x] Outlet helper: `app/api/ai/outlet/route.ts`
- [x] Sidebar nav: `app/dashboard/layout.tsx` — "AI Asisten" + PRO badge
- [x] Pro tier gate: `backend/api/routes/ai.py` — query tenant.subscription_tier, 403 Starter
- [x] Tenant model container sync (subscription_tier missing di container lama)
- [x] Admin tenant upgraded ke `pro` di DB
- **DONE**: ANTHROPIC_API_KEY sudah di-set dan backend rebuilt (2026-04-09)

## ✅ FIX REGISTER FLOW (2026-04-09)
- [x] `otp/send` sekarang terima `purpose: "register"` — skip cek user exists, tolak jika nomor sudah terdaftar
- [x] `auth.ts` pakai BACKEND_INTERNAL_URL + sendOtp() terima purpose param
- [x] `register/page.tsx` kirim purpose register

## ✅ BUG FIX 2026-04-09 — Realtime Sync + Order Multi-Item
- [x] Flutter: `ref.invalidate()` dashboardProvider/ordersProvider/productsProvider setelah payment sukses & sync
- [x] Backend: `selectinload().joinedload()` → `selectinload().selectinload()` di create_order (fix MissingGreenlet crash >1 item)
- [x] Backend: `metadata=` → `event_metadata=` di stock_service.py (field name salah)
- [x] `payment_success_page.dart` → ConsumerStatefulWidget (butuh ref untuk invalidate)
- Commits: `3358b34` + `adf20a9` pushed, backend di-restart via docker cp

## ✅ BUG FIX 2026-04-05 — Data Mock + Payment
- [x] `shift_open_page.dart`: ganti TODO mock → real `POST /shifts/open`, simpan shift_session_id ke FlutterSecureStorage
- [x] `payment_modal.dart`: cash tidak lagi silent fail — tampil error jika shift belum buka / payment gagal + kirim shift_session_id
- [x] `backend/api/routes/customers.py`: buat route GET /customers/ + POST /customers/
- [x] `backend/api/api.py`: include customers router
- [x] `customer_selection_modal.dart`: ganti 5 mock hardcoded → real API call + onSelected callback ke cartProvider
- [x] `add_customer_modal.dart`: ganti TODO → real POST /customers/
- [x] `cart_provider.dart`: tambah customerName di CartState, setCustomer() terima name
- [x] `cart_panel.dart`: tampilkan nama pelanggan yang dipilih, pass onSelected callback
- NOTE: File backend harus di-`docker cp` ke container karena tidak ada volume mount kode

## ✅ TAB/BON + SPLIT BILL (2026-04-09) — Pro Feature
- [x] Migration 062: `tabs` + `tab_splits` tables, `tab_id` FK di orders
- [x] Models: `Tab` + `TabSplit` (SQLAlchemy, relationships, row_version)
- [x] Schemas: `TabCreate`, `SplitEqualRequest`, `SplitPerItemRequest`, `SplitCustomRequest`, `PaySplitRequest`
- [x] API Routes: `backend/api/routes/tabs.py` — 10 endpoints:
  - `POST /tabs/` — buka tab (link ke meja)
  - `GET /tabs/` — list tabs per outlet
  - `GET /tabs/{id}` — detail tab + splits
  - `POST /tabs/{id}/orders` — tambah order ke tab
  - `POST /tabs/{id}/split/equal` — split rata (÷ jumlah orang)
  - `POST /tabs/{id}/split/per-item` — split per item (assign item ke orang)
  - `POST /tabs/{id}/split/custom` — split nominal bebas
  - `POST /tabs/{id}/pay-full` — 1 orang bayar semua
  - `POST /tabs/{id}/splits/{split_id}/pay` — bayar per orang (bisa beda metode: cash/QRIS)
  - `POST /tabs/{id}/cancel` — batalkan tab
- [x] Pro tier gate (require_pro_tier dependency)
- [x] Semua WRITE endpoint ada audit log
- [x] Optimistic locking (row_version) di semua update
- [x] Idempotency key di payment
- [x] Migration + container deployed, backend running
- [x] Flutter UI: tab_provider.dart, tab_list_page.dart, tab_detail_page.dart
- [x] Flutter widgets: open_tab_modal.dart, split_bill_modal.dart, pay_split_modal.dart
- [x] GoRouter: /tabs + /tabs/:tabId
- [x] Dashboard: tombol "Tab / Bon" di header

## ❌ BELUM MULAI / OPEN (per 2026-04-26)
1. ~~**ANTHROPIC_API_KEY**~~ — ✅ DONE 2026-04-09
2. ~~**UptimeRobot**~~ — REPLACED 2026-04-25 oleh Telegram healthcheck cron (signup HC.io susah, Fonnte self-send block)
3. **Xendit sub-account** — daftarkan outlet di Xendit untuk aktifkan QRIS production (outlets.xendit_business_id masih NULL untuk live merchant)
4. **Multi-outlet (Business tier)** — belum mulai, terakhir di FASE 6 belum disentuh
5. **APK v1.0.46 deploy** — warkop pattern Phase A udah merge ke main, build APK pending dispatch
6. **Vultr credit $300** — expire 2026-05-11 (`project_vultr_credit.md`), reminder 10 Mei cek dashboard
7. **Fonnte device pisah** — owner nomor = device = WA block self-send (`project_fonnte_otp_gotcha.md`), pisahin sender vs admin nomor sebelum publish

## Keputusan Teknikal (JANGAN DIUBAH TANPA ALASAN)
- ORM: SQLAlchemy async (bukan Tortoise)
- Migration: Alembic
- Validation: Pydantic v2
- Auth: PyJWT + bcrypt
- Background: Celery + Redis
- Flutter state: Riverpod
- Flutter offline: Drift
- HTTP Flutter: Dio + Retrofit
- Printer: bluetooth_print package
- Multi-tenant: schema-per-tenant di PostgreSQL
- AI streaming: SSE (bukan WebSocket) untuk chatbot
- Payment: **Xendit xenPlatform QRIS** + idempotency key (Master-Sub Account, platform fee 0.2%)
- Tax: PB1 10%, PPN 12%, service charge configurable
- Loyalty: 1 poin/Rp10.000 earn, 1 poin=Rp100 redeem, min 10 poin, UNIQUE(order_id,type)
- Dapur App: entry point terpisah main_dapur.dart, polling 8 detik, dark UI theme
- PIN Login: `/auth/pin/verify` untuk dapur (phone+PIN tanpa OTP)
- AI Model: Haiku default, Sonnet hanya Pro+/complex task — via get_model_for_tier()
- AI Context cache: Redis key ai:context:{outlet_id}, TTL sampai 00.00 WIB
- AI SSE format: {type: chunk/done/error, content, intent, tokens_used, model}

## Branch Git
- Branch aktif: `main`
- Semua commit langsung ke `main`, push ke `origin/main`

## Lanjut Berikutnya (per 2026-04-26)
Production-ready. Fokus pivot ke **acquisition + monetisation**:
1. **Build & deploy APK v1.0.46** — warkop ad-hoc pattern Phase A
2. **Onboard pilot merchant** — 25 tenant cap aman, 30 conservative
3. **Xendit live activation** — daftarkan sub-account untuk live QRIS (sandbox sudah test)
4. **Multi-outlet (Business tier)** — design + migration + tier gating
5. **Marketing landing page polish** — SEO sudah, tinggal copy + testimonial pilot

## Context Files Status
- context/database.md    → ⏳ In Progress
- context/auth.md        → ⏳ Belum dibuat
- context/orders.md      → ⏳ Belum dibuat
- context/inventory.md   → ⏳ Belum dibuat
- context/payment.md     → ⏳ Belum dibuat
- context/flutter-kasir.md → ⏳ Belum dibuat
- context/connect.md     → ⏳ Belum dibuat
- context/dapur.md       → ⏳ Belum dibuat
