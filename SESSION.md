# SESSION — 2026-03-20
# Claude update file ini otomatis tiap task selesai

## FOKUS HARI INI
- [x] Task 1: Buat file Alembic untuk Batch 1 (tenants, brands, outlets)
- [x] Task 2: Buat file Alembic untuk Batch 2 (roles, users, sessions, devices, suppliers, customers, outlet_tax_config, tables)
- [x] Task 3: Buat file Alembic untuk Batch 3 (products, inventory, recipes)
- [x] Task 4: Buat file Alembic untuk Batch 4 (pricing_rules, shifts, orders, payments, reservations, purchase_orders)

## MODUL AKTIF
Modul: Database Migrations
File dikerjakan:
- backend/migrations/versions/023_pricing_rules.py
- backend/migrations/versions/023b_shifts.py
- backend/migrations/versions/024_orders.py
- backend/migrations/versions/025_order_items.py
- backend/migrations/versions/026_payments.py
- backend/migrations/versions/027_reservations.py
- backend/migrations/versions/028_purchase_orders.py
- backend/migrations/versions/029_purchase_order_items.py

## PROGRESS
✅ Selesai:
- CRDT Bug Fixes (HLC.receive logic and PNCounter lower bound)
- Update backend requirements (uvicorn, cryptography)
- Translate X-Tenant-ID error message
- Add WA receipt logic for Cash and QRIS payments
- Setup Flutter Login OTP Flow (4 states: Input Phone, Input OTP, Set PIN, PIN Login) with Riverpod
- Setup Flutter QRIS Screen (Payment Modal, QrImageView, Timer, Polling)
- Setup Alembic file 038_connect_outlets.py
- Setup Alembic file 039_connect_orders.py (idempotency_key UNIQUE, FK to orders, ENUM status)
- Setup Alembic file 040_connect_customer_profiles.py
- Setup Alembic file 041_connect_chats.py (message_encrypted AES-256)
- Setup Alembic file 042_connect_behavior_log.py (Append only)
- Setup Alembic file 043_outlet_location_detail.py
- Setup Alembic file 044_supplier_price_history.py
- Setup Alembic file 045_products_update.py (ALTER TABLE add sku, barcode, is_subscription)
- Setup Alembic file 046_subscriptions.py (row_version)
- Setup Alembic file 047_invoices.py (row_version)
- Setup Alembic file 048_subscription_payments.py
- Setup Alembic file 049_payments_update.py (ALTER TABLE order_id nullable, add invoice_id, is_partial)
- Setup Alembic file 050_partial_payments.py
- Setup Alembic file 051_payment_refunds.py (approved_by FK)
- FastAPI project init (requirements.txt, main.py, config.py, database.py, security.py)
- Auth setup (JWT, PIN verification, deps.py, auth routes)
- Base models and schemas (BaseModel, User, Tenant, Outlet, StandardResponse)
- CRUD routes for users, tenants, outlets
- CRUD routes for categories and products
- Simple Stock logic for products (restock endpoint, auto-hide on 0 stock)
- CRUD routes for orders and payments (Transaction-First Simple Stock deduct)
- Payment + Midtrans QRIS integration (API service + Webhook)
- Setup Flutter App UI (Kasir) - Init project, Theme, Colors, Login Page
- Setup Flutter App UI (Kasir) - POS Page Layout (Split screen, Product Grid, Cart Panel)
- Setup Flutter App UI (Kasir) - Dashboard Page (Sidebar, Stats, Recent Orders)
- Setup Flutter App UI (Kasir) - Payment Modal (Cash/QRIS, Quick Cash, Change calculation)
- Setup Flutter App UI (Kasir) - Order List Page (Tabs: Semua, Diproses, Selesai, Batal)
- Setup Flutter App UI (Kasir) - Shift Management Page (Buka/Tutup Shift, Modal Awal, Rekap)
- Setup Flutter App UI (Kasir) - Product Management Page (Toggle Habis/Tersedia)
- Setup Flutter App UI (Kasir) - Settings Page (Printer, Sync, Profil Kasir)
- Setup Flutter App UI (Kasir) - Customer Selection Modal (Pilih Pelanggan di POS)
- Setup Flutter App UI (Kasir) - Order Detail Modal (Rincian Pesanan)
- Setup Flutter App UI (Kasir) - Add Customer Modal (Tambah Pelanggan Baru)
- Setup Flutter App UI (Kasir) - Printer Settings Page (Bluetooth Printer Config)

