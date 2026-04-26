# SESSION — 2026-04-03
# Claude update file ini otomatis tiap task selesai
# Kalau reconnect: baca CLAUDE.md → MEMORY.md → SESSION.md ini, lalu lanjut dari "## NEXT ACTION"

## ✅ SELESAI SESI INI (update terakhir)
- [x] Fix upload gambar: pipe raw body (jangan parse FormData), gunakan BACKEND_INTERNAL_URL=http://backend:8000
- [x] Fix ProductResponse: tambah computed_field price=base_price dan stock=stock_qty untuk Flutter & storefront
- [x] Fix read_products: brand_id sekarang Optional — infer dari tenant user saat Flutter tidak kirim brand_id
- [x] Fix fetchWithAuth: auto trailing-slash normalization (hindari 307 yang drop Authorization header)
- [x] **Fix 500 error products.py** — tambah `from datetime import datetime, timezone` (dipakai di update_product), hapus `from datetime import` duplikat di delete_product
- [x] **Fix audit log tidak tersimpan** — tambah `await db.commit()` setelah setiap `log_audit()` di products.py + categories.py
- [x] **Rebuild backend container** — container lama masih run kode dengan `request_id` di `log_audit()` yang menyebabkan TypeError → 500

## ✅ SELESAI SESI INI
- [x] VPS live: semua container running (backend 8000, frontend 3000, db, redis)
- [x] Feature F: FASE 5 Pre-Pilot (Sentry, R2 APK upload, env.example, kasira-setup.sh)
- [x] Tier Gating, CRDT Stock, Event-Sourced Stock, Offline-First PNCounter (sesi sebelumnya)
- [x] **Owner Dashboard — Kategori CRUD** (tab Kategori di menu/page.tsx)
  - Tambah/edit/hapus kategori, toggle aktif/non-aktif
  - Fix getCategories: outlet_id → brand_id
  - Fix categories.py: hapus `request_id` dari log_audit()
- [x] **Owner Dashboard — Produk CRUD Lengkap**
  - Tambah tombol hapus produk (soft delete)
  - Fix field names: price→base_price, stock→stock_qty, outlet_id→brand_id
  - Fix getProducts: pakai brand_id, trailing slash
  - Fix toggleProductActive: kirim row_version
  - Fix updateProduct: kirim row_version
- [x] **Fix 307 Redirect Bug** — `fetchWithAuth` sekarang normalize trailing slash otomatis
  - Semua GET yang kena redirect (outlets, categories, products) sekarang langsung benar
- [x] **Upload Foto Produk dari Device**
  - Backend: `backend/api/routes/media.py` — POST /media/upload (auth required, max 5MB)
  - Backend: `main.py` — mount StaticFiles /uploads/ → /app/uploads/
  - Backend: `api.py` — include media router
  - `docker-compose.yml` — tambah volume uploads_data:/app/uploads
  - Next.js: `app/api/upload/route.ts` — proxy upload (baca httpOnly cookie server-side)
  - UI: file picker + preview + ganti/hapus foto
- [x] **Fix event.py SQLAlchemy error** — kolom `metadata` reserved, rename ke `event_metadata`

---

## STATUS VPS

| Service | Status | Port |
|---------|--------|------|
| Backend (FastAPI) | ✅ Running | 8000 |
| Frontend (Next.js) | ✅ Running | 3000 |
| PostgreSQL | ✅ Running | 5432 |
| Redis | ✅ Running | 6379 |

**Admin**: phone `6285270782220`, OTP dev `123456`, PIN `111222`
**Outlet slug**: `kasira-coffee`
**Dashboard**: http://103.189.235.164:3000/dashboard/menu

---

