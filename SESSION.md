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

## ⏭️ NEXT ACTION

### PRIORITAS 1 — Flutter APK via GitHub Actions
Workflow sudah siap, tidak perlu R2. Yang perlu dilakukan:
1. Push/merge ke GitHub (branch `claude/review-documentation-qqAkC` atau `main`)
2. Buka GitHub → Actions → "Build & Release Kasira Flutter APK" → Run workflow
3. Isi: version=1.0.0, is_mandatory=false, release_notes
4. Tunggu ~5-10 menit → APK tersedia di GitHub Releases

**Checklist sebelum build:**
- [ ] Repo sudah di-push ke GitHub
- [ ] Branch `main` ada di GitHub (untuk version.json)
- [ ] Workflow jalan dari branch yang ada `build-apk.yml`-nya

**Setelah APK jadi:**
- Download `kasira-pos-v1.0.0.apk` dari GitHub Releases
- Install di HP → login dengan phone `628111222333`, OTP `123456`, PIN `111222`
- Set Server URL: `http://103.189.235.164:8000`

### PRIORITAS 2 — Dashboard Pro Features Teaser (belum dieksekusi)
Buat halaman/section di dashboard yang menampilkan fitur Pro sebagai "teaser" — tampil tapi tidak bisa diakses, ada badge "Pro" + tombol "Upgrade". Tujuan: daya tarik untuk upgrade.

**File yang akan dibuat/diubah:**
- `app/dashboard/layout.tsx` — tambah section Pro di sidebar (badge "PRO" terkunci)
- `app/dashboard/pro/page.tsx` — halaman khusus Pro features showcase
- Atau: tambah cards di `app/dashboard/page.tsx` (overview) sebagai teaser

**Fitur Pro yang ditampilkan (dari ROADMAP.md FASE 6):**
| Fitur | Icon | Deskripsi singkat |
|---|---|---|
| Reservasi & Booking | CalendarCheck | Pelanggan bisa booking meja via storefront |
| AI Chatbot Owner | Bot | Tanya laporan & insight bisnis via WA |
| Loyalty Points | Star | Program poin pelanggan otomatis |
| Tab / Bon | Receipt | Pembayaran cicil / bon pelanggan |
| Multi-Outlet | Building2 | Kelola banyak cabang dalam 1 akun |
| Laporan Lanjutan | BarChart3 | HPP, analitik tren, export Excel |

**Desain teaser card:**
```
┌─────────────────────────────┐
│ 🔒 [Ikon] Nama Fitur  [PRO] │
│ Deskripsi singkat 1-2 baris │
│ [Hubungi untuk Upgrade]     │
└─────────────────────────────┘
```
- Card grayscale/blur sedikit, badge PRO kuning/gold
- Tombol "Upgrade ke Pro" → bisa link WA owner Kasira
- Di sidebar: nav item terkunci dengan lock icon + badge PRO

**Storefront booking pages** (`app/[slug]/booking/`) — pertimbangkan redirect ke halaman info "Fitur ini belum aktif di outlet ini" atau hapus routing sama sekali untuk Starter.

---

### PRIORITAS 2 — Bug & Polish yang tersisa
- Cek halaman **Kasir** di dashboard (`/dashboard/kasir`)
- Cek halaman **Laporan** (`/dashboard/laporan`) — pastikan data load benar
- **Seed produk demo** untuk test storefront: `docker exec kasira-backend-1 python -m backend.scripts.seed_demo`
- **UptimeRobot** — monitor http://103.189.235.164:8000/ dan http://103.189.235.164:3000/

### Cara reconnect:
> "baca CLAUDE.md, MEMORY.md, SESSION.md di /var/www/kasira/ lalu lanjut dari NEXT ACTION"
