# KASIRA — Roadmap & Build Order
# Claude Code: baca ini untuk tau harus ngapain selanjutnya

## Status Sekarang
- [ ] FASE 0: Fondasi ← MULAI DARI SINI
- [ ] FASE 1: Auth
- [ ] FASE 2: Core POS Starter
- [ ] FASE 3: Flutter Kasir App
- [ ] FASE 4: Owner Dashboard Next.js
- [ ] FASE 5: Pilot
- [ ] FASE 6: Pro Features

---

## FASE 0 — Fondasi (Wajib selesai sebelum 1 baris fitur)

### Step 0.1 — VPS Setup
```bash
# Jalankan kasira-setup.sh di VPS
bash kasira-setup.sh
```
- [ ] PostgreSQL 16 running
- [ ] Redis running
- [ ] FastAPI project init
- [ ] Folder structure: /var/www/kasira/

### Step 0.2 — CLAUDE.md + MEMORY.md di VPS
- [ ] Copy semua file MD ke /var/www/kasira/
- [ ] skills/ folder lengkap
- [ ] context/ folder siap

### Step 0.3 — Alembic Migration (FK-safe order)

#### Batch 1 — Root Tables (tidak ada FK)
```
01. tenants
02. brands          → tenants
03. outlets         → brands, tenants ★ BANYAK YANG BERGANTUNG
04. roles           → tenants
05. users           → tenants, roles
```

#### Batch 2 — User & Device
```
06. sessions        → users, outlets
07. devices         → users, outlets
08. suppliers       → tenants
09. customers       → tenants
10. outlet_tax_config → outlets
```

#### Batch 3 — Products & Ingredients
```
11. tables          → outlets
12. products        → brands ★ COMPLEX (18 fields + row_version + CHECK)
13. product_variants → products
14. modifiers       → brands
15. outlet_product_overrides → outlets, products
16. ingredients     → brands
17. ingredient_units → ingredients
18. ingredient_suppliers → ingredients, suppliers
19. outlet_stock    → outlets, ingredients (CRDT JSONB + CHECK)
20. recipes         → products
21. recipe_ingredients → recipes, ingredients
```

#### Batch 4 — Orders & Transactions
```
22. pricing_rules   → tenants, brands, outlets
23. orders          → outlets, users, customers(nullable), tables(nullable)
24. reservations    → outlets, tables, customers(nullable) + row_version
25. payments        → orders (COMPLEX - 20 fields)
26. purchase_orders → outlets, suppliers
27. purchase_order_items → purchase_orders, ingredients
28. customer_points → customers, tenants + row_version
29. point_transactions → customers, orders + UNIQUE(order_id, type)
30. order_feedback  → orders, customers(nullable)
```

#### Batch 5 — Supporting & Analytics
```
31. notifications   → tenants, outlets
32. knowledge_graph_edges → tenants, brands
33. ai_setup_sessions → tenants, outlets
34. stock_events    → outlets, ingredients
35. stock_snapshots → outlets, ingredients
36. audit_log       → users, outlets
37. global_event_log → tenants, outlets
```

#### Batch 6 — Connect (Storefront)
```
38. connect_outlets → outlets
39. connect_orders  → orders, outlets + idempotency_key
40. connect_customer_profiles → customers
41. connect_chats   → connect_orders
42. connect_behavior_log → connect_orders
```

#### Batch 7 — Billing
```
43. outlet_location_detail → outlets
44. supplier_price_history → suppliers
45. products columns update → sold_today, sold_total
46. subscriptions   → tenants + row_version
47. invoices        → tenants, subscriptions + row_version
48. subscription_payments → invoices
49. payments update → expanded schema (20 fields)
50. partial_payments → payments, orders (Pro+)
51. payment_refunds → payments, orders
52. pending_receipts → SQLite Flutter (bukan PostgreSQL!)
```

### Step 0.4 — Infrastruktur Wajib
- [ ] Event store table (append-only)
- [ ] Audit log middleware semua WRITE endpoint
- [ ] Rate limiting: auth 5/min, payment 10/min
- [ ] Field encryption AES-256-GCM helper
- [ ] mask_phone() helper di semua response
- [ ] Response format wrapper: {success, data, meta, request_id}

