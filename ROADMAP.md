# KASIRA — Roadmap & Build Order
# Source of truth untuk fitur, tier, dan status build.
# Updated: 2026-04-13

---

## Status Sekarang
- [x] FASE 0: Fondasi ✅
- [x] FASE 1: Auth ✅
- [x] FASE 2: Core POS Starter ✅
- [x] FASE 3: Flutter Kasir App ✅
- [x] FASE 4: Owner Dashboard Next.js ✅
- [x] FASE 5: Pilot ✅
- [x] FASE 6: Pro Features ✅ (built, tier gate audit in progress)
- [x] FASE 7: Infrastruktur Lanjutan ✅ (RLS, billing, referral, platform intelligence)
- [ ] FASE 8: Polish & Publish ← SEKARANG DI SINI

---

## Tier Definition (SOURCE OF TRUTH)

Semua fitur Starter **ada di Pro**. Semua fitur Pro **ada di Business**.

### Starter (Gratis / Default)
- POS: order, payment (cash + QRIS Xendit)
- Products + categories CRUD
- Simple stock (deduct otomatis, restock manual)
- Shifts (buka/tutup + rekap kas)
- Basic reporting (revenue harian, summary)
- Storefront basic (menu browsing, order online, booking)
- Customer management
- Download APK + auto-update
- Landing page + SEO

### Pro (Berbayar — via Xendit subscription)
Semua Starter + :
- Reservasi + booking management
- Tab / Split Bill (equal, per-item, custom, full)
- Recipe / Ingredient / HPP analysis
- Recipe mode stock (ingredient-level tracking)
- AI Chat owner (Claude API — Haiku untuk Starter context, Sonnet untuk Pro)
- Knowledge Graph (product-ingredient relationships)
- Loyalty points (earn/redeem per order)
- Dapur app (Kitchen Display System)
- HPP report + margin analysis
- Best seller analytics

### Business (Enterprise — masa depan)
Semua Pro + :
- Multi-outlet management
- Cross-outlet reporting
- Platform benchmarks (bandingkan vs industri)

---

## FASE 0 — Fondasi ✅

### Database: 72 Alembic Migrations

#### Batch 1 — Root Tables (001-005)
```
01. tenants          — multi-tenant foundation + subscription tier
02. brands           → tenants (warung/cafe/resto/other)
03. outlets          → brands, tenants (slug, stock_mode, Xendit keys)
04. roles            → tenants (permission flags, HPP visibility)
05. users            → tenants, roles (phone login, PIN hash)
```

#### Batch 2 — User & Device (006-010)
```
06. sessions         → users, outlets (token, device binding)
07. devices          → users, outlets (kasir/dapur/owner, FCM token)
08. suppliers        → tenants
09. customers        → tenants (phone HMAC, WhatsApp consent)
10. outlet_tax_config → outlets (PB1, PPN, service charge)
```

#### Batch 3 — Products & Ingredients (011-022)
```
11. tables           → outlets (capacity, floor section, position)
12. products         → brands (stock_qty, CHECK >= 0, pgvector embedding)
13. product_variants → products (price adjustment)
14. modifiers        → brands (add-ons, min/max select)
15. outlet_product_overrides → outlets, products
16. ingredients      → brands (tracking_mode, unit_type, buy_price)
17. ingredient_units → ingredients (conversion factors)
18. ingredient_suppliers → ingredients, suppliers (price trend)
19. outlet_stock     → outlets, ingredients (CRDT JSONB + CHECK >= 0)
20. recipes          → products (version, AI-assisted flag)
21. recipe_ingredients → recipes, ingredients (qty, optional flag)
```

#### Batch 4 — Orders & Transactions (023-031)
```
22. pricing_rules    → tenants, brands, outlets (discount/happy_hour)
23. shifts           → outlets, users (cash reconciliation)
24. orders           → outlets, users, customers, tables, tabs (display_number SEQUENCE)
25. order_items      → orders, products, variants (modifiers JSONB)
26. payments         → orders, outlets (Xendit QRIS, xendit_raw JSONB)
27. reservations     → outlets, tables, customers (date/time split, deposit)
28. purchase_orders  → outlets, suppliers (draft→received workflow)
29. purchase_order_items → POs, ingredients
30. customer_points  → customers, outlets (balance CHECK >= 0)
31. point_transactions → customers, orders (UNIQUE order_id+type)
```

