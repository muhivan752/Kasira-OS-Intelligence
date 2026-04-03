# SESSION — 2026-04-02
# Claude update file ini otomatis tiap task selesai

## ✅ SELESAI SESI INI
- [x] Feature D: Loyalty Points — backend + Flutter
- [x] Feature A: Flutter Dapur App — 8 layar kitchen display
- [x] Feature B: Kasira Connect Storefront — Xendit QRIS + QR display + bugfix
- [x] Feature C: AI Chatbot Owner — SSE streaming + intent classifier

## 🔴 LANJUT DARI SINI → Feature E: Reservasi + Booking

---

## CHECKPOINT LENGKAP — RESUME DARI SINI

### Branch aktif
```
claude/review-documentation-qqAkC
```
Last commit: `bbc1cfc` — "feat: Feature C — AI Chatbot Owner (SSE streaming)"

### Urutan priority fitur tersisa
```
E → F → VPS
```
1. **Feature E: Reservasi + Booking via Connect** ← NEXT
2. Feature F: FASE 5 Pre-Pilot (UptimeRobot, Sentry, APK ke R2, .env.example update)
3. VPS Deployment (kasira-setup.sh sudah siap)

---

## FEATURE E: RESERVASI + BOOKING — Detail Teknikal

### Konteks
- Tabel `reservations` sudah ada di DB (migration batch 4)
- Tabel sudah punya `row_version` (Rule #33: reservations WAJIB row_version)
- Golden Rule #24: Meja reserved otomatis saat connect_order confirmed → release saat done
- Golden Rule #23: ETA dine in disimpan di connect_orders.eta_minutes

### Yang harus dibuat:
```
backend/api/routes/reservations.py    ← CRUD reservasi (baru atau cek sudah ada)
app/[slug]/booking/page.tsx           ← Booking form di storefront (baru)
app/[slug]/booking/[id]/page.tsx      ← Booking status page (baru)
```

### File yang perlu dibaca sebelum coding Feature E:
1. `backend/models/reservation.py` (atau cek di models/) — struktur tabel
2. `backend/migrations/versions/027_reservations.py` — lihat kolom lengkap
3. `app/[slug]/` — lihat struktur existing untuk tahu cara tambah halaman baru
4. `backend/api/routes/connect.py` — connect order sudah ada, perlu tambah ETA + meja reserved
5. Check apakah `reservations` router sudah ada di `backend/api/api.py`

### Key fields reservations table (dari migration batch 4):
- id UUID, outlet_id, customer_id
- table_id (FK tables), reservation_date, start_time, end_time
- party_size, notes, status (pending/confirmed/cancelled/completed)
- row_version (Rule #33)
- connect_order_id (link ke connect_order jika booking via storefront)

### Endpoints yang dibutuhkan:
```
POST /reservations/           ← buat booking (guest bisa tanpa login)
GET  /reservations/{id}       ← status booking
PUT  /reservations/{id}/confirm  ← owner/kasir konfirmasi
PUT  /reservations/{id}/cancel   ← cancel
GET  /connect/{slug}/tables   ← available tables untuk storefront booking
```

### Frontend storefront (Next.js):
- Form: nama, telepon, tanggal, jam, jumlah orang, catatan
- Pilih meja (dari GET /connect/{slug}/tables)
- Konfirmasi via WA setelah submit
- Status page polling (booking pending/confirmed/cancelled)

---

## FEATURE C — Summary yang Sudah Selesai

### backend/services/ai_service.py (BARU)
- `get_model_for_tier(tier, task)` — Rule #25/#26
  → "claude-haiku-4-5-20251001" default
  → "claude-sonnet-4-6" hanya Pro+/complex
- `classify_intent(message)` — Rule #54/#56
  → READ: laporan/omzet/stok/penjualan/pelanggan
  → WRITE: tambah/hapus/ubah/ganti → blok, minta ke Settings app
  → UNKNOWN: tolak sopan
- `build_context(outlet_id, tenant_id, outlet_name, db, redis)` — Rule #27/#55
  → Cache Redis: `ai:context:{outlet_id}`, TTL sampai 00.00 WIB
  → Agregat: omzet hari ini, top 3 produk, 7 hari, stok kritis <5
  → Max ~800 token
- `stream_ai_response()` — AsyncGenerator SSE chunks
  → format: `data: {"type": "chunk/done/error", ...}\n\n`

### backend/api/routes/ai.py (BARU)
- `POST /ai/chat` → StreamingResponse text/event-stream
  → Auth required (get_current_user)
  → Validate outlet belongs to tenant
  → log_audit (Rule #2)
  → X-Accel-Buffering: no (nginx bypass untuk SSE)
- `DELETE /ai/context/{outlet_id}` → clear Redis cache manual

### backend/api/api.py
- Tambah: `api_router.include_router(ai.router, prefix="/ai", tags=["ai"])`

### backend/requirements.txt
- Tambah: `anthropic>=0.40.0`

### backend/core/config.py
- Tambah: `ANTHROPIC_API_KEY: str = ""`

### .env.example (perlu ditambah di sesi berikutnya)
- `ANTHROPIC_API_KEY=sk-ant-...`

---

## CATATAN PENTING
- `loyalty.py` route file tidak ada di filesystem (mungkin tidak pernah dibuat atau hilang)
  → Perlu dicek dan dibuat ulang jika Feature D (Loyalty) sudah ada di MEMORY.md
  → File yang perlu dicek: `backend/api/routes/loyalty.py`
- `backend/api/api.py` tidak include loyalty router → perlu ditambah juga

---

## CARA RESUME SESI BARU

Perintah untuk Claude di sesi baru:
> "baca claude.md, memory.md, session.md dulu lalu lanjut"

Claude harus:
1. Baca CLAUDE.md + MEMORY.md + SESSION.md
2. Cek apakah loyalty.py exists, jika tidak buat ulang
3. Lanjut Feature E: Reservasi
