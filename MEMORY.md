# KASIRA — Long-Term Memory
# Update ini setiap selesai satu task!

## 🗺️ ROADMAP PROGRESS (Menuju Tier Starter)
- ✅ **FASE 0: Fondasi** (Semua Migration, Docker, VPS, Backend Core)
- ✅ **FASE 1: Auth** (OTP WA, JWT, Device Binding, Role Check)
- ✅ **FASE 2: Core POS Starter** (Products, Orders, Payment QRIS **Xendit xenPlatform**, Stock Deduct)
- ✅ **FASE 3: Flutter Kasir App** (15 layar lengkap, GoRouter, Sync Engine, Offline Mode)
- ✅ **FASE 4: Owner Dashboard Next.js** (Owner Login, Laporan, Menu, dll)
- 🔴 **FASE 5: Pilot** (Pre-Pilot Checklist belum tuntas)
- 🔴 **FASE 6: Pro Features** (Reservasi, Chatbot AI, dll)

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

## ⏳ IN PROGRESS
- VPS Deployment: kasira-setup.sh siap, butuh VPS Ubuntu 22.04 untuk deploy

## ❌ BELUM MULAI (Prioritas sesuai urutan)
1. **VPS Deployment** — jalankan `bash kasira-setup.sh` di server Ubuntu 22.04
   - Isi FONNTE_TOKEN, XENDIT_API_KEY, ANTHROPIC_API_KEY, SENTRY_DSN saat prompted
   - Setelah up: setup UptimeRobot monitor untuk /health endpoint
   - Setelah up: trigger build-apk.yml untuk upload APK ke R2 (isi GitHub Secrets dulu)

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
- Branch aktif: `claude/review-documentation-qqAkC`
- Branch fitur lama: `feat/loyalty-points` (sudah merged ke branch aktif)
- Semua commit harus ke `claude/review-documentation-qqAkC`

## Lanjut Berikutnya
**Feature F: FASE 5 Pre-Pilot** — checklist sebelum deploy ke VPS produksi:
- UptimeRobot monitoring setup
- Sentry error tracking integration
- APK upload ke Cloudflare R2 (build-apk.yml update)
- .env.example update (tambah ANTHROPIC_API_KEY)
- pg_dump cron sudah ada di kasira-setup.sh → verify running

## Context Files Status
- context/database.md    → ⏳ In Progress
- context/auth.md        → ⏳ Belum dibuat
- context/orders.md      → ⏳ Belum dibuat
- context/inventory.md   → ⏳ Belum dibuat
- context/payment.md     → ⏳ Belum dibuat
- context/flutter-kasir.md → ⏳ Belum dibuat
- context/connect.md     → ⏳ Belum dibuat
- context/dapur.md       → ⏳ Belum dibuat
