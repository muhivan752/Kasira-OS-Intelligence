# SESSION — 2026-04-03
# Claude update file ini otomatis tiap task selesai

## ✅ SELESAI SESI INI
- [x] Feature E: Reservasi + Booking via Connect
- [x] Feature D fix: loyalty.py route + model + migration 059 (file hilang, dibuat ulang)

## 🔴 LANJUT DARI SINI → Feature F: FASE 5 Pre-Pilot

---

## CHECKPOINT LENGKAP — RESUME DARI SINI

### Branch aktif
```
claude/review-documentation-qqAkC
```
Last commit: feat: Feature E — Reservasi + Booking + Loyalty fix

### Urutan priority fitur tersisa
```
F → VPS
```
1. **Feature F: FASE 5 Pre-Pilot** ← NEXT
2. VPS Deployment (kasira-setup.sh sudah siap)

---

## FEATURE F: FASE 5 PRE-PILOT — Detail Teknikal

### Yang harus dibuat/dikerjakan:
1. **UptimeRobot** — tambah monitor config/instructions di docs atau README
2. **Sentry** — integrate ke backend FastAPI + Next.js frontend
   - `pip install sentry-sdk[fastapi]`
   - `SENTRY_DSN` env var
   - Sentry.init di main.py + next.config.js
3. **APK ke Cloudflare R2** — update `.github/workflows/build-apk.yml`
   - Upload kasira-pos-v*.apk + kasira-dapur-v*.apk ke R2 setelah build
4. **.env.example** — tambah:
   - `ANTHROPIC_API_KEY=sk-ant-...`
   - `SENTRY_DSN=https://...`
5. **Verify pg_dump cron** — sudah ada di kasira-setup.sh, cek syntax benar

### File yang perlu dibaca sebelum coding Feature F:
1. `.env.example` — lihat apa yang sudah ada
2. `backend/main.py` — lihat struktur app FastAPI
3. `.github/workflows/build-apk.yml` — lihat struktur workflow
4. `kasira-setup.sh` — verify pg_dump cron

---

## FEATURE E — Summary yang Sudah Selesai

### backend/models/reservation.py
- `Table`: outlet_id, name, capacity, status (available/reserved/occupied/closed), position_x, position_y, is_active, row_version
- `Reservation`: outlet_id, customer_id, table_id, reservation_time, guest_count, status (pending/confirmed/cancelled/completed), notes, row_version

### backend/api/routes/reservations.py (BARU)
- `GET /reservations/?outlet_id=` → list reservasi (bulk load N+1 safe)
- `GET /reservations/{id}` → detail
- `PUT /reservations/{id}/confirm` → konfirmasi + set table.status='reserved' (Golden Rule #24)
- `PUT /reservations/{id}/cancel` → cancel + release table (Golden Rule #24)
- `PUT /reservations/{id}/complete` → complete + release table (Golden Rule #24)
- Semua WRITE: log_audit + optimistic lock row_version

### backend/api/routes/connect.py (TAMBAHAN)
- `GET /{slug}/tables` → meja status='available' untuk booking form
- `POST /{slug}/booking` → buat reservasi (tanpa login, validasi meja WITH FOR UPDATE, WA confirmation)
- `GET /bookings/{booking_id}` → status polling

### backend/api/api.py
- Tambah: `reservations.router` + `loyalty.router`

### app/actions/storefront.ts (TAMBAHAN)
- `getAvailableTables(slug)` + `createBooking(slug, data)` + `getBookingStatus(bookingId)`
- Mock fallback untuk semua 3 functions

### app/[slug]/booking/page.tsx (BARU)
- Form: nama, telepon, tanggal (min tomorrow), jam, jumlah tamu (counter), pilih meja, catatan
- Filter meja by guest_count >= capacity
- Submit → redirect ke /[slug]/booking/[id]

### app/[slug]/booking/[id]/page.tsx (BARU)
- Polling setiap 10 detik, stop saat confirmed/cancelled/completed
- Status visual: pending=kuning, confirmed=hijau, cancelled=merah, completed=abu
- WA contact button, back to menu

### app/[slug]/page.tsx (MODIFIED)
- Tombol "Reservasi Meja" muncul saat cart kosong + outlet is_open

### Feature D Fix (Loyalty):
- `backend/migrations/versions/059_loyalty_points.py` → customer_points + point_transactions
- `backend/models/loyalty.py` → CustomerPoints + PointTransaction
- `backend/api/routes/loyalty.py` → balance, earn (idempoten UNIQUE order+type), redeem (row_version lock), history

---

## CARA RESUME SESI BARU

Perintah untuk Claude di sesi baru:
> "baca claude.md, memory.md, session.md dulu lalu lanjut"

Claude harus:
1. Baca CLAUDE.md + MEMORY.md + SESSION.md
2. Lanjut Feature F: FASE 5 Pre-Pilot