### Definition of Done FASE 0
```
✓ alembic upgrade head — 0 error
✓ alembic downgrade base — 0 error
✓ Semua CHECK constraints verified
✓ Semua ENUM types created
✓ PostgreSQL SEQUENCE untuk display_number
✓ pg_dump backup berjalan
✓ Redis + Celery connected
```

---

## FASE 1 — Auth (Week 1 setelah FASE 0)

### Fitur
- OTP WA via Fonnte — kirim, verify, expire 5 menit
- JWT access token + refresh token
- Device binding — login per device
- PIN offline — kasir bisa login tanpa internet
- Role & permission check per endpoint
- Tenant + outlet setup wizard

### Files yang akan dibuat
```
backend/
├── routers/auth.py
├── services/auth_service.py
├── services/otp_service.py
├── services/fonnte_service.py
├── middleware/auth_middleware.py
├── middleware/tenant_middleware.py
└── models/auth.py
```

### Definition of Done FASE 1
```
✓ POST /auth/register — buat tenant baru
✓ POST /auth/otp/send — kirim OTP ke WA
✓ POST /auth/otp/verify — verify + return JWT
✓ POST /auth/pin/set — kasir set PIN
✓ POST /auth/pin/login — login offline pakai PIN
✓ POST /auth/refresh — refresh JWT
✓ DELETE /auth/logout — revoke token
✓ GET /auth/me — profile user
✓ Middleware: verify JWT tiap request
✓ Middleware: set search_path tenant
```

---

## FASE 2 — Core POS Starter (Week 2-3)

### Fitur
- Products + categories CRUD
- Orders + order_items
- Payment: cash + QRIS Midtrans
- Struk WA via Fonnte
- Simple stock — deduct otomatis
- Shift buka/tutup + rekap kas
- Basic reporting

### Definition of Done FASE 2
```
✓ Kasir bisa input order sampai payment
✓ QRIS generate + callback webhook
✓ Struk terkirim ke WA customer
✓ Stok auto-deduct per transaksi
✓ Shift rekap bisa di-close
✓ Revenue hari ini tampil di dashboard
```

---

## FASE 3 — Flutter Kasir App (Week 3-4)

### 15 Layar Kasir
1. Splash + update checker
2. Login OTP WA
3. PIN login (offline)
4. Dashboard meja (grid)
5. Order screen (menu grid)
6. Order detail + catatan
7. Payment screen (cash/QRIS)
8. QRIS waiting screen
9. Payment success
10. Receipt preview
11. Riwayat transaksi
12. Shift buka
13. Shift tutup + rekap
14. Low stock alert
15. Settings

### Definition of Done FASE 3
```
✓ Kasir bisa transaksi end-to-end
✓ Offline mode: order bisa masuk tanpa internet
✓ Sync otomatis saat online
✓ Printer reconnect tidak block transaksi
✓ QRIS fallback ke cash berfungsi
```

---

## FASE 4 — Owner Dashboard Next.js (Week 4-5)

### Halaman
1. Login owner
2. Dashboard overview
3. Revenue + laporan
4. Menu management
5. Stock management
6. User + kasir management
7. Connect setup (storefront)
8. Download APK

### Definition of Done FASE 4
```
✓ Owner bisa lihat revenue real-time
✓ Owner bisa tambah/edit menu
✓ Owner bisa tambah kasir
✓ Connect storefront aktif otomatis
```

---

## FASE 5 — Pilot (Bulan 2)

### Checklist Pre-Pilot
- [ ] pg_dump backup berjalan tiap 6 jam
- [ ] UptimeRobot monitoring aktif
- [ ] kasira-setup.sh tested di VPS bersih
- [ ] APK upload ke R2
- [ ] Landing page kasira.id live
- [ ] Training kasir selesai
- [ ] Error monitoring (Sentry/logtail)

---

## FASE 6 — Pro Features (Bulan 3+)

- Reservasi + booking
- Kasira Connect storefront full
- AI chatbot owner
- Knowledge Graph
- Loyalty points
- Tab/Bon system
- Invoice scan + HPP
- Multi-outlet

---

## Build Priority Rules
1. FASE 0 WAJIB selesai sebelum FASE 1
2. FASE 1 (Auth) WAJIB selesai sebelum fitur apapun
3. Backend endpoint WAJIB ada sebelum Flutter consume
4. Migration WAJIB test upgrade + downgrade sebelum lanjut
5. Jangan skip step — setiap step ada dependency
