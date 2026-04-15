# KASIRA — Roadmap & Build Order
# Source of truth untuk fitur, tier, dan status build.
# Updated: 2026-04-15

---

## Status Sekarang
- [x] FASE 0: Fondasi ✅
- [x] FASE 1: Auth ✅
- [x] FASE 2: Core POS Starter ✅
- [x] FASE 3: Flutter Kasir App ✅
- [x] FASE 4: Owner Dashboard Next.js ✅
- [x] FASE 5: Pilot ✅
- [x] FASE 6: Pro Features ✅
- [x] FASE 7: Infrastruktur Lanjutan ✅
- [x] FASE 8: Polish & Publish ✅ (hampir semua selesai)
- [ ] FASE 9: Scale & Intelligence ← SEKARANG DI SINI

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
- Struk WA via Fonnte

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
- Menu Engineering (BCG Matrix: Star/Plowhorse/Puzzle/Dog)
- Combo Detection (co-occurrence analysis)
- Semantic Product Search (Voyage AI embeddings)
- Dark mode (Pro theme)

### Business (Enterprise — masa depan)
Semua Pro + :
- Multi-outlet management
- Cross-outlet reporting
- Platform benchmarks (bandingkan vs industri)
- Cross-tenant product similarity search

---

## FASE 0 — Fondasi ✅

### Database: 74 Alembic Migrations

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

#### Batch 10 — Security & Intelligence (069-074)
```
69. RLS policies + 18 composite indexes — tenant isolation on 40+ tables
70. referral system — referral_code on tenants, referrals table
71. referral_commissions — commission per invoice (20% default)
72. platform benchmarks — daily_stats, hpp_benchmarks, ingredient_prices, insights cache
73. embedding layer4 — products.embedding vector(512) + HNSW index
74. platform_geo_columns — city, district, province, hourly_distribution
```

### Infrastruktur ✅
- [x] Event store (append-only, partitioned by outlet_id)
- [x] Audit log middleware semua WRITE endpoint
- [x] Rate limiting: OTP 3x resend/15min, verify 5x/15min
- [x] Response format wrapper: `{success, data, meta, request_id}`
- [x] RLS (Row-Level Security) tenant isolation
- [x] CRDT sync engine (HLC + PNCounter)
- [x] mask_phone() di semua API response ✅ 2026-04-15
- [ ] Field encryption AES-256-GCM helper (partial — customer phone HMAC ada)

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
- Struk WA via Fonnte ✅ 2026-04-14

---

## FASE 3 — Flutter Kasir App ✅

### 15+ Layar
1. Splash + update checker (force update support)
2. Login OTP WA (+ success screen, PIN setup UX)
3. PIN login (offline)
4. Dashboard (revenue, quick actions)
5. POS screen (menu grid + cart panel + tax/service breakdown)
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

### Dark Mode Pro Theme ✅ 2026-04-13
- Background: #0B0E14, Surface: #141820
- Primary: Emerald Green #00D68F
- Accent: Cool Blue #3B82F6

---

## FASE 4 — Owner Dashboard (Next.js 14) ✅

### Halaman
1. Dashboard overview (revenue, order count, best seller)
2. Menu management (CRUD + recipe linking)
3. Kasir management (CRUD + role assignment)
4. Laporan revenue (cash/QRIS breakdown)
5. Settings: outlet info, payment (Xendit), billing, stock mode
6. Download APK page
7. Landing page + SEO + GA4
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
- [x] GitHub Actions: APK build workflow (workflow_dispatch)
- [ ] UptimeRobot monitoring
- [ ] kasira-setup.sh tested di VPS bersih

---

## FASE 6 — Pro Features ✅

### Status per Feature

| Feature | Backend | Dashboard | Flutter | Tier Gate |
|---------|---------|-----------|---------|-----------|
| Reservasi + booking | ✅ | ✅ | ✅ | ✅ all layers |
| Tab / Split Bill | ✅ | N/A | ✅ | ✅ all layers |
| Recipe/Ingredient/HPP | ✅ | ✅ | ✅ sync+display | ✅ all layers |
| AI Chat owner | ✅ Claude API | ✅ | ✅ SSE streaming | ✅ all layers |
| Knowledge Graph | ✅ | N/A | N/A | ✅ |
| Loyalty points | ✅ | N/A | ❌ | ✅ |
| Dapur app (KDS) | ✅ | N/A | ✅ | ✅ |
| Menu Engineering | ✅ BCG Matrix | N/A | N/A | ✅ |
| Combo Detection | ✅ co-occurrence | N/A | N/A | ✅ |
| Struk WA Fonnte | ✅ | ✅ | N/A | All tiers |
| Multi-outlet | ⚠️ partial | ❌ | ❌ | ❌ (Business) |
| Invoice scan OCR | ✅ Claude Vision | ❌ | ❌ | All tiers |

---

## FASE 7 — Infrastruktur Lanjutan ✅

### Subscription Billing (Xendit)
- Model: `subscription_invoices` + tenant billing fields
- API: `billing.py` — GET /current, GET /invoices, POST retry
- Tasks: `subscription_billing.py` — auto-generate invoice
- Tasks: `payment_reconciliation.py` — Xendit webhook → mark paid

