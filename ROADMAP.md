# KASIRA — Roadmap & Build Order
# Source of truth untuk fitur, tier, dan status build.
# Updated: 2026-04-25

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
- [x] FASE 8: Polish & Publish ✅
- [x] FASE 9: Scale & Intelligence ✅
- [x] FASE 10: Pre-Launch Hardening ✅ (2026-04-19 → 2026-04-25)
- [ ] FASE 11: Public Launch + Scale Operations ← SEKARANG DI SINI

**Decision 2026-04-22:** Publish 25 tenant aman (90% confidence). 30 conservative ceiling. Vultr upgrade saat threshold trigger 2 dari 3 indicator kuning sustained 7 hari (memory `:project_vps_capacity`).

---

## Tier Definition (SOURCE OF TRUTH)

Semua fitur Starter **ada di Pro**. Semua fitur Pro **ada di Business**.

### Starter (Gratis / Default)
- POS: order, payment (cash + QRIS Xendit)
- Products + categories CRUD
- Simple stock (deduct otomatis, restock manual)
- **Buy price + margin tracking** (Migration 084, sejak 2026-04-24) — `products.buy_price` snapshot terakhir restock
- **Margin Report** `GET /reports/margin` — summary avg margin %, missing buy_price flag, negative margin alert
- Shifts (buka/tutup + rekap kas)
- Refunds (full + partial)
- Basic reporting (revenue harian, summary, top products)
- Storefront basic (menu browsing, order online, booking)
- Customer management
- Adaptive UI label (label "Meja/Dapur" auto-swap ke "Rak/Gudang/Teknisi" untuk non-F&B per domain detection 10 bucket)
- Download APK + auto-update
- Landing page + SEO
- Struk WA via Fonnte

### Pro (Berbayar — **Rp 299.000/bulan** via Xendit subscription, decision 2026-04-18)
Semua Starter + :
- Reservasi + booking management
- Tab / Split Bill (equal, per-item, custom, full)
- Recipe / Ingredient / HPP analysis (recipe mode stock, ingredient-level tracking)
- **AI Chat owner** dengan multi-turn conversation (Redis-only session store, 5 turn pair, TTL 1800s)
- **AI Pricing Coach** (Sonnet 4.5, quota 5x/hari/tenant via redis `ai_sonnet:{tenant}:{date}`)
- **AI Setup Resep** (Haiku, intent SETUP_RECIPE/MENU_BULK/RESTOCK)
- **AI Domain-Aware** (10 UMKM bucket: kopi_cafe, resto_makanan, warteg, bakery, vape_liquid, laundry, salon_barber, minimarket, pet_shop, apotik_herbal)
- Knowledge Graph (product-ingredient relationships)
- **KG Price Events** — auto WA alert ke owner kalau ingredient price update bikin margin produk drop ≥5pp atau <20%
- Loyalty points (earn/redeem per order)
- Dapur app (Kitchen Display System) — Pro-only Flutter Android
- HPP report + margin analysis
- Best seller analytics
- Menu Engineering (BCG Matrix: Star/Plowhorse/Puzzle/Dog)
- Combo Detection (co-occurrence analysis)
- Semantic Product Search (Voyage AI embeddings)
- Inventory Powerhouse Flutter UI (tabbed Produk & Stok, low-stock badge, embedded restock)
- Dark mode (Pro theme)

### Business (Enterprise — masa depan, decision deferred)
Semua Pro + :
- Multi-outlet management (limit 20 outlet)
- Cross-outlet reporting
- Platform benchmarks (bandingkan vs industri)
- Cross-tenant product similarity search

### Tier Outlet Limits
- Starter: 1 outlet
- Pro: 5 outlets
- Business: 20 outlets
- Enterprise: ∞

Source: `backend/services/subscription.py` `TIER_OUTLET_LIMITS`. Cascade downgrade reset `outlet.stock_mode` ke simple kalau tier turun ke starter.

---

## FASE 0 — Fondasi ✅

### Database: 84 Alembic Migrations (head: 084)

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

#### Batch 3 — Products & Ingredients (011-021)
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

#### Batch 4 — Orders & Transactions (022-031)
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
32. notifications    → tenants, outlets
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
54. shift_session_id → payments
55. row_version batch 2 — roles, sessions, devices, suppliers, modifiers, dll
56-57. Midtrans → Xendit migration
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
68. subscription_invoices — tenant billing cycle
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

