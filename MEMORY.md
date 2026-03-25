# KASIRA — Long-Term Memory
# Update ini setiap selesai satu task!

## ✅ SELESAI
- [x] Migration Batch 1 (tenants, brands, outlets)
- [x] Migration Batch 2 (roles, users, sessions, devices, suppliers, customers, outlet_tax_config, tables)
- [x] Migration Batch 3 (categories, products, product_variants, modifiers, outlet_product_overrides, ingredients, ingredient_units, ingredient_suppliers, outlet_stock, recipes, recipe_ingredients)
- [x] Migration Batch 4 (pricing_rules, shifts, orders, order_items, payments, reservations, purchase_orders, purchase_order_items)
- [x] Migration Batch 5 (customer_points, point_transactions)
- [x] Migration Batch 6 (notifications, knowledge_graph_edges, stock_events, stock_snapshots, audit_log, global_event_log)
- [x] Migration Batch 7 (connect_outlets, connect_orders, connect_customer_profiles, connect_chats, connect_behavior_log)
- [x] Migration Batch 8 (outlet_location_detail, supplier_price_history, products_update, subscriptions, invoices, subscription_payments, payments_update, partial_payments, payment_refunds)
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
- [x] Create backend/scripts/seed_demo.py
- [x] Fix Connect API bugs (product fields, order sequence, error messages)
- [x] Fix backend/scripts/seed_demo.py (imports, timezone, search_path, idempotent)
- [x] Fix backend/scripts/seed_demo.py models (remove tenant_id from Category/Product/Shift, add stock_enabled)
- [x] Create Dockerfile.next for Next.js frontend
- [x] Fix route conflict in connect.py (/order/{id} -> /orders/{id}) and update frontend polling
- [x] Fix Next.js auth (save tenant_id & outlet_id to cookies, add X-Tenant-ID header)
- [x] Fix backend auth response to include tenant_id & outlet_id
- [x] Fix Flutter app entry point (DashboardPage -> LoginPage)

## ⏳ IN PROGRESS
- Menunggu instruksi selanjutnya

## ⏳ BELUM MULAI
- Flutter kasir app (15 layar)
- Flutter dapur app (8 layar)
- Self-order Next.js
- CRDT sync engine
- Pilot Otomatis rule engine
- AI chatbot SSE streaming

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
- Payment: Midtrans QRIS + idempotency key
- Tax: PB1 10%, PPN 12%, service charge configurable

## Lanjut Berikutnya
Menunggu instruksi selanjutnya untuk fitur Flutter atau Backend.

## Context Files Status
- context/database.md    → ⏳ In Progress
- context/auth.md        → ⏳ Belum dibuat
- context/orders.md      → ⏳ Belum dibuat
- context/inventory.md   → ⏳ Belum dibuat
- context/payment.md     → ⏳ Belum dibuat
- context/flutter-kasir.md → ⏳ Belum dibuat
- context/connect.md     → ⏳ Belum dibuat