⏳ In Progress:
   Nama: Setup Flutter App UI
   File: kasir_app/lib/*
   Sudah: Init Flutter project, Theme, Login Page, POS Page, Dashboard Page, Payment Modal, Order List, Shift Page, Product Management, Settings, Customer Selection, Order Detail, Add Customer, Printer Settings
   Tinggal: Melanjutkan pembuatan 3 layar kasir lainnya (Sync Settings, Cash Drawer History, Profile)
   Catatan: Menggunakan Riverpod untuk state management dan GoRouter untuk routing.

⏳ In Progress:
   Nama: Backend Sync Engine (Pure CRDT)
   File: backend/services/crdt.py, backend/services/sync.py, backend/api/routes/sync.py, backend/migrations/versions/052_add_missing_row_versions.py
   Sudah: Create migration for missing row_versions, update models, create CRDT math engine (HLC, PNCounter), create sync orchestrator, refactor /sync endpoint to use Pure CRDT.
   Tinggal: Testing sync endpoint.

✅ Selesai:
- Setup Flutter App UI (Kasir) - Sync Settings Page
- Setup Flutter App UI (Kasir) - Profile Page
- Setup Flutter App UI (Kasir) - Cash Drawer History Page
- Backend Shift Management (models, schemas, migrations, API routes, sync engine integration)

❌ Belum:
- Flutter dapur app (8 layar)
- Self-order Next.js
- CRDT sync engine (Testing)
- Pilot Otomatis rule engine
- AI chatbot SSE streaming

## FILE YANG DIUBAH HARI INI
- backend/services/crdt.py
- backend/requirements.txt
- backend/api/deps.py
- backend/api/routes/payments.py
- kasir_app/pubspec.yaml
- kasir_app/lib/features/auth/presentation/pages/login_page.dart
- backend/migrations/versions/001_tenants.py s/d 051_payment_refunds.py
- backend/requirements.txt
- backend/main.py
- backend/core/config.py
- backend/core/database.py
- backend/core/security.py
- backend/api/deps.py
- backend/api/api.py
- backend/api/routes/auth.py
- backend/api/routes/users.py
- backend/api/routes/tenants.py
- backend/api/routes/outlets.py
- backend/api/routes/categories.py
- backend/api/routes/products.py
- backend/api/routes/orders.py
- backend/api/routes/payments.py
- backend/models/base.py
- backend/models/user.py
- backend/models/tenant.py
- backend/models/outlet.py
- backend/models/category.py
- backend/models/product.py
- backend/models/order.py
- backend/models/payment.py
- backend/schemas/token.py
- backend/schemas/user.py
- backend/schemas/tenant.py
- backend/schemas/outlet.py
- backend/schemas/category.py
- backend/schemas/product.py
- backend/schemas/stock.py
- backend/schemas/order.py
- backend/schemas/payment.py
- backend/schemas/response.py
- backend/services/midtrans.py
- kasir_app/pubspec.yaml
- kasir_app/lib/main.dart
- kasir_app/lib/core/theme/app_colors.dart
- kasir_app/lib/core/theme/app_theme.dart
- kasir_app/lib/features/auth/presentation/pages/login_page.dart
- kasir_app/lib/features/pos/presentation/pages/pos_page.dart
- kasir_app/lib/features/pos/presentation/widgets/product_card.dart
- kasir_app/lib/features/pos/presentation/widgets/cart_panel.dart
- kasir_app/lib/features/pos/presentation/widgets/payment_modal.dart
- kasir_app/lib/features/dashboard/presentation/pages/dashboard_page.dart
- kasir_app/lib/features/orders/presentation/pages/order_list_page.dart
- kasir_app/lib/features/shift/presentation/pages/shift_page.dart
- kasir_app/lib/features/products/presentation/pages/product_management_page.dart
- kasir_app/lib/features/settings/presentation/pages/settings_page.dart
- kasir_app/lib/features/customers/presentation/widgets/customer_selection_modal.dart
- kasir_app/lib/features/orders/presentation/widgets/order_detail_modal.dart
- kasir_app/lib/features/customers/presentation/widgets/add_customer_modal.dart
- kasir_app/lib/features/settings/presentation/pages/printer_settings_page.dart
- app/page.tsx
- MEMORY.md
- SESSION.md

## KEPUTUSAN BARU HARI INI
- Menambahkan tabel integrasi Kasira Connect: `connect_outlets` (038), `connect_orders` (039), `connect_customer_profiles` (040), `connect_chats` (041), dan `connect_behavior_log` (042).
- Menambahkan `idempotency_key` (UNIQUE) dan ENUM status yang lengkap pada tabel `connect_orders`.
- Menggunakan `message_encrypted` (Text) dengan komentar AES-256 pada tabel `connect_chats` untuk menjaga kerahasiaan pesan.
- Menjadikan `connect_behavior_log` sebagai tabel append-only (tanpa `updated_at` dan `deleted_at`).
- Menambahkan tabel `outlet_location_detail` (043) dan `supplier_price_history` (044).
- Menggunakan ALTER TABLE pada `products` (045) untuk menambahkan `sku`, `barcode`, dan `is_subscription`.
- Menambahkan tabel billing: `subscriptions` (046) dan `invoices` (047), keduanya dilengkapi dengan `row_version`.
- Update `subscriptions` (046): Tambah `plan_tier`, `outlet_count`, `amount_per_period`, dan `grace_period_end_at`.
- Menambahkan `subscription_payments` (048).
- Update `subscription_payments` (048): Ubah `payment_method` menjadi ENUM, tambah `collected_by` (FK users), dan `wa_sent_at`.
- Menggunakan ALTER TABLE pada `payments` (049) untuk mengubah `order_id` menjadi nullable, serta menambahkan `invoice_id` dan `is_partial`.
- Menambahkan tabel `partial_payments` (050) dan `payment_refunds` (051) dengan FK `approved_by`.
- Update `partial_payments` (050): Ubah `payment_method` menjadi ENUM, tambah `status` ENUM (paid/refunded), dan `notes`.
- Inisialisasi FastAPI project dengan struktur folder yang rapi (`core`, `api`, `models`, `schemas`).
- Menggunakan format response standar `{success, data, meta, request_id, message}` untuk semua endpoint (kecuali OAuth2 token endpoint).
- Setup JWT authentication dan PIN verification.
- Implementasi CRUD Categories & Products.
- Implementasi Simple Stock (Tier Starter): Tambah endpoint `/products/{id}/restock` dan auto-hide jika stok <= 0.
- Implementasi CRUD Orders & Payments:
  - `POST /orders`: Membuat order dan otomatis memotong stok produk (Transaction-First). Jika stok <= 0 dan `stock_auto_hide` aktif, produk otomatis disembunyikan.
  - `POST /payments`: Membuat payment. Jika metode `cash`, status langsung `paid` dan status order menjadi `completed`. Jika `qris`, status `pending` dan generate mock QRIS URL.
- Integrasi Midtrans QRIS:
  - Menambahkan `httpx` ke `requirements.txt`.
  - Membuat `backend/services/midtrans.py` untuk generate QRIS via Midtrans Core API.
  - Menambahkan endpoint `POST /payments/webhook/midtrans` untuk menerima notifikasi dari Midtrans (dengan verifikasi `signature_key`).
  - Jika webhook menerima status `settlement`, status payment otomatis menjadi `paid` dan status order menjadi `completed`.
- Inisialisasi Flutter Kasir App (`kasir_app`):
  - Menggunakan arsitektur Feature-First.
  - State management: `flutter_riverpod`.
  - Routing: `go_router`.
  - Theme: Menggunakan warna utama `#FF5C00` dan font `Syne` (untuk headings) serta `Inter` (untuk body text) sesuai dengan Logo System Kasira.
  - Membuat `LoginPage` sebagai layar pertama dengan desain modern, card putih di atas background orange, dan input PIN yang besar.
  - Membuat `PosPage` (Point of Sale) dengan layout split-screen (kiri: kategori & grid produk, kanan: keranjang/cart).
  - Membuat komponen `ProductCard` dengan overlay "HABIS" otomatis jika stok 0.
  - Membuat komponen `CartPanel` dengan pilihan Dine In/Takeaway dan rincian subtotal/pajak.
  - Membuat `DashboardPage` dengan Sidebar Navigation, Stats Cards (Pendapatan, Transaksi), dan daftar Transaksi Terakhir.
  - Membuat `PaymentModal` untuk memproses pembayaran (Pilih Cash/QRIS, hitung kembalian otomatis, tombol Quick Cash).
  - Membuat `OrderListPage` dengan TabBar (Semua, Diproses, Selesai, Batal) dan Search Bar.
  - Membuat `ShiftPage` untuk manajemen laci kasir (Modal Awal, Penerimaan, Pengeluaran, Input Aktual).
  - Membuat `ProductManagementPage` untuk mengubah status ketersediaan produk (Tersedia/Habis).
  - Membuat `SettingsPage` untuk pengaturan printer, sinkronisasi, dan profil.
  - Membuat `CustomerSelectionModal` untuk memilih atau menambah pelanggan saat transaksi POS.
  - Membuat `OrderDetailModal` untuk melihat rincian pesanan dari Order List.
  - Membuat `AddCustomerModal` untuk menambah pelanggan baru.
  - Membuat `PrinterSettingsPage` untuk mengatur koneksi Bluetooth printer.

## BLOCKER
- Tidak ada.

## CHECKPOINT TERAKHIR
Terakhir sampai di: Selesai membuat QRIS Screen di Flutter (Payment Modal).
Besok lanjut dari: Menunggu instruksi selanjutnya untuk fitur Flutter atau Backend.