#### Batch 11 — Dine-In Tab System (075-077)
```
75. reservation_settings — auto_confirm, slot_duration
76. storefront_dine_in — connect order dine_in_tab_mode
77. payment_tab_id — payments.tab_id FK → tabs for proper tab-payment linking
```

#### Batch 12 — Production Hardening (078-080) ✅ 2026-04-19
```
78. production_hardening — misc constraint + index tuning untuk pre-launch
79. tax_config_number_and_footer — outlet NPWP + custom struk footer
80. encrypt_xendit_keys — AES-256-GCM at-rest via EncryptedString TypeDecorator
                         (`backend/utils/encryption.py`, versioned `v1:` prefix,
                          fail-loud kalau ENCRYPTION_KEY unset)
```

#### Batch 13 — Sync Reliability + Stock Mode (081-084) ✅ 2026-04-19 → 2026-04-24
```
81. sync_idempotency — table sync_idempotency_keys (composite PK tenant_id+key,
                       RLS isolation, atomic INSERT ON CONFLICT DO NOTHING RETURNING)
82. sync_pagination_indexes — 8 composite indexes untuk cursor pagination
                              (orders, order_items, cash_activities, ingredients,
                               shifts, categories, outlet_stock, recipes/recipe_ingredients)
83. xendit_reliability — table xendit_webhook_events (callback_id UNIQUE + RLS)
                        untuk webhook dedup atomic
84. product_buy_price — products.buy_price NUMERIC(12,2) NULL
                       (Starter margin tracking — additive, backward compat 100%)
```

### Infrastruktur ✅
- [x] Event store (append-only, partitioned by outlet_id)
- [x] Audit log middleware semua WRITE endpoint
- [x] Rate limiting: OTP 3x resend/15min, verify 5x/15min
- [x] Response format wrapper: `{success, data, meta, request_id}`
- [x] RLS (Row-Level Security) tenant isolation
- [x] CRDT sync engine (HLC + PNCounter)
- [x] mask_phone() di semua API response
- [x] Field encryption AES-256-GCM (`EncryptedString` TypeDecorator) ✅ 2026-04-19
- [x] Sync cursor pagination + idempotency dedup ✅ 2026-04-19
- [x] Disaster Recovery script + runbook (RTO 60min, RPO 6h) ✅ 2026-04-19
- [x] Observability stack (Prometheus `/metrics`, JSON logging, PII redactor) ✅ 2026-04-19
- [x] Async task supervisor (auto-restart + exponential backoff + `/health/background`) ✅ 2026-04-19

---

## FASE 1 — Auth ✅

### Endpoints
```
✓ POST /auth/register        — buat tenant baru (auto Starter tier)
✓ POST /auth/otp/send        — kirim OTP ke WA (Fonnte)
✓ POST /auth/otp/verify      — verify + return JWT + stock_mode + subscription_tier
✓ POST /auth/pin/set         — kasir set PIN
✓ POST /auth/pin/verify      — login offline pakai PIN (Pro: dapur app)
✓ POST /auth/logout          — revoke token
✓ GET  /auth/me              — profile + subscription_tier + stock_mode
✓ GET  /auth/app/version     — Flutter update checker
✓ POST /ai/classify-domain   — public, no-auth, untuk register flow domain hint
✗ POST /auth/refresh         — BELUM (JWT expire panjang, low priority)
```

### Middleware
- JWT verify via HTTPBearer + `get_current_user()`
- Tenant via X-Tenant-ID header + `TenantMiddleware`
- Subscription status check (suspended → block access, 402 SUBSCRIPTION_INACTIVE vs 403 INSUFFICIENT_TIER)
- Superadmin bypass

### Fonnte Resilience ✅ 2026-04-19
- Singleton httpx.AsyncClient (pool 10 keepalive/20 total)
- `Timeout(4s read/2s connect)`, 3-attempt exponential backoff
- Circuit breaker (threshold 5 consec fails, 60s cooldown, auto half-open probe)
- Worst case 13.5s (from unlimited)