#### Batch 5 — Supporting & Analytics (032-037)
```
32. notifications    → tenants, outlets (info/warning/alert/system)
33. knowledge_graph_edges → tenants, brands (weighted relationships)
34. stock_events     → outlets, ingredients (immutable audit trail)
35. stock_snapshots  → outlets, ingredients (daily valuation)
36. audit_log        → users, outlets (append-only, before/after JSONB)
37. events           → partitioned by outlet_id (event sourcing, 4 partitions)
```

#### Batch 6 — Connect / Storefront (038-042)
```
38. connect_outlets  → outlets (WhatsApp/GoFood/Grab/Shopee/TikTok/IG)
39. connect_orders   → orders, outlets (idempotency_key UNIQUE)
40. connect_customer_profiles → customers (external ID mapping)
41. connect_chats    → connect_orders (AES-256 encrypted messages)
42. connect_behavior_log → connect_orders (append-only customer actions)
```

#### Batch 7 — Billing & Payments Extended (043-051)
```
43. outlet_location_detail → outlets (precision coordinates)
44. supplier_price_history → suppliers (immutable price changes)
45. products update   — sold_today, sold_total, SKU, barcode
46. subscriptions    → tenants (billing interval, trial/past_due)
47. invoices         → tenants, subscriptions (draft→paid workflow)
48. subscription_payments → invoices (multi-method)
49. payments update  — order_id nullable, invoice_id FK, is_partial
50. partial_payments → payments, orders (Pro+)
51. payment_refunds  → payments, orders (approval chain)
```

#### Batch 8 — Optimistic Locking & Infrastructure (052-061)
```
52. row_version batch 1 — categories, product_variants, customers, shifts, order_items
53. cash_activities  → shifts (income/expense audit)
54. shift_session_id → payments (cash drawer tracking)
55. row_version batch 2 — roles, sessions, devices, suppliers, modifiers, ingredients, recipes, dll
56-57. Midtrans → Xendit migration (drop Midtrans, add Xendit columns)
58. payments rename  — midtrans_raw → xendit_raw
59. loyalty redesign — Integer balance, outlet_id added
60. outlet cover_image_url
61. outlet xendit_api_key (per-outlet Xendit)
```

#### Batch 9 — Pro Features (062-068)
```
62. tabs + tab_splits — split bill (full/equal/per_item/custom)
63. unique_open_shift — 1 open shift per user per outlet
64. reservation upgrade — date/time split, deposit, settings table
65. outlet stock_mode — simple/recipe ENUM
66. ingredient buy_price + buy_qty
67. tax_config columns — tax_pct, service_charge_enabled
68. subscription_invoices — tenant billing cycle (billing_day, next_billing_date)
```

#### Batch 10 — Security & Intelligence (069-072)
```
69. RLS policies + 18 composite indexes — tenant isolation on 40+ tables
70. referral system — referral_code on tenants, referrals table
71. referral_commissions — commission per invoice (20% default)
72. platform benchmarks — daily_stats, hpp_benchmarks, ingredient_prices, insights cache
```

### Infrastruktur ✅
- [x] Event store (append-only, partitioned by outlet_id)
- [x] Audit log middleware semua WRITE endpoint
- [x] Rate limiting: OTP 3x resend/15min, verify 5x/15min
- [x] Response format wrapper: `{success, data, meta, request_id}`
- [x] RLS (Row-Level Security) tenant isolation
- [x] CRDT sync engine (HLC + PNCounter)
- [ ] Field encryption AES-256-GCM helper (partial — customer phone HMAC ada)
- [ ] mask_phone() helper di semua response

---

## FASE 1 — Auth ✅

### Endpoints
```
✓ POST /auth/register        — buat tenant baru (auto Starter tier)
✓ POST /auth/otp/send        — kirim OTP ke WA (Fonnte)
✓ POST /auth/otp/verify      — verify + return JWT + stock_mode
✓ POST /auth/pin/set         — kasir set PIN
✓ POST /auth/pin/verify      — login offline pakai PIN (Pro: dapur app)
✓ POST /auth/logout           — revoke token
✓ GET  /auth/me              — profile + subscription_tier + stock_mode
✓ GET  /auth/app/version     — Flutter update checker
✗ POST /auth/refresh         — BELUM (JWT expire panjang, low priority)
```

### Middleware
- JWT verify via HTTPBearer + `get_current_user()`
- Tenant via X-Tenant-ID header + `TenantMiddleware`
- Subscription status check (suspended → block access)
- Superadmin bypass

---

## FASE 2 — Core POS Starter ✅

### Fitur Built
- Products + categories CRUD
- Orders + order_items (dine_in/takeaway/delivery)
- Payment: cash + QRIS (Xendit webhook)
- Simple stock: auto-deduct on order, restore on cancel
- Shifts: buka/tutup, cash reconciliation
- Basic reporting: revenue harian, daily summary
- Tax & service charge: PB1, PPN, configurable per outlet

