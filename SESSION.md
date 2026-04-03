# SESSION — 2026-04-03
# Claude update file ini otomatis tiap task selesai

## ✅ SELESAI SESI INI
- [x] Feature E: Reservasi + Booking via Connect (sesi sebelumnya)
- [x] Feature D fix: loyalty.py route + model + migration 059
- [x] Feature F: FASE 5 Pre-Pilot (Sentry, R2 APK upload, .env.example, kasira-setup.sh)

## 🎉 SEMUA FEATURE SELESAI — Siap VPS Deployment

---

## STATUS AKHIR SEBELUM DEPLOYMENT

### Branch aktif
```
claude/review-documentation-qqAkC
```

### Urutan deploy ke VPS
1. **Setup VPS** (Ubuntu 22.04):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/muhivan752/Kasira-OS-Intelligence/main/kasira-setup.sh | sudo bash
   ```
   Saat prompted isi: FONNTE_TOKEN, XENDIT_API_KEY, XENDIT_WEBHOOK_TOKEN, ANTHROPIC_API_KEY, SENTRY_DSN

2. **GitHub Secrets** (untuk build-apk.yml R2 upload):
   - R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL

3. **Build APK** — trigger `Build & Release Kasira Flutter APK` workflow di GitHub Actions
   - Isi version, is_mandatory, release_notes

4. **UptimeRobot** — setup monitor:
   - URL: http://VPS_IP:8000/ (backend health)
   - URL: http://VPS_IP:3000/ (frontend)

---

## FEATURE F — Summary yang Sudah Selesai

### Sentry Backend
- `backend/requirements.txt` — tambah `sentry-sdk[fastapi]>=2.0.0`
- `backend/core/config.py` — tambah `SENTRY_DSN: str = ""`
- `backend/main.py` — Sentry init (only if SENTRY_DSN set):
  - FastApiIntegration + SqlalchemyIntegration
  - traces_sample_rate=0.1, send_default_pii=False

### Sentry Next.js Frontend
- `package.json` — tambah `@sentry/nextjs ^8.0.0`
- `sentry.client.config.ts` — client init (Replay only on error, maskAllText)
- `sentry.server.config.ts` — server init
- `instrumentation.ts` — Next.js native hook (register() → import server config)
- `next.config.ts` — wrap `withSentryConfig` conditional on NEXT_PUBLIC_SENTRY_DSN

### APK ke Cloudflare R2 (build-apk.yml)
- Step baru: Upload APK ke R2 via awscli (S3-compatible)
  - `s3://{R2_BUCKET}/apk/kasira-pos-v{version}.apk`
  - `s3://{R2_BUCKET}/apk/kasira-dapur-v{version}.apk`
- Upload `version.json` ke R2 (Flutter baca saat startup):
  ```json
  {
    "pos": { "version", "is_mandatory", "download_url", "release_notes" },
    "dapur": { "version", "is_mandatory", "download_url", "release_notes" }
  }
  ```
- GitHub Secrets yang perlu diisi: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL

### .env.example
- Tambah: ANTHROPIC_API_KEY, SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN
- Tambah komentar R2 vars (untuk GitHub Secrets, bukan VPS .env)

### kasira-setup.sh
- Prompt baru saat setup: ANTHROPIC_API_KEY + SENTRY_DSN
- Generated .env sekarang include ANTHROPIC_API_KEY + SENTRY_DSN + NEXT_PUBLIC_SENTRY_DSN

### pg_dump cron — sudah benar di kasira-setup.sh
- Tiap 6 jam ke /var/backups/kasira/ — delete backup >7 hari
- Format: `kasira_YYYYMMDD_HHMM.sql.gz`

---

## CARA RESUME SESI BARU (jika ada bug/perlu perubahan)

> "baca claude.md, memory.md, session.md dulu lalu lanjut"

Semua feature sudah selesai. Sesi selanjutnya = debugging deploy atau tambah fitur baru.