### OTP Self-Send Block
Catatan: nomor admin/owner WAJIB beda dari nomor Fonnte device sender. WhatsApp block self-send sebagai anti-spam. Kalau OTP gak masuk, cek nomor user vs nomor Fonnte device. Detail: memory `project_fonnte_otp_gotcha`.

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
- Struk WA via Fonnte
- **Buy price + margin tracking** (2026-04-24) — restock optional `unit_buy_price` snapshot ke `products.buy_price`, additive event payload
- **Margin Report** `GET /reports/margin` — outlet-scoped, simple-mode only (recipe → 400 STOCK_MODE_NOT_SUPPORTED, arahkan ke `/recipes/hpp-report`)

### Stock Deduction Code Path (6+ tempat WAJIB konsisten)
- `backend/api/routes/orders.py` — online order create + cancel restore
- `backend/services/stock_service.py` — simple mode
- `backend/services/ingredient_stock_service.py` — recipe mode
- `backend/api/routes/sync.py` — offline order sync
- `backend/api/routes/products.py:compute_recipe_stock()` — display
- `kasir_app/lib/features/pos/providers/cart_provider.dart` — Flutter offline
- `kasir_app/lib/features/products/providers/products_provider.dart` — Flutter display

---

## FASE 3 — Flutter Kasir App ✅

### 15+ Layar
1. Splash + update checker (force update support)
2. Login OTP WA + success screen + PIN setup
3. PIN login (offline)
4. Dashboard (revenue, quick actions)
5. POS screen (menu grid + cart panel + tax/service breakdown)
6. Payment screen (cash/QRIS) — QRIS polling 30s timeout + retry dialog
7. Payment success + receipt
8. Receipt preview (Bluetooth printer, async lock + 15s timeout)
9. Order list (riwayat transaksi)
10. Shift buka/tutup + rekap
11. **Produk & Stok** (tabbed: Produk + Stok dengan low-stock badge, embedded RestockPage) ✅ 2026-04-22
12. **Untung-Rugi (Margin Report)** tab di Product Management ✅ 2026-04-25
13. Settings (server, sync, printer)
14. Reservasi list + table grid
15. Tab list + detail + split bill (occupied table tap → fetch /tabs/by-table)
16. Low stock alert
17. AI Chat (SSE streaming, markdown render, multi-turn) — Pro-only

### Sync Engine
- CRDT: HLC + PNCounter (conflict-free stock)
- Offline-first: order masuk tanpa internet
- Drift v5: ingredients, recipes, outlet_stock, products.buy_price tables
- Bidirectional: push orders/products, pull everything
- Cursor-based pagination (handle offline 7 hari tanpa OOM)
- Persistent idempotency_key di prefs (reuse across retries, remove only on 200 OK)
- HLC.fromServer merge (handle multi-segment node_id `server:{outlet_uuid}`)

### Defense-in-Depth Hardening (Batch #14-#18)
- Rule #50 multi-outlet scope — query drift WAJIB scope ke `SessionCache.instance.outletId`
- Node ID isolation `sha256(device|user)` — shift switch user di device sama gak bypass PNCounter
- Atomic `batch.update` (bukan `batch.replace`) — prevent clobber mutasi lokal selama sync window
- Dio CancelToken — printer/sync request bisa di-cancel saat user logout

### Dark Mode Pro Theme ✅ 2026-04-13
- Background: #0B0E14, Surface: #141820
- Primary: Emerald Green #00D68F
- Accent: Cool Blue #3B82F6

### Adaptive UI Label (2026-04-21, Batch #26)
Label "Meja/Dapur/Area Servis" auto-swap based on `SessionCache.businessDomain` — F&B default, retail/service custom labels via `core/localization/business_labels.dart`.

---

## FASE 4 — Owner Dashboard (Next.js 14) ✅

### Halaman
1. Dashboard overview (revenue, order count, best seller)
2. Menu management (CRUD + recipe linking + buy_price field + margin preview)
3. Kasir management (CRUD + role assignment)
4. Laporan revenue (cash/QRIS breakdown)
5. **Laporan Margin** `/laporan/margin` — outlet selector + summary + table dengan margin badge color-coded ✅ 2026-04-25
6. Laporan HPP (Pro recipe mode) `/laporan/hpp`
7. Settings: outlet info, payment (Xendit), billing, stock mode
8. Download APK page
9. Landing page + SEO + GA4
10. Pro upgrade page (feature showcase)

### Pro-Only Pages (gated dengan `useProGuard`)
- Bahan Baku (ingredient management) — preset library 14 bahan + 3-category unit selector
- HPP report (cost analysis)
- AI Asisten (business insights)
- Reservasi + meja + settings

---