## ✅ SELESAI SESI INI (dashboard + storefront sync fix)
- [x] **Fix storefront tampil mock data** — `storefront.ts` pakai `BACKEND_INTERNAL_URL` (bukan `NEXT_PUBLIC_API_URL`), hapus semua mock fallback, tambah null guard untuk slug
- [x] **Fix slug undefined** — tambah `if (!slug) return` di useEffect `[slug]/page.tsx`
- [x] Rebuild frontend container — hapus cached bundle lama
- [x] **Fix dashboard storefront link = "undefined"** — tambah `slug`, `is_open`, `opening_hours` ke `OutletInDBBase` schema (belum ada sebelumnya)
- [x] **Fix settings outlet tidak bisa save** — tambah endpoint `PUT /outlets/{id}` (belum ada), fix `OutletUpdate` schema
- [x] **Fix log_audit request_id kwarg di outlets.py** → sama seperti products.py sebelumnya
- [x] **Fix teks "QRIS Midtrans" → "QRIS Xendit"** di settings/page.tsx
- [x] **Fix connect endpoint** — tambah `slug` ke outlet response, flush Redis cache
- [x] **Cover image storefront** — migration 060 `cover_image_url` di outlets, upload dari settings, tampil di storefront hero
- [x] **Fix settings save error** — settings page di-rewrite: form sekarang kirim `cover_image_url`, `opening_hours` handle string JSONB, error message lebih jelas
- [x] **Hapus tombol Reservasi dari storefront** — fitur Pro, tidak boleh ada di Starter tier

---

## ✅ SELESAI SESI INI (pro teaser + kasir bug fix)
- [x] **Fix Kelola Kasir — semua endpoint backend dibuat**
  - `GET /users/` — list kasir (non-superuser) per tenant
  - `POST /users/cashier` — tambah kasir baru (owner only, validasi phone 628, PIN 6 digit)
  - `PUT /users/{id}/status` — toggle aktif/nonaktif
  - `PUT /users/{id}/pin` — reset PIN kasir
  - Semua endpoint: audit log + tenant isolation
- [x] **Pro Features Teaser**
  - `app/dashboard/pro/page.tsx` — 6 feature cards (Reservasi, AI Chatbot, Loyalty, Tab/Bon, Multi-Outlet, Laporan Lanjutan), card grayscale+overlay, badge PRO kuning, tombol CTA ke WA
  - `app/dashboard/layout.tsx` — nav item "Fitur Pro" dengan Lock icon + PRO badge di sidebar
- [x] Rebuild backend + frontend image dan container

## ✅ SELESAI SESI INI (bug fix kasir + laporan)
- [x] **Fix Kelola Kasir — cashier.name → cashier.full_name** (crash saat render list)
- [x] **Fix Kelola Kasir — error message** dari backend pakai `data.detail`, bukan `data.message` → sekarang `data.message || data.detail`
- [x] **Fix Laporan — orders date filter** — backend `GET /orders/` tambah `start_date` & `end_date` query params
- [x] **Fix Laporan — reports date param** — backend `GET /reports/daily` tambah `report_date` param (sebelumnya selalu return hari ini), frontend kirim `report_date` bukan `date`
- [x] Rebuild backend + frontend container