### Referral System
- Model: `referrals` + `referral_commissions`
- API: `referrals.py` — code generate, apply, dashboard
- Commission: 20% default per invoice paid

### Superadmin Dashboard
- API: `superadmin.py` — tenant list, suspend/activate, stats, broadcast
- Suspend flow: H-7 WA → H-3 WA → H+7 suspend → H+60 deletion

### Tax & Service Charge
- Model: `outlet_tax_config` (PB1, PPN, service charge)
- Configurable per outlet
- Client-side calculation di Flutter cart ✅ 2026-04-15
- Backend recalculates on order create (server authoritative)

### Security
- RLS policies on 40+ tables (migration 069)
- 18 composite indexes for query optimization
- `kasira_app` DB role with limited permissions
- mask_phone() on all API responses ✅ 2026-04-15

---

## FASE 8 — Polish & Publish ✅

### Tier Gate Fixes ✅
- [x] Flutter: simpan `subscription_tier` dari login/sync response
- [x] Flutter: gate Tab/Bon button di dashboard (Pro only)
- [x] Flutter: gate Reservasi navigation (Pro only)
- [x] OTP verify + sync response: tambah `subscription_tier`
- [x] Backend: gate partial payments Pro-only
- [ ] Backend: gate multi-outlet logic (Business only) — low priority

### Model row_version Fixes ✅
- [x] Recipe, RecipeIngredient, ReservationSettings
- [x] PointTransaction, Referral, ReferralCommission

### Smooth & User-Friendly ✅
- [x] Upgrade bottom sheet saat Starter akses fitur Pro
- [x] Reservasi nav visible tapi locked + lock icon
- [x] Dashboard: Pro page context banner
- [x] Stock mode: confirmation dialog + next steps guidance
- [x] Sync: SnackBar notify kasir saat stock_mode berubah
- [x] Login flow fix: success screen + PIN setup UX ✅ 2026-04-15
- [x] Dark mode Pro theme ✅ 2026-04-13

### APK Releases
- v2.0.0 — dark mode, tier gate, Pro upgrade flow (2026-04-13)
- v2.2.0 — login fix, success screen (2026-04-15)
- v2.3.0 — cart tax/service breakdown (2026-04-15)

---

## FASE 9 — Scale & Intelligence ← CURRENT

### Platform Intelligence (Silent Learning) ✅ 2026-04-14
Empat piece all done, berjalan otomatis:

1. **Location Tracking** — Nominatim reverse geocode on outlet location submit
2. **Product Embeddings** — Voyage AI (voyage-3-lite, 512 dims), auto-embed on product CRUD
3. **Transaction Aggregation** — Cron: daily stats (6h), HPP benchmark (weekly), ingredient prices (12h), insights (24h)
4. **Geo Intelligence** — Platform models: daily_stats, hpp_benchmarks, ingredient_prices, insights (all with geo columns)

### Cross-Tenant Intelligence ✅ 2026-04-15
- 14/14 products embedded across 4 tenants
- `POST /embeddings/generate-all` — bulk embed all tenants (platform admin)
- `GET /embeddings/similar/{id}?cross_tenant=true` — RLS bypass, find similar across merchants
- Similarity: Kopi Hitam → Kopi Ku (Dita Coffee) 80.7%

### Menu Engineering ✅ 2026-04-15
- BCG Matrix classification (Star/Plowhorse/Puzzle/Dog)
- Combo detection (co-occurrence analysis)
- Auto-injected into AI context

### AI RAG Context ✅ 2026-04-15
- Knowledge Graph context
- HPP benchmarks
- Menu engineering + combo data
- Cross-tenant benchmarks
- Semantic search (product embedding)
- **BLOCKER: Anthropic API credit habis — perlu top up**

### Belum Dibangun
- [x] Invoice scan + OCR (Claude Vision) ✅ 2026-04-15
- [ ] UptimeRobot monitoring
- [ ] Multi-outlet full implementation (Business tier)
- [ ] POST /auth/refresh (low priority)
- [ ] Flutter: loyalty points UI
- [x] Flutter: AI chat (SSE streaming, Pro gate) ✅ 2026-04-15
- [x] Hourly distribution API + aggregation ✅ 2026-04-15
- [x] Anthropic API key + budget controls ✅ 2026-04-15 ($7.16 balance)

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
- Phone numbers WAJIB masked di response (mask_phone())

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
- Flutter: git push → GitHub Actions → APK release (workflow_dispatch)

---

## Build Priority Rules
1. FASE 0 WAJIB selesai sebelum FASE 1
2. FASE 1 (Auth) WAJIB selesai sebelum fitur apapun
3. Backend endpoint WAJIB ada sebelum Flutter consume
4. Migration WAJIB test upgrade + downgrade sebelum lanjut
5. ROADMAP.md = source of truth untuk fitur dan tier
6. Jangan skip step — setiap step ada dependency

---

## System State (2026-04-15)
- **Migration:** 074
- **APK:** v2.3.0
- **Containers:** 4 (backend, frontend, db, redis) — all healthy
- **Tenants:** 4 (Kasira Coffee pro, Dita Coffee starter, B coffee starter, Warung Demo)
- **Embeddings:** 14/14 products across 4 tenants
- **Anthropic API:** credit habis — needs top up
- **Voyage AI:** working