## FASE 5 — Pilot ✅

- [x] pg_dump backup tiap 6 jam ke R2 (14-day retention `s3://kasira-production/backups`)
- [x] APK hosted di GitHub Releases + auto-update
- [x] Landing page live
- [x] Error monitoring (Sentry)
- [x] GitHub Actions: APK build workflow (workflow_dispatch)
- [x] Disaster Recovery script (`scripts/restore_db.sh` + `docs/DISASTER_RECOVERY.md`)
- [x] **Telegram Healthcheck Alert** ✅ 2026-04-25 (cron `*/2 * * * *` + state-change throttle)
- [ ] UptimeRobot status page (public, ~15 menit, masih pending)
- [ ] kasira-setup.sh tested di VPS bersih

---

## FASE 6 — Pro Features ✅

### Status per Feature

| Feature | Backend | Dashboard | Flutter | Tier Gate |
|---------|---------|-----------|---------|-----------|
| Reservasi + booking | ✅ | ✅ | ✅ | ✅ all layers |
| Tab / Split Bill | ✅ | N/A | ✅ | ✅ all layers |
| Recipe/Ingredient/HPP | ✅ unit_utils.py | ✅ | ✅ sync+display | ✅ all layers |
| AI Chat owner | ✅ Claude API + multi-turn | ✅ | ✅ SSE streaming + markdown | ✅ all layers |
| AI Pricing Coach (Sonnet) | ✅ quota 5x/hari | ✅ | ✅ | ✅ Pro |
| AI Setup Resep | ✅ 4 intent | ✅ | ✅ | ✅ Pro |
| AI Domain-Aware (10 bucket) | ✅ detect_domain | ✅ guardrail injection | ✅ adaptive UI | ✅ all |
| KG Price Events | ✅ task | N/A | N/A | ✅ Pro (gated via task skip) |
| Knowledge Graph | ✅ | N/A | N/A | ✅ |
| Loyalty points | ✅ | N/A | ❌ Flutter UI | ✅ |
| Dapur app (KDS) | ✅ | N/A | ✅ | ✅ |
| Menu Engineering | ✅ BCG + unit_utils | N/A | N/A | ✅ |
| Combo Detection | ✅ co-occurrence | N/A | N/A | ✅ |
| Inventory Powerhouse Flutter | N/A | N/A | ✅ tabbed UI | ✅ Pro |
| Struk WA Fonnte | ✅ | ✅ | N/A | All tiers |
| Multi-outlet | ⚠️ partial | ❌ | ❌ | ❌ (Business) |
| Invoice scan OCR | ✅ Claude Vision | ❌ | ❌ | All tiers |

---

## FASE 7 — Infrastruktur Lanjutan ✅

### Subscription Billing (Xendit)
- Model: `subscription_invoices` + tenant billing fields
- API: `billing.py` — GET /current, GET /invoices, POST retry
- Tasks: `subscription_billing.py` — auto-generate invoice
- Tasks: `payment_reconciliation.py` — Xendit webhook → mark paid (RLS bypass `SET LOCAL app.current_tenant_id = ''`)

### Xendit Reliability ✅ 2026-04-19
- 5-attempt expo backoff (0.5s/1s/2s/4s)
- Webhook dedup atomic via `xendit_webhook_events` (Migration 083)
- Constant-time signature verify (`hmac.compare_digest`)
- Fail-safe state `pending_manual_check` (admin verify via Xendit dashboard)
- 3-tier error: permanent → failed, transient → pending_manual_check, unexpected → pending_manual_check

### Referral System
- Model: `referrals` + `referral_commissions`
- API: `referrals.py` — code generate, apply, dashboard
- Commission: 20% default per invoice paid

### Superadmin Dashboard
- API: `superadmin.py` — tenant list, suspend/activate, stats, broadcast
- Suspend flow: H-7 WA → H-3 WA → H+7 suspend → H+60 deletion
- **Waitlist monitoring** `GET /superadmin/waitlist` ✅ 2026-04-21 — domain breakdown + recent signups untuk early-access outreach

### Tax & Service Charge
- Model: `outlet_tax_config` (PB1, PPN, service charge, NPWP, custom_footer)
- Configurable per outlet
- Client-side calculation di Flutter cart
- Backend recalculates on order create (server authoritative)