### Belum
- ✗ Struk WA via Fonnte

---

## FASE 3 — Flutter Kasir App ✅

### 15+ Layar
1. Splash + update checker (force update support)
2. Login OTP WA
3. PIN login (offline)
4. Dashboard (revenue, quick actions)
5. POS screen (menu grid + cart panel)
6. Payment screen (cash/QRIS)
7. Payment success + receipt
8. Receipt preview (Bluetooth printer)
9. Order list (riwayat transaksi)
10. Shift buka/tutup + rekap
11. Product management
12. Settings (server, sync, printer)
13. Reservasi list + table grid
14. Tab list + detail + split bill
15. Low stock alert

### Sync Engine
- CRDT: HLC + PNCounter (conflict-free stock)
- Offline-first: order masuk tanpa internet
- Drift v4: ingredients, recipes, outlet_stock tables
- Bidirectional: push orders/products, pull everything

---

## FASE 4 — Owner Dashboard (Next.js 14) ✅

### Halaman
1. Dashboard overview (revenue, order count, best seller)
2. Menu management (CRUD + recipe linking)
3. Kasir management (CRUD + role assignment)
4. Laporan revenue (cash/QRIS breakdown)
5. Settings: outlet info, payment (Xendit), billing, stock mode
6. Download APK page
7. Landing page + SEO
8. Pro upgrade page (feature showcase)

### Pro-Only Pages (gated dengan `useProGuard`)
- Bahan Baku (ingredient management)
- HPP report (cost analysis)
- AI Asisten (business insights)
- Reservasi + meja + settings

---

## FASE 5 — Pilot ✅

- [x] pg_dump backup tiap 6 jam ke R2
- [x] APK hosted di GitHub Releases + auto-update
- [x] Landing page live
- [x] Error monitoring (Sentry)
- [x] GitHub Actions: APK build workflow
- [ ] UptimeRobot monitoring
- [ ] kasira-setup.sh tested di VPS bersih
- [ ] Training kasir

---

## FASE 6 — Pro Features ✅

### Status per Feature

| Feature | Backend | Dashboard | Flutter | Tier Gate |
|---------|---------|-----------|---------|-----------|
| Reservasi + booking | ✅ routes + model | ✅ 3 pages | ✅ list + grid | ✅ backend+dashboard, ⚠️ Flutter belum gate |
| Tab / Split Bill | ✅ routes + model | N/A (Flutter only) | ✅ list + detail + modals | ✅ backend, ⚠️ Flutter belum gate |
| Recipe/Ingredient/HPP | ✅ routes + model | ✅ bahan-baku + HPP page | ✅ sync + display | ✅ backend+dashboard, ⚠️ Flutter pakai stock_mode proxy |
| AI Chat owner | ✅ routes (Claude API) | ✅ AI page | ❌ belum | ✅ backend+dashboard |
| Knowledge Graph | ✅ routes + model | N/A | N/A | ✅ backend |
| Loyalty points | ✅ routes + model | N/A | ❌ belum | ✅ backend |
| Dapur app (KDS) | ✅ PIN verify gated | N/A | ✅ pages built | ✅ backend (PIN verify Pro-only) |
| Multi-outlet | ⚠️ model ready, logic partial | ❌ | ❌ | ❌ belum gate (Business tier) |
| Invoice scan | ❌ | ❌ | ❌ | — |
| Struk WA (Fonnte) | ❌ | — | — | — |

---

## FASE 7 — Infrastruktur Lanjutan ✅

Fitur yang sudah built tapi belum ada di ROADMAP sebelumnya:

### Subscription Billing (Xendit)
- Model: `subscription_invoices` + tenant billing fields
- API: `billing.py` — GET /current, GET /invoices, POST retry
- Tasks: `subscription_billing.py` — auto-generate invoice
- Tasks: `payment_reconciliation.py` — Xendit webhook → mark paid
- Flow: tenant baru = Starter → upgrade = manual konfirmasi Ivan (Rule #51)

### Referral System
- Model: `referrals` + `referral_commissions`
- API: `referrals.py` — code generate, apply, dashboard
- Commission: 20% default per invoice paid
- RLS: tenant-scoped

### Superadmin Dashboard
- API: `superadmin.py` — tenant list, suspend/activate, stats
- Suspend flow: H-7 WA → H-3 WA → H+7 suspend → H+60 deletion (Rule #52)

### Platform Intelligence (Cross-Tenant)
- Model: `platform_daily_stats`, `platform_hpp_benchmarks`, `platform_ingredient_prices`, `platform_insights`
- Cron: aggregate daily stats per outlet
- Purpose: benchmark HPP/harga vs industri (Business tier — masa depan)

### Security
- RLS policies on 40+ tables (migration 069)
- 18 composite indexes for query optimization
- `kasira_app` DB role with limited permissions

### Tax & Service Charge
- Model: `outlet_tax_config` (PB1, PPN, service charge)
- Configurable per outlet
- Applied to order calculation (subtotal → tax → service → total)

---

## FASE 8 — Polish & Publish ← CURRENT

### Tier Gate Fixes (harus selesai sebelum publish)
- [x] Flutter: simpan `subscription_tier` dari login/sync response ✅ 2026-04-13
- [x] Flutter: gate Tab/Bon button di dashboard (Pro only) ✅ 2026-04-13
- [x] Flutter: gate Reservasi navigation (Pro only) ✅ 2026-04-13
- [x] OTP verify + sync response: tambah `subscription_tier` ✅ 2026-04-13
- [x] Backend: gate partial payments Pro-only (Rule #43) ✅ 2026-04-13
- [ ] Backend: gate multi-outlet logic (Business only) — low priority

### Model row_version Fixes (Golden Rule #29)
- [x] Recipe — fixed ✅ 2026-04-13
- [x] RecipeIngredient — fixed ✅ 2026-04-13
- [x] ReservationSettings — fixed ✅ 2026-04-13
- [x] PointTransaction — fixed ✅ 2026-04-13
- [x] Referral — fixed ✅ 2026-04-13
- [x] ReferralCommission — fixed ✅ 2026-04-13

### Belum Dibangun
- [ ] Struk WA via Fonnte (FASE 2 sisa)
- [ ] Invoice scan + OCR (FASE 6)
- [ ] POST /auth/refresh (low priority)
- [ ] UptimeRobot monitoring (FASE 5 sisa)
- [ ] mask_phone() di semua response
- [ ] Multi-outlet full implementation (Business tier)

### Smooth & User-Friendly Improvements
- [x] Flutter: upgrade bottom sheet saat Starter akses fitur Pro ✅ 2026-04-13
- [x] Flutter: Reservasi nav visible tapi locked + lock icon ✅ 2026-04-13
- [x] Dashboard: Pro page tampil context banner "X memerlukan paket Pro" ✅ 2026-04-13
- [x] Dashboard: useProGuard pass feature name ke redirect ✅ 2026-04-13
- [x] Stock mode: confirmation dialog + next steps guidance ✅ 2026-04-13
- [x] Sync: SnackBar notify kasir saat stock_mode berubah via sync ✅ 2026-04-13

---

## Golden Rules Summary

### Data Layer
- UUID untuk semua PK — TIDAK BOLEH integer
- Soft delete via `deleted_at` — TIDAK hard delete
- Event store append-only — TIDAK update/delete event
- `row_version` di semua tabel kritikal
- `CHECK (stock_qty >= 0)` dan `CHECK (computed_stock >= 0)` di DB level

### API Layer
- Setiap WRITE endpoint WAJIB audit log
- Response: `{success, data, meta, request_id}`
- Idempotency key wajib untuk payment + storefront order
- Timezone: simpan UTC, tampilkan Asia/Jakarta

### Auth
- OTP WA only — tidak ada email+password
- JWT: httpOnly cookie (web), SecureStorage (mobile)
- OTP expire 5 menit, max 3x resend per 15 menit

### Stock
- Deduct otomatis dari transaksi
- Stok = 0 → `is_available: false`, TETAP MUNCUL
- `order_display_number` dari PostgreSQL SEQUENCE

### Payment
- Payment endpoint WAJIB `SELECT FOR UPDATE`
- `xendit_raw` (JSONB) WAJIB disimpan
- `partial_payments` = Pro+ only

### Deploy
- Backend: `docker cp` + `docker restart` (BUKAN `docker compose up -d`)
- Frontend: `docker compose build frontend && docker compose up -d frontend`
- Flutter: git push → GitHub Actions → APK release

---

## Build Priority Rules
1. FASE 0 WAJIB selesai sebelum FASE 1
2. FASE 1 (Auth) WAJIB selesai sebelum fitur apapun
3. Backend endpoint WAJIB ada sebelum Flutter consume
4. Migration WAJIB test upgrade + downgrade sebelum lanjut
5. ROADMAP.md = source of truth untuk fitur dan tier
6. Jangan skip step — setiap step ada dependency
