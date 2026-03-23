# CONTEXT — DATABASE MIGRATIONS

## STATUS
✅ Selesai (Batch 1)
⏳ In Progress (Menunggu Approval Batch 2)

## FILE LIST
- backend/migrations/versions/001_tenants.py
- backend/migrations/versions/002_brands.py
- backend/migrations/versions/003_outlets.py

## KEPUTUSAN TEKNIS
- Menggunakan `op.execute("CREATE TYPE ... AS ENUM (...)")` untuk menghindari isu Alembic auto-generate dengan PostgreSQL ENUMs.
- Semua tabel menggunakan `id UUID DEFAULT gen_random_uuid() PRIMARY KEY`.
- Semua tabel kritikal (`tenants`, `brands`, `outlets`) memiliki `row_version` INT DEFAULT 0 untuk optimistic locking.
- Soft delete diimplementasikan via `deleted_at TIMESTAMPTZ`.
- FK order dipatuhi: `tenants` -> `brands` -> `outlets`.
- `outlets` memiliki denormalized `tenant_id` untuk performance query.

## GOTCHA / JANGAN DIUBAH
- Jangan lupa `ondelete='CASCADE'` pada FK jika diperlukan, namun karena kita pakai soft delete, penghapusan data master sebaiknya ditangani di level application logic (soft delete cascade). Saat ini FK diset `CASCADE` di DB level untuk hard delete jika diperlukan saat development.
- `outlets` memiliki banyak feature toggles (BOOLEAN) yang defaultnya `false` kecuali `qris_enabled` dan `cash_enabled`.

## DEPENDENCY
Dipakai oleh: Semua modul backend.
Bergantung pada: PostgreSQL 16.