### Security
- RLS policies on 40+ tables (Migration 069)
- 18 composite indexes for query optimization
- `kasira_app` DB role with limited permissions
- mask_phone() on all API responses
- AES-256-GCM at-rest encryption (Migration 080)

### Tier Lifecycle ✅ 2026-04-19
- `backend/services/subscription.py` single source of truth
- `TenantSnapshot` cache (Redis, TTL 30s)
- `is_subscription_active()` full check (subscription_status + is_active + expires_at)
- `apply_tier_downgrade_cascade()` reset outlet.stock_mode kalau ke starter + outlet count check
- 402 SUBSCRIPTION_INACTIVE vs 403 INSUFFICIENT_TIER (structured detail)

---

## FASE 8 — Polish & Publish ✅

### Tier Gate Fixes ✅
- [x] Flutter: simpan `subscription_tier` dari login/sync response
- [x] Flutter: gate Tab/Bon button di dashboard (Pro only)
- [x] Flutter: gate Reservasi navigation (Pro only)
- [x] OTP verify + sync response: tambah `subscription_tier`
- [x] Backend: gate partial payments Pro-only
- [ ] Backend: gate multi-outlet logic (Business only) — low priority

### Smooth & User-Friendly ✅
- [x] Upgrade bottom sheet saat Starter akses fitur Pro
- [x] Reservasi nav visible tapi locked + lock icon
- [x] Dashboard: Pro page context banner
- [x] Stock mode: confirmation dialog + next steps guidance
- [x] Sync: SnackBar notify kasir saat stock_mode berubah
- [x] Login flow fix: success screen + PIN setup UX
- [x] Dark mode Pro theme
- [x] **UX clarify "modal" vs "stok"** ✅ 2026-04-25 (banner + tile + form helper, definisi inline + contoh konkret)

### Adaptive UI for Non-F&B (Batch #26-#28) ✅ 2026-04-21
- [x] Domain classifier `POST /ai/classify-domain` (public, 3 super-group: fnb/retail/service)
- [x] Flutter `core/localization/business_labels.dart` — adaptive label per domain
- [x] AI guardrail injection (skip recipe/menu F&B kalau detect non-F&B bucket)
- [x] Waitlist signup `POST /waitlist/join` (Event-based, no schema change)
- [x] Adaptive upgrade sheet (non-F&B Pro feature → waitlist prompt, bukan paywall)
- [x] Superadmin waitlist monitoring

### APK Releases (terbaru)
- v1.0.30-v1.0.32 — Flutter Batch #14-#18 (multi-outlet scope, printer lock, node ID isolation, atomic batch.update)
- v1.0.34 — multi-turn AI + HLC.fromServer + persistent idempotency_key
- v1.0.36 — Adaptive UI Batch #27
- v1.0.37 — POS stock visual guard (HABIS/NONAKTIF badge)
- v1.0.38 — Inventory Powerhouse (tabbed Produk & Stok + low-stock badge)
- v1.0.39 — Starter Margin Tracking Fase 3 (RestockSheet + MarginReportPage)
- v1.0.42 — Pre-launch hardening (QRIS retry + table release guard)
- v1.0.43-v1.0.44 — Split-bill flow + dashboard nav

---

## FASE 9 — Scale & Intelligence ✅

### Platform Intelligence (Silent Learning) ✅ 2026-04-14
1. **Location Tracking** — Nominatim reverse geocode on outlet location submit
2. **Product Embeddings** — Voyage AI (voyage-3-lite, 512 dims), auto-embed on product CRUD
3. **Transaction Aggregation** — Cron: daily stats (6h), HPP benchmark (weekly), ingredient prices (12h), insights (24h)
4. **Geo Intelligence** — Platform models: daily_stats, hpp_benchmarks, ingredient_prices, insights (all with geo columns)

### Cross-Tenant Intelligence ✅ 2026-04-15
- All products embedded across tenants
- `POST /embeddings/generate-all` — bulk embed all tenants (platform admin)
- `GET /embeddings/similar/{id}?cross_tenant=true` — RLS bypass

### Menu Engineering ✅ 2026-04-15
- BCG Matrix classification (Star/Plowhorse/Puzzle/Dog)
- Combo detection (co-occurrence analysis)
- Auto-injected into AI context
- HPP unification via `unit_utils.py` (single source of truth, kg↔gram cross-family flag)

### AI RAG Context ✅ 2026-04-15
- Knowledge Graph context
- HPP benchmarks
- Menu engineering + combo data
- Cross-tenant benchmarks
- Semantic search (product embedding)