## ✅ SELESAI SESI INI (auth bug fixes - 2026-04-04)
- [x] **Fix Dashboard login tidak bisa masuk** — root cause: `fetchWithAuth` tambah trailing slash `/users/me/` → FastAPI 307 redirect → Node.js fetch drop Authorization header → 401 → redirect balik ke login
  - `app/actions/api.ts`: Ganti ke `BACKEND_INTERNAL_URL` (http://backend:8000) untuk server actions
  - `app/actions/api.ts`: Tambah `redirect: 'manual'` + manual follow 307/308 dengan headers preserved
  - `app/actions/api.ts`: Trailing slash normalization sekarang skip untuk endpoints resource (/me, /status, /pin, dll)
  - Rebuild & restart frontend container ✅
- [x] **Fix Flutter APK SharedPreferences URL lama** — jika user install APK baru tapi SharedPreferences masih simpan `http://` URL lama, sekarang diabaikan dan pakai `defaultBaseUrl` (https://kasira.online)
  - `kasir_app/lib/core/config/app_config.dart`: Hanya load saved URL jika startsWith('https://')

## ✅ SELESAI SESI INI (2026-04-09) — Realtime Sync + Order Bug Fix

### Bug Fix 1: Data penjualan tidak realtime sync ke dashboard/laporan
- [x] `cart_panel.dart`: tambah `ref.invalidate(dashboardProvider/ordersProvider/productsProvider)` setelah payment sukses
- [x] `pos_page.dart`: invalidate semua provider setelah offline→online sync selesai
- [x] `payment_success_page.dart`: convert ke `ConsumerStatefulWidget`, invalidate saat navigasi ke dashboard
- **Efek:** Dashboard stats, order list, stock produk langsung update tanpa manual refresh

### Bug Fix 2: Order >1 item crash 500 (CRITICAL)
- [x] `orders.py`: ganti `selectinload(Order.items).joinedload(OrderItem.product)` → `selectinload().selectinload()` — joinedload trigger lazy load di async context → MissingGreenlet error
- [x] `stock_service.py`: fix `metadata=` → `event_metadata=` (field name salah setelah rename, metadata stock event tidak tersimpan ke DB)
- [x] Backend di-restart via `docker cp` + `docker restart`
- [x] Tested: order 2 item + cash payment → sukses
- **Commits:** `3358b34` (realtime sync) + `adf20a9` (order fix) — pushed to `origin/main`

### Juga di commit ini (minor):
- [x] `page.tsx` landing page: hapus kata "pilot" dari CTA copy

---

## ✅ SELESAI SESI INI (2026-04-09) — Register Fix + AI Chatbot Pro

### Fix Register Flow
- [x] Backend `otp/send`: tambah `purpose` param — `register` skip cek user exists, tolak jika nomor sudah terdaftar
- [x] `backend/schemas/auth.py`: tambah `purpose: Optional[Literal["login","register"]]` di OTPSendRequest
- [x] `app/actions/auth.ts`: `sendOtp()` terima param `purpose`, pakai `BACKEND_INTERNAL_URL` (bukan NEXT_PUBLIC)
- [x] `app/register/page.tsx`: kirim `purpose: 'register'` saat sendOtp
- [x] Deploy backend (docker cp + restart) + rebuild frontend

### AI Chatbot Owner (Pro Feature)
- [x] **Chat UI**: `app/dashboard/ai/page.tsx` — full chat interface, suggestion buttons, SSE streaming, model+token info
- [x] **SSE Proxy**: `app/api/ai/route.ts` — Next.js API route proxy ke backend (handle httpOnly cookie auth)
- [x] **Outlet Helper**: `app/api/ai/outlet/route.ts` — expose outlet_id dari httpOnly cookie ke client
- [x] **Sidebar Nav**: `app/dashboard/layout.tsx` — tambah "AI Asisten" dengan Bot icon + PRO badge (purple theme)
- [x] **Pro Tier Gate**: `backend/api/routes/ai.py` — query tenant.subscription_tier, 403 jika bukan Pro+
- [x] **Tenant Model Sync**: container tenant.py tidak punya subscription_tier — docker cp fix
- [x] **Tested**: Starter → 403 ditolak. Pro → stream OK (error karena ANTHROPIC_API_KEY placeholder)
- [x] Admin tenant di-upgrade ke `pro` di DB untuk testing
- **Backend AI service sudah ada sebelumnya**: `ai_service.py` (intent classifier, context builder, SSE stream, model selector)

### IdCloudHost Issue
- VPS semua service **online** (backend, frontend, db, redis, nginx, SSL valid)
- Tapi akses publik **timeout** — masalah di jaringan IdCloudHost, bukan server
- Backup lengkap dibuat: `/root/kasira-backup-20260409.tar.gz` (DB + uploads + .env)

---

## ✅ SELESAI SESI INI (2026-04-09) — Tab/Bon + Split Bill (Pro Feature)

### Backend
- [x] Migration 062: `tabs` + `tab_splits` tables + `orders.tab_id` FK
- [x] Models: `backend/models/tab.py` — Tab + TabSplit (row_version, relationships)
- [x] Schemas: `backend/schemas/tab.py` — full CRUD + split bill schemas
- [x] Routes: `backend/api/routes/tabs.py` — 10 endpoints (open, list, detail, add order, split equal/per-item/custom, pay full, pay split, cancel)
- [x] `backend/api/api.py` — include tabs router
- [x] `backend/models/order.py` — tambah tab_id FK + relationship
- [x] Pro tier gate via `require_pro_tier` dependency
- [x] Migration deployed + backend restarted in container

### Split Bill Options
1. **Bayar semua** — 1 orang bayar total (`/tabs/{id}/pay-full`)
2. **Split rata** — total ÷ jumlah orang (`/tabs/{id}/split/equal`)
3. **Split per item** — assign item ke orang, bayar masing-masing (`/tabs/{id}/split/per-item`)
4. **Split custom** — kasir input nominal per orang (`/tabs/{id}/split/custom`)
5. Setiap split bisa bayar dengan metode berbeda (cash/QRIS)

### Flutter Kasir UI
- [x] `features/tabs/providers/tab_provider.dart` — TabNotifier + TabModel + TabSplitModel (Riverpod)
- [x] `features/tabs/presentation/pages/tab_list_page.dart` — list tabs, filter aktif/selesai, buka tab baru
- [x] `features/tabs/presentation/pages/tab_detail_page.dart` — detail tab, list splits, bayar per split
- [x] `features/tabs/presentation/widgets/open_tab_modal.dart` — form buka tab (nama tamu, jumlah tamu)
- [x] `features/tabs/presentation/widgets/split_bill_modal.dart` — pilih metode (bagi rata/custom), input jumlah orang
- [x] `features/tabs/presentation/widgets/pay_split_modal.dart` — bayar per orang (cash/QRIS), hitung kembalian
- [x] `main.dart` — GoRouter /tabs + /tabs/:tabId
- [x] `dashboard_page.dart` — tombol "Tab / Bon" di header dashboard

### ANTHROPIC_API_KEY
- [x] Key di-set di `.env`, backend rebuilt

---

## ✅ SELESAI SESI INI (2026-04-10) — Deep Bug Fix Starter Production-Ready

### CRITICAL FIX 1: Dashboard Login Gagal
- [x] `config.py`: tambah `MASTER_OTP` setting (configurable, bukan hardcoded "123456")
- [x] `auth.py`: OTP verify + register → pakai `settings.MASTER_OTP`, decode bytes safety
- [x] `.env`: tambah `MASTER_OTP=123456` + `BACKEND_INTERNAL_URL=http://backend:8000`
- **Root cause**: ENVIRONMENT=production block hardcoded dev OTP "123456", BACKEND_INTERNAL_URL tidak di-set

### CRITICAL FIX 2: Riwayat Kas Tidak Sinkron
- [x] `schemas/shift.py`: tambah `CashPaymentSummary`, `ShiftWithActivitiesResponse` sekarang include `cash_payments`, `total_cash_sales`, `total_qris_sales`
- [x] `shifts.py`: `_enrich_shift_with_payments()` — query Payment linked ke shift, return display_number + net amount
- [x] `shifts.py`: GET `/shifts/{id}/activities` sekarang return `{activities, cash_payments}`
- [x] `shift_page.dart`: tampilkan Penjualan Cash, QRIS, Penerimaan Lainnya, Pengeluaran di tutup shift
- [x] `cash_drawer_history_page.dart`: merge CashActivity + Payment transactions, sorted by time
- **Root cause**: shift activities cuma CashActivity, payment transactions tidak termasuk

### CRITICAL FIX 3: Connect Order — Stock Event + Audit Log
- [x] `connect.py`: stok deduction sekarang via `deduct_stock()` service (event-sourced, Golden Rule #8)
- [x] `connect.py`: tambah `log_audit()` setelah order commit (Golden Rule #2)
- [x] `connect.py`: restructure flow — create order dulu, deduct stock dengan order_id

### HIGH FIX 4: Flutter Online Order Missing shift_session_id
- [x] `cart_provider.dart`: `_submitOnline()` sekarang baca `shift_session_id` dari SecureStorage, kirim ke backend

### HIGH FIX 5: Connect Bugs
- [x] `connect.py`: `Table.is_active == 'true'` → `True` (boolean)
- [x] `connect.py`: idempotency key scoped ke outlet (JOIN ConnectOutlet)
- [x] `connect.py`: `datetime.datetime.utcnow()` → `datetime.datetime.now(datetime.timezone.utc)`

### HIGH FIX 6: Double Commits
- [x] `categories.py`: 3 endpoint (create/update/delete) — hapus double commit, pakai flush+commit
- [x] `products.py`: 4 endpoint (create/update/delete/restock) — hapus double commit

### MEDIUM FIX 7: Reports
- [x] `reports.py`: tambah `end_of_day` boundary (sebelumnya cuma `>= start_of_day`, bisa bocor next day)
- [x] `reports.py`: tambah `Product.deleted_at.is_(None)` di top_products join
- [x] `reports.py`: tambah `Payment.deleted_at.is_(None)` di semua subquery

### OTHER
- [x] `payments.py`: `asyncio.create_task()` WA receipt wrapped in try/except (fire-and-forget safety)

---

## ✅ SELESAI SESI INI (2026-04-10) — Production Hardening + SEO

### Deploy & E2E Test
- [x] Semua fix deployed ke container (backend + frontend rebuilt)
- [x] **E2E Test 1 (API)**: 14/14 PASS — register, login, shift, order, payment, stock, audit
- [x] **E2E Test 2 (Dita Coffee real merchant)**: 20/25 PASS — 5 fail = test script bukan bug
- [x] MASTER_OTP dihapus dari .env — OTP hanya via WA Fonnte (production mode)
- [x] APK v1.1.0 built + published di GitHub Releases

### Production Hardening
- [x] **Payment reconciliation**: asyncio background task, auto-expire pending QRIS >10 min (Rule #38)
- [x] **OTP verify rate limit**: max 5 attempts/15min per phone (brute-force protection)
- [x] **APK version endpoint**: reads from version.json (auto-update via GitHub Actions, Rule #14)
- [x] **Tenant model ENUM**: subscription_tier/status pakai PostgreSQL ENUM (fix register crash)
- [x] **Audit log auto-commit**: log_audit() sekarang commit sendiri (fix missing audit entries)
- [x] **Product MissingGreenlet**: selectinload(category) on create/update/restock
- [x] **Storefront cache invalidation**: Redis cache di-invalidate saat stock berubah

### SEO Landing Page
- [x] Full metadata: OG, Twitter Card, canonical, keywords, robots directive
- [x] Dynamic OG image 1200x630 (logo + tagline + value props)
- [x] Dynamic favicon 32x32
- [x] robots.ts: allow /, block /dashboard/ /api/ /onboarding/
- [x] sitemap.xml: homepage, login, register
- [x] JSON-LD structured data (SoftwareApplication schema)

### Git Commits (10 total hari ini)
- `c89f01b` — 15 bug fixes (login, shift, connect, reports)
- `9883770` — auth.ts double path, config extra=ignore
- `951ed5f` — payment reconciliation + rate limit + APK version
- `7b834dd` — tenant ENUM + audit auto-commit
- `decd9c7` — product MissingGreenlet fix
- `e334ab9` — storefront cache invalidation
- `a9b6ba5` — complete SEO setup

---

## ✅ SELESAI SESI INI (2026-04-11) — Dashboard-Kasir Sync Fix

### Bug: Data penjualan kasir tidak muncul di dashboard owner
- [x] **Fix dashboard `page.tsx`** — field names salah: `total_revenue` → `revenue_today`, `total_orders` → `order_count`
- [x] **Fix `laporan/page.tsx`** — pakai `report.payment_breakdown` dari API (bukan hitung dari `o.payment_method` yang tidak ada di OrderResponse)
- [x] **Fix `getWeeklyRevenue`** — `json.data?.total_revenue` → `json.data?.revenue_today` (chart 7 hari selalu 0)
- [x] **Fix `reports.py`** — tambah `active_shifts` (count shift open) + `critical_stock_items` (stock ≤ threshold) di response
- [x] **Fix `orders.py` + `order.py` schema** — tambah `payment_method` + `payment_status` di OrderResponse (join Payment table), supaya tabel riwayat transaksi tampil metode pembayaran
- [x] Backend deployed (docker cp + restart), frontend rebuilt + recreated

---

## ✅ SELESAI SESI INI (2026-04-11) — Reservasi Pro Feature

### Backend
- [x] Migration 064: `reservation_settings` table, upgrade `reservations` (new columns), `tables.floor_section`
- [x] Models: `Reservation`, `ReservationSettings`, `Table` (updated)
- [x] Schemas: full CRUD + storefront schemas
- [x] Routes `reservations.py`: 10 endpoints (CRUD + confirm/seat/complete/cancel/no-show + settings)
- [x] Routes `tables.py`: CRUD meja (create/update/delete + floor section)
- [x] Routes `connect.py`: public storefront `GET /connect/{slug}/reservation/slots` + `POST /connect/{slug}/reservation`
- [x] Auto-assign table logic (smallest capacity that fits, no time conflict)
- [x] WA notification via Fonnte (konfirmasi + cancel)
- [x] Pro tier gate (`require_pro_tier`)

### Dashboard UI
- [x] `/dashboard/reservasi` — daily timeline, date nav, status filter, create modal, detail modal with actions
- [x] `/dashboard/reservasi/settings` — reservation settings form (enable, slot duration, hours, deposit, auto-confirm)
- [x] `/dashboard/reservasi/meja` — table management grouped by floor section
- [x] Sidebar: "Reservasi" nav with PRO badge
- [x] API functions: 13 new server actions in `api.ts`

### Also this session
- [x] Fix dashboard-kasir sync (field names mismatch)
- [x] Fix register: `is_superuser=true` for new merchant owners
- [x] Fix OTP rate limit (3→10), error handling Flutter
- [x] APK v1.2.0 built & published

---

## ✅ SELESAI SESI INI (2026-04-11) — WA Bot + Flutter Reservasi + Dashboard Fixes

### WhatsApp AI Bot
- [x] `POST /webhook/fonnte` + `/webhooks/fonnte` — dual route
- [x] `wa_bot.py` — 7 intents keyword-based (greeting, menu, reservasi, cek/cancel reservasi, general, order_status)
- [x] Multi-turn reservation flow via Redis (date→time→guests→name→confirm)
- [x] Flexible parsing: "besok", "7 malam", "15 April"
- [x] Auto-assign table, check slot availability
- [x] AI fallback Claude Haiku for ambiguous messages (150 token max)
- [x] Fonnte webhook URL set: `https://kasira.online/api/v1/webhooks/fonnte`

### Flutter APK v1.3.0
- [x] Tab "Reservasi" di bottom nav dashboard kasir
- [x] Reservation list page (grouped by status, date nav, detail+actions)
- [x] Table grid page (color-coded, floor sections)
- [x] Create reservation modal
- [x] Build success, published to GitHub Releases

### Dashboard Fixes
- [x] Tier-aware layout: 1 gradient PRO badge, flat nav for Pro, locked for Starter
- [x] `/users/me` return `subscription_tier`
- [x] `reports/daily` return `shift_status` (Flutter fix)
- [x] `get_current_tenant` match UUID (was matching schema_name only)
- [x] `require_pro_tier` use `.value` for enum comparison
- [x] Storefront tier badge dynamic (was hardcoded 'starter')
- [x] Reservation button conditional (only when enabled)
- [x] Auto-invalidate Redis cache on outlet/settings/tier change
- [x] Dashboard reservasi: auto-navigate to nearest upcoming + timezone fix
- [x] Table model: position_x/y Float fix
- [x] GitHub Actions workflow: reset to origin/main before version.json push

---

---

## ✅ SESI 2026-04-19 — Senior Audit + 17 CRITICAL FIXES
Role-swap ke auditor (`feedback_senior_audit_pattern.md`) → nemuin 17 CRITICAL bug yang gue miss sendiri. Semua fixed:
- **#2 + #8 HPP unification** — 4 raw-multiply sites pake helper `unit_utils.py` (pricing_coach, menu_engineering, knowledge_graph, ai_service)
- **#6 Sync idempotency dedup** di `/sync/` push (Migration 081)
- **#7 Sync cursor-based pagination** (Migration 082) — fix offline 3-hari load
- **#9 R2 restore automation** + disaster recovery runbook
- **#10 Observability**: Prometheus metrics + structured logging + health aggregate
- **#11 Async supervisor auto-restart** + health endpoint
- **#12 Xendit retry backoff** + webhook idempotency + fail-safe (Migration 083)
- **#13 Fonnte singleton** + retry + circuit breaker
- **#14 PRICING_COACH fail-closed** Sonnet→Haiku fallback (preserve quota)
- **#15 + #16 Subscription tier lifecycle** + cascade downgrade

---

## ✅ SESI 2026-04-20 — Flutter UX Hardening Batch #14-#18
APK v1.0.27 → v1.0.32. Close audit holes:
- **Batch #14**: Rule #50 outlet scope verification + tax config + UI polish
- **Batch #15**: Multi-outlet sync + phone normalize + modal protection
- **Batch #16**: Printer lock + sync resilience + async boundary (`unawaited()` pattern)
- **Batch #17**: Node ID isolation `sha256(device|user)` + orphan cleanup + hardened logout
- **Batch #18**: Atomic batch.update + Dio CancelToken + performLogout orphan cleanup
- **POS auto-print + WA customer save** di payment success path

---

## ✅ SESI 2026-04-21 — AI Multi-Turn + Adaptive Domain
APK v1.0.32 → v1.0.36:
- **Batch #19-#21**: UUID attr error fix + dine-in table release (Rule #50 follow-up) + stale order janitor + close ghost race janitor↔payment settle
- **Batch #22**: AI multi-turn chat via Redis-only session store
- **Batch #23**: Flutter wire multi-turn + HLC merge + persistent idempotency
- **Batch #24**: Backend hardening & hygiene
- **Batch #25**: AI chat UX polish v1.0.35
- **Batch #26**: Adaptive UI domain classify endpoint + Flutter infrastructure
- **Batch #27**: Strategic positioning — waitlist + AI guardrail + adaptive upgrade sheet + coming soon

---

## ✅ SESI 2026-04-22 — Inventory Powerhouse + KG Price Events
APK v1.0.36:
- **Batch #28**: POS stock visual guard (isAvailable + isOutOfStock gate)
- **Batch #29**: Inventory Powerhouse — tabbed Produk & Stok di Flutter
- **Backend Batch #28**: superadmin waitlist monitoring endpoint
- **Backend Batch #29**: KG Price Events (margin drift WA alert)
- Hotfix: missing `sync_provider.dart` import + Dart-side filter low-stock count
- Untrack `loadtest/` (contained JWT)

---

## ✅ SESI 2026-04-24 → 2026-04-25 — Starter Margin Tracking
Fitur **Untung-Rugi** untuk Starter tier:
- **Migration 084**: `products.buy_price`
- **Backend Fase 2**: `restock` accept `unit_buy_price` + `GET /reports/margin`
- **Flutter Fase 3**: Drift v5 + restock buy_price form + Untung-Rugi tab di laporan
- **Dashboard**: buy_price form di product create/edit + `/laporan/margin` page
- **UX clarity**: "modal" vs "stok" untuk merchant non-technical (`9538341`)
- APK v1.0.39 published

---

## ✅ SESI 2026-04-25 — Pre-Launch Hardening
Production hardening sebelum publish:
- **Remove MASTER_OTP bypass** — production OTP WA only (`cbb833a`)
- **Xendit reconciliation** hardening
- **FIX #2 security audit**: Flutter QRIS polling 30s timeout + retry dialog
- **FIX #3 follow-up**: RLS bypass added to `payment_reconciliation` background task — RLS gotcha (CLAUDE.md gotcha #16: background task tanpa `SET LOCAL app.current_tenant_id = ''` → silent broken)
- APK v1.0.40 published

---

## ✅ SESI 2026-04-25 — Split-Bill Humanity + Warkop Ad-Hoc
APK v1.0.40 → v1.0.45:
- **Split-bill data integrity** (`9762674`): table release guard untuk active tab — kitchen mark order ready/completed → table di-release prematurely → janitor heal back. Fix: query `Tab.status` + skip release kalau active. 2 code path: `orders.py:519-533` + `stale_order_cleanup.py:185-220`. Reference: gotcha #15.
- **v1.0.42**: split-bill UX gaps — table tap, info card, grid sub-badge
- **v1.0.43**: split-bill flow & dashboard navigation gaps
- **v1.0.44**: split-bill humanity — active list missing + per-split receipt
- **v1.0.45**: chore version bump
- **Migration 085**: warkop ad-hoc per-item payment (`order_items.paid_at`)
- **Phase A SHIPPED**: pay_items_modal + table_actions_sheet di Flutter
- **Source-of-truth split**: `tab.paid_amount` untuk split/full, `items.paid_at` untuk pay-items adhoc
- APK v1.0.46 build pending deploy (warkop pattern)

---

## ✅ SESI 2026-04-25 — Telegram Healthcheck Cron
- `/health` monitor → Telegram bot self-alert via cron (LIVE)
- Replace healthchecks.io plan, pivot karena signup difficulty + Fonnte self-send block (`project_fonnte_otp_gotcha.md`)
- State-change throttle (anti-spam)
- Script: `scripts/healthcheck_ping.sh` (untracked)

---

## ⏭️ NEXT ACTION (per 2026-04-26)

### PRIORITAS 1 — Build & Deploy APK v1.0.46
- Warkop ad-hoc Phase A udah merge ke main, build APK pending
- Cek gotcha #13: push commit terakhir dulu, verify `git log origin/main` match lokal, baru dispatch
- Verify `head_sha` di workflow run match latest push

### PRIORITAS 2 — Onboard Pilot Merchant
- 25 tenant cap aman publish (90% confidence per `project_publish_readiness.md`)
- 30 conservative cap
- Ops hardening 4-quick-wins sudah di list
- Pisah Fonnte device dari owner nomor (gotcha self-send block)

### PRIORITAS 3 — Xendit Live Activation
- Daftar Xendit sub-account untuk live merchant
- Set `xendit_business_id` di outlets table
- E2E test QRIS production

### PRIORITAS 4 — Multi-Outlet (Business Tier)
- Design + migration + tier gating
- Belum mulai, paling besar untuk monetisation Business tier

### PRIORITAS 5 — Vultr Credit Reminder
- $300 credit expire 2026-05-11
- Decision: hangus (per `project_vultr_credit.md`)
- Reminder 10 Mei cek dashboard

### Cara reconnect:
> "baca CLAUDE.md, MEMORY.md, SESSION.md di /var/www/kasira/ lalu lanjut dari NEXT ACTION"