### AI Multi-Turn Chat ✅ 2026-04-21 (Batch #22)
- Redis-only storage `ai:conversation:{tenant_id}:{conv_id}`, TTL 1800s rolling, LTRIM cap 10 entries
- Tenant-scoped key (cegah cross-tenant leak)
- Fail-open Redis down → fresh turn
- Injection di `messages[]` (preserve Anthropic prompt cache)
- Action intents (RESTOCK/SETUP_RECIPE/MENU_BULK) short-circuit, no history persist

### KG Price Events ✅ 2026-04-22 (Batch #29)
- `backend/tasks/kg_price_event_loop.py` tails `ingredient.price_updated` events
- Compute margin drift per affected product via KG `used_by`/`contains` edges
- WA alert via Fonnte ke owner kalau cost delta ≥20% AND (margin drop ≥5pp OR new margin <20%)
- Dedup per (tenant, ingredient, day) via `margin_alert.sent` event
- Skip demo tenants, non-active subscription, no owner phone

---

## FASE 10 — Pre-Launch Hardening ✅ (2026-04-19 → 2026-04-25)

Batch hardening response ke production audit. Closed 17/17 CRITICAL bugs + ops infra.

### Backend Integrity (Batch #19-#21) ✅ 2026-04-21
- **#19** UUID `.id` attribute fix — silent-fail `hpp_benchmark_loop` unblocked
- **#19** Dine-in table release after payment — `payments.py:301` (cash) + `:619` (webhook) mirror `orders.py:519-533`
- **#20** Stale order janitor + orphan table healer — `backend/tasks/stale_order_cleanup.py`
- **#21** Ghost race guards — payments.py + tabs.py reject cancelled order / all-cancelled tab

### Backend Hardening (Batch #24) ✅ 2026-04-21
- SlowAPI fail-open Redis down (`ConditionalSlowAPIMiddleware`)
- Tab recalc on janitor cancel (mirror orders.py cancel path)
- Weekly sync_idempotency cleanup (per-tenant iteration karena RLS hard-cast policy)

### Adaptive UI + Strategic Positioning (Batch #26-#28) ✅ 2026-04-21
- Domain classifier 3 super-group + 10 bucket
- Flutter adaptive label system
- Waitlist signup + admin monitoring
- AI guardrail untuk non-F&B

### Stock Visual Guard + Inventory Powerhouse (Batch #28-#29 Flutter) ✅ 2026-04-22
- POS ProductCard `isAvailable` + `isOutOfStock` opacity 0.5 + HABIS/NONAKTIF badge
- ProductManagementPage tabbed UI (Produk + Stok)
- Embedded RestockPage + low-stock badge merah

### Stress Test Batch #30 ✅ 2026-04-22
- Tahap 1 E2E Smoke Integrity Test: GREEN, zero IntegrityError
- Tahap 2 k6 hammer scheduled
- Decision: 25 tenant aman publish (90% confidence), 30 conservative ceiling

### Starter Margin Tracking (Fase 1-3) ✅ 2026-04-24 → 2026-04-25
- **Fase 1** Migration 084 + model + schema
- **Fase 2** `restock_product()` accept `unit_buy_price` + `GET /reports/margin` endpoint
- **Fase 3** Flutter v1.0.39 RestockSheet + MarginReportPage + Drift schema v4→v5
- **Dashboard gap closure** form margin preview + `/dashboard/laporan/margin` page

### Final Pre-Launch Hardening ✅ 2026-04-25
- **Security:** MASTER_OTP bypass removed (`cbb833a`)
- **Reliability:** Xendit reconciliation cron RLS fix (`01910f5` — latent bug since shipping)
- **UX:** QRIS polling 30s timeout + retry dialog (`9619e64`)
- **Data Integrity:** Split-bill table release guard (`9762674`) — 2 code path: orders.py PUT status + janitor orphan heal. Bug ke-discover saat split-bill testing → kitchen mark order completed → table di-release prematurely.
- **UX Clarify:** "modal" vs "stok" copy fix 3 surface (`9538341`) — Flutter MarginReportPage + dashboard /laporan/margin + dashboard /menu form
- **Split-bill UX gaps:** TabInfoCard payment status row + table grid sub-badge (`f9985d1`)
- **Dashboard navigation:** Tap occupied table fetch /tabs/by-table → tab detail (delegate to existing flow), pendingNavigateToPosProvider one-shot signal (`eb8c4d9`)

### Split-Bill Humanity Pass ✅ 2026-04-25 (APK v1.0.45)
- **Bug fix `isActive` getter** — `tab_provider.dart` getter `isOpen` cuma cover `open|asking_bill`, miss `splitting`. Akibatnya tab status `splitting` GAK MUNCUL di Active Tabs List Page + counter under-report. Fix: tambah getter `isActive = isOpen || isSplitting`, update 2 caller (active_tabs_list filter + activeTabsCountProvider). `tab_bottom_actions` dan `_showMergeTabModal` sengaja stay pake `isOpen` (intentional gate — gak boleh add order / merge target saat splitting).
- **Struk per split (staggered payment)** — backend NEW `GET /tabs/{tab_id}/splits/{split_id}/receipt` mirror pattern `get_order_receipt`. Return outlet info + tab number + split label + position "X dari N" + payment method + outstanding info. Flutter: `SplitReceiptData` + `buildSplitReceipt()` di printer_service.dart dengan banner "*** BAYAR PATUNGAN ***" + footer adaptive ("Bill belum lunas, Y orang lagi" atau "*** BILL SUDAH LUNAS ***"). Auto-print dipicu di pay_split_modal post-cash-success via `unawaited()` (Rule #54 fail-silent). Real-world skenario "1 orang keluar duluan, sisanya nyusul" sekarang dapet bukti bayar individual per orang.

### Ops Infrastructure ✅ 2026-04-25
- **Telegram Healthcheck Alert** LIVE — bot connected chat_id=5918616553, cron `*/2 * * * *`, state-change throttle (anti-spam). Pivoted dari Healthchecks.io (signup difficulty) + Fonnte (self-send block).

---

## FASE 11 — Public Launch + Scale Operations ← CURRENT

### Pending Pre-Publish Action Items
**Carry-over user actions:**
- [ ] Update APK v1.0.44 di HP Ivan + Dita
- [ ] Manual verify 4 test scenario flow (split-bill tap occupied + dashboard nav + Tambah Pesanan + payment retry)
- [ ] Lanjutin tab `28db5d3a` collect 16420 dari Tamu 2 → close tab + table A1 release
- [ ] Isi 7 produk missing buy_price Kasira Coffee dashboard

**3 ops quick-wins masih pending (~2 jam total, GRATIS):**
- [ ] UptimeRobot status page (~15 menit) — public-facing trust
- [ ] pg_dump restore drill ke /tmp (~1 jam) — confidence boost
- [ ] TOS sederhana footer kasira.online (~30 menit) — legal protection
- [ ] Marketing copy update klaim AES-256 (~5 menit) — claim akurat: "AES-256-GCM at-rest dgn unique nonce", BUKAN per-outlet

**Manual test required pre-publish:**
- [ ] FIX QRIS retry dialog di device real — install APK v1.0.44, simulate offline saat QRIS modal
- [ ] Split-bill end-to-end di device — open tab → split → bayar 1 split → kitchen mark complete → verify table TETAP occupied
- [ ] Verify margin report copy clarity (read banner saat ada missing buy_price)

### Belum Dibangun (deferred / low priority)
- [ ] Multi-outlet full implementation (Business tier) — defer sampai customer demand
- [ ] POST /auth/refresh — low priority
- [ ] Flutter: loyalty points UI
- [ ] Flutter: ingredient restock wire (sekarang dashboard-only)
- [ ] AI Reservation Tools (~4h) — niche, defer sampai reservasi user base meningkat
- [ ] Starter Template Seed Non-F&B (~3h) — defer, revisit kalau waitlist signal kuat (>20 retail/service tenant joined)

### Capacity Trigger Upgrade
**Upgrade VPS ketika 2 dari 3 indicator masuk kuning sustained 7 hari:**

| Indicator | Hijau | Kuning | Merah |
|---|---|---|---|
| Memory util peak | <60% | 60-80% | >80% |
| Backend p99 latency | <500ms | 500-1500ms | >1500ms |
| Support ticket capacity issue/hari | <2 | 2-5 | >5 |

Upgrade path: Vultr Cloud Compute 4C/8GB (~$30/bulan) untuk 30-50 cafe → Vultr Dedicated 2C/8GB (~$48/bulan) atau General Purpose 4C/16GB (~$96/bulan) untuk 50-100 cafe.

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
- Idempotency key wajib untuk payment + storefront order + sync push
- Timezone: simpan UTC, tampilkan Asia/Jakarta
- Phone numbers WAJIB masked di response (mask_phone())

### Auth
- OTP WA only — tidak ada email+password
- JWT: httpOnly cookie (web), SecureStorage (mobile)
- OTP expire 5 menit, max 3x resend per 15 menit
- Owner/admin nomor WAJIB beda dari Fonnte device sender (WA self-send block)

### Stock
- Deduct otomatis dari transaksi
- Stok = 0 → `is_available: false`, TETAP MUNCUL
- `order_display_number` dari PostgreSQL SEQUENCE
- Sort `order_in.items` by `product_id` SEBELUM loop deduct (deadlock prevention)

### Payment
- Payment endpoint WAJIB `SELECT FOR UPDATE`
- `xendit_raw` (JSONB) WAJIB disimpan
- `partial_payments` = Pro+ only
- Payment-path bypasses `PUT /orders/{id}/status` — side-effect (table release, tab recalc) WAJIB replicated manual di payments.py
- Cancelled order reject di payment endpoint (ghost race guard)

### Tab / Split-Bill
- Order completion ≠ "all paid" di tab era
- WAJIB cek `tab.status NOT IN ('paid', 'cancelled')` sebelum release table
- 2 code path guard: `orders.py:519+` PUT status + `stale_order_cleanup.py:185+` janitor

### Background Tasks
- WAJIB `SET LOCAL app.current_tenant_id = ''` di awal session
- RLS policy default unset → query return 0 rows silently kalau gak set context
- Per-tenant iteration kalau RLS policy hard-cast UUID tanpa bypass clause (Migration 081 sync_idempotency_keys)

### Deploy
- Backend: `docker cp` + `docker restart` (BUKAN `docker compose up -d`)
- Frontend: `docker compose build frontend && docker compose up -d --no-deps frontend`
- Flutter: git push (verify origin/main HEAD match) → GitHub Actions workflow_dispatch → APK release
- WAJIB cek `gh run` `conclusion` BUKAN cuma `status` (completed bisa failure)

---

## Build Priority Rules
1. FASE 0 WAJIB selesai sebelum FASE 1
2. FASE 1 (Auth) WAJIB selesai sebelum fitur apapun
3. Backend endpoint WAJIB ada sebelum Flutter consume
4. Migration WAJIB test upgrade + downgrade sebelum lanjut
5. ROADMAP.md = source of truth untuk fitur dan tier
6. Jangan skip step — setiap step ada dependency
7. Senior Audit Pattern WAJIB sebelum klaim "bulletproof" di fitur kritikal (sync, stock, payment, CRDT, auth) — role-swap ke auditor mode, spawn 3-4 skenario kiamat, tunjukin file:line yang jamin

---

## System State (2026-04-25)
- **Migration head:** 084
- **APK head:** v1.0.44 (POS + Dapur)
- **Containers:** 4 (backend, frontend, db, redis) — all healthy
- **Tenants production:** 3 real (Kasira Coffee pro, Dita Coffee starter, B coffee starter) + 1 _loadtest_tenant (pro, is_demo)
- **Embeddings:** all products embedded across tenants
- **Anthropic API:** budget controlled, Sonnet quota 5x/hari/tenant
- **Voyage AI:** working (voyage-3-lite, 512 dims)
- **Cloudflare:** DNS proxied, SSL Full Strict
- **R2 backup:** every 6 hours, 14-day retention
- **Sentry:** configured
- **Prometheus metrics:** `/metrics` endpoint exposed
- **Telegram healthcheck:** LIVE, chat_id=5918616553, `*/2 * * * *`
- **Disaster Recovery:** RTO 60min, RPO 6h, scripts ready
- **Postgres tuning:** shared_buffers 256MB, work_mem 8MB (applied 2026-04-18)
- **Task supervisor:** 10 background tasks (was 7, +stale_order_cleanup, +sync_idempotency_cleanup, +kg_price_event_loop)
- **VPS:** Vultr shared 2C/3.8GB, capacity headroom 25 tenant @ 90% confidence, 30 conservative ceiling
- **Pricing:** Pro Rp 299.000/bulan (decision 2026-04-18), Starter gratis dengan margin tracking
