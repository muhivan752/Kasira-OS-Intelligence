# KASIRA — Disaster Recovery Runbook

**Scenario:** Vultr VPS mati total (hardware failure, hack, terhapus, dll). Business harus online lagi dalam <1 jam.

**Target Recovery Objectives:**
- **RTO** (Recovery Time Objective): 60 menit dari deteksi server mati → kasira.online live
- **RPO** (Recovery Point Objective): 6 jam max (backup R2 cron interval)

---

## Backup Infrastructure (Sudah Jalan)

| Asset | Storage | Interval | Retention |
|---|---|---|---|
| PostgreSQL dump (`kasira_db`) | Cloudflare R2 `s3://kasira-production/backups` | 6 jam | 14 hari |
| PostgreSQL dump (local) | `/var/backups/kasira` | 6 jam | 7 hari |
| Code | GitHub `muhivan752/Kasira-OS-Intelligence` | Per push | Unlimited |
| `.env` credentials | ⚠ **Manual — simpan aman di 1Password/password manager** | — | — |

**Format backup:** `kasira_db_YYYYMMDD_HHMMSS.sql.gz`
**R2 endpoint:** `https://63003661b5b663860000bcf6e9dc4955.r2.cloudflarestorage.com`

---

## STEP 1 — Provisioning VPS Baru di Vultr

**Target spec (match Kasira production):**
- **Location:** Singapore (latency terendah ke Indonesia)
- **Plan:** Cloud Compute 2 vCPU / 4GB RAM / 80GB SSD (minimum)
- **OS:** Ubuntu 22.04 LTS
- **Estimated cost:** $24/bulan

**Langkah:**

1. Login Vultr dashboard → Deploy New Server
2. Pilih **Cloud Compute → Regular Performance**
3. Location: **Singapore (Johore area)**
4. OS: **Ubuntu 22.04 LTS x64**
5. Plan: minimum **2vCPU / 4GB / 80GB SSD**
6. Tambah SSH key dari laptop:
   ```bash
   cat ~/.ssh/id_ed25519.pub  # copy ke Vultr SSH Keys
   ```
7. Enable **Auto Backup** di Vultr (optional, jadi layer 2 redundancy)
8. Deploy → tunggu ~60 detik → **catat IP address baru**

**Validasi:**
```bash
ssh root@<NEW_IP>
uname -a  # Ubuntu 22.04
nproc      # ≥2
free -h    # ≥4GB
df -h      # ≥80GB
```

---

## STEP 2 — Install Dependencies

Run semua ini di VPS baru sbg **root** (atau sudo):

### 2.1 Update system
```bash
apt update && apt upgrade -y
apt install -y curl git htop vim unzip ca-certificates gnupg
```

### 2.2 Docker + Docker Compose
```bash
# Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Enable + start
systemctl enable docker
systemctl start docker

# Docker Compose plugin (v2)
apt install -y docker-compose-plugin

# Verify
docker --version            # should be ≥24.0
docker compose version      # v2.x
```

### 2.3 AWS CLI (untuk R2 restore)
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscli.zip
cd /tmp && unzip awscli.zip
./aws/install
rm -rf /tmp/aws /tmp/awscli.zip

# Verify
aws --version  # aws-cli/2.x
```

### 2.4 Configure AWS R2 profile
Siapkan R2 credentials dari Cloudflare dashboard (Access Key + Secret) — **ambil dari 1Password** atau Cloudflare R2 → API Tokens:

```bash
aws configure --profile r2
# AWS Access Key ID: <paste R2 access key>
# AWS Secret Access Key: <paste R2 secret>
# Default region: auto
# Default output format: json
```

Test:
```bash
aws s3 ls s3://kasira-production/backups/ \
    --endpoint-url https://63003661b5b663860000bcf6e9dc4955.r2.cloudflarestorage.com \
    --profile r2
# Should list backup files
```

### 2.5 (Opsional) Python 3.11 + uv untuk dev/debug
```bash
apt install -y python3.11 python3.11-venv python3-pip
```
Tidak strictly needed — Kasira backend jalan di Docker, tidak perlu Python host-level.

---

## STEP 3 — Restoration

### 3.1 Clone repo
```bash
cd /var/www  # atau path favorit
git clone https://github.com/muhivan752/Kasira-OS-Intelligence.git kasira
cd kasira
```

### 3.2 Setup `.env`
**KRITIKAL** — tanpa `.env` yg benar, backend gak bisa decrypt Xendit keys + sign JWT.

Ambil `.env` dari 1Password / backup credential lo:
```bash
# Paste isi .env original — JANGAN commit
vim .env
```

Minimum wajib set:
```ini
# Database
POSTGRES_USER=kasira
POSTGRES_PASSWORD=<from 1password>
POSTGRES_DB=kasira_db
DATABASE_URL=postgresql+asyncpg://kasira:<pass>@db:5432/kasira_db

# Redis
REDIS_URL=redis://redis:6379/0

# Security (WAJIB SAMA DGN ORIGINAL biar JWT + encrypted data decrypt)
SECRET_KEY=<from 1password — 32+ char>
ENCRYPTION_KEY=<from 1password — 44 char base64 urlsafe untuk AES-256>
# ⚠ ENCRYPTION_KEY BEDA = semua xendit_api_key di DB gak bisa di-decrypt!

# Xendit
XENDIT_API_KEY=<from 1password>
XENDIT_WEBHOOK_TOKEN=<from 1password>

# Fonnte (WA)
FONNTE_TOKEN=<from 1password>

# Anthropic (AI)
ANTHROPIC_API_KEY=<from 1password>

# Production flags
ENVIRONMENT=production
SUPERADMIN_PHONES=6285270782220  # Ivan

# Frontend URLs (sesuaikan kalau domain berubah)
BACKEND_INTERNAL_URL=http://backend:8000/api/v1
NEXT_PUBLIC_API_URL=https://kasira.online/api/v1
BACKEND_CORS_ORIGINS=["https://kasira.online"]
```

### 3.3 Start database container (TANPA backend dulu)
```bash
docker compose up -d db redis
sleep 10

# Verify DB ready
docker exec kasira-db-1 pg_isready -U kasira
```

### 3.4 Jalankan restore script
```bash
sudo ./scripts/restore_db.sh --list  # cek available backups
sudo ./scripts/restore_db.sh          # pakai backup TERBARU
# Atau specify timestamp: sudo ./scripts/restore_db.sh 20260419_0600
```

Script akan:
1. Validate AWS CLI + R2 connection + Docker
2. Download backup ke `/tmp/kasira_restore_XXX/`
3. Verify gzip integrity
4. Prompt konfirmasi **2x** (ketik `yes` + ketik nama file)
5. Drop + create `kasira_db`
6. Inject data via `psql`
7. Validate tenants, orders, payments count + RLS + alembic version

Kalau restore sukses, output terakhir:
```
✓ RESTORE COMPLETE
```

### 3.5 Start full stack
```bash
docker compose up -d

# Wait for healthcheck
sleep 15
docker ps

# Run any missing migrations (edge case — backup from older version)
docker exec kasira-backend-1 alembic upgrade head

# Restart backend to reload cache
docker restart kasira-backend-1
```

---

## STEP 4 — DNS Switch di Cloudflare

Kasira pakai Cloudflare untuk DNS + CDN + WAF.

### 4.1 Login Cloudflare Dashboard
https://dash.cloudflare.com → pilih domain `kasira.online`

### 4.2 Update A record
- Navigate: **DNS → Records**
- Cari record `A` untuk `@` atau `kasira.online` dan `api.kasira.online` (kalau ada)
- Edit → ganti **IPv4 address** dari IP lama ke IP VPS baru
- Save (propagation langsung, TTL default 5 menit)

### 4.3 Verify propagation
```bash
# Dari laptop:
dig +short kasira.online
dig +short api.kasira.online
# Harus return IP VPS baru
```

**Catatan:** DNS proxied via Cloudflare (orange cloud) biasanya update <1 menit karena Cloudflare edge cache. Kalau bypass proxy (grey cloud), user downstream mungkin cache 5-10 menit.

---

## STEP 5 — Validation

### 5.1 Basic health
```bash
curl https://kasira.online/health
# Expected: {"status":"ok","db":"ok","bg_tasks":"healthy","bg_tasks_dead":[]}
```

### 5.2 Detailed bg task health
```bash
curl https://kasira.online/health/background | python3 -m json.tool
# Expected: 7 tasks, semua state="running" alive=true
```

### 5.3 Prometheus metrics
```bash
curl https://kasira.online/metrics | grep kasira_bg
# Expected: kasira_bg_tasks_alive{task="..."} 1.0 untuk semua 7 task
```

### 5.4 API smoke test (auth + protected endpoint)
```bash
# Health public ok
curl https://kasira.online/api/v1/auth/app/version
# Expected: {"version":"1.0.X", ...}

# Try login via WA OTP — dari Flutter app atau Postman
```

### 5.5 Data integrity check
```bash
sudo docker exec kasira-db-1 psql -U kasira -d kasira_db <<'SQL'
SELECT
  (SELECT COUNT(*) FROM tenants) AS tenants,
  (SELECT COUNT(*) FROM outlets) AS outlets,
  (SELECT COUNT(*) FROM orders) AS orders,
  (SELECT COUNT(*) FROM payments) AS payments,
  (SELECT version_num FROM alembic_version) AS alembic;
SQL
```

Compare dengan count terakhir yg lo tau (kalau punya metrics histori di Prometheus/Grafana old).

### 5.6 RLS sanity check
```bash
sudo docker exec kasira-db-1 psql -U kasira -d kasira_db -c \
  "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND rowsecurity=true;"
# Expected: 56 (per migration 069)
```

### 5.7 Critical workflow end-to-end (manual via Flutter app)
1. Login via OTP WA (test Fonnte working)
2. Create order di POS → pay QRIS (test Xendit working)
3. Sync Flutter offline order (test sync engine working)

---

## Rollback Plan (Kalau Restore Gagal)

**Kalau restore ke VPS baru gagal tapi VPS lama masih sebagian jalan:**
1. Jangan switch DNS ke VPS baru — biar traffic tetap ke VPS lama
2. Debug di VPS baru sampai issue resolved
3. Re-run `./scripts/restore_db.sh` dgn backup yg lebih baru

**Kalau VPS lama mati total dan restore gagal:**
1. Contact Vultr support untuk recover snapshot VPS lama (mungkin <24 jam window)
2. Alternative: pakai backup di `/var/backups/kasira` VPS lama kalau VPS masih bisa SSH

---

## Post-Recovery — Catatan Operasional

Setelah sistem live lagi:

1. **Monitor log 1 jam pertama:**
   ```bash
   sudo docker logs kasira-backend-1 -f | grep -iE "error|critical|exception"
   ```

2. **Verify cron backup jalan lagi:**
   ```bash
   # Tambahkan kembali cron backup_r2.sh di /etc/cron.d/
   cat > /etc/cron.d/kasira-backup-r2 <<EOF
   0 */6 * * * root /var/www/kasira/scripts/backup_r2.sh
   EOF
   ```

3. **Cek Xendit payment flow** (critical — merchant loss kalau payment broken):
   - Buat test order QRIS via Flutter
   - Verify webhook callback `POST /api/v1/payments/webhook/xendit` processed
   - Check `/metrics | grep kasira_xendit_calls_total`

4. **Verify sync Flutter** dari minimum 1 device (kasir app):
   - Force sync → `/sync/` endpoint
   - Check `/metrics | grep kasira_sync_records_total`

5. **WA notification test:**
   ```bash
   # Test Fonnte masih kirim OTP
   sudo docker exec kasira-backend-1 python -c "
   import asyncio
   from backend.services.fonnte import send_whatsapp_message
   print(asyncio.run(send_whatsapp_message('6285270782220', 'Kasira recovery test — sistem live')))
   "
   ```

6. **Update status di memory/project docs:**
   - Record restoration timestamp
   - Note any data gap (kalau backup bukan yg TERBARU)
   - Review impacted orders (jeda antara last-backup → recovery)

---

## RLS + HLC Integrity Setelah Restore

**RLS (Row Level Security):**
- Policy di-store sbg DDL object di database — ikut ke-backup lewat `pg_dump`
- Setelah restore, verify: `\d+ <table>` harus show policy `tenant_isolation`
- Force row security: `SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'orders';`
- Kalau RLS hilang: run `alembic upgrade head` (migration 069 re-create policy)

**HLC (Hybrid Logical Clock):**
- HLC di-derive dari `updated_at` + `row_version` (existing columns)
- Restore preserve semua ini intact — HLC generation logic server-side (`HLC.generate()` + `server_node_id`) auto-restart dari physical clock baru
- **Potential issue:** Kalau clock VPS baru mundur dari terakhir active (misal timezone salah), HLC bisa jitter. Fix: `timedatectl set-ntp on` + verify `date -u` accurate
- Flutter client punya HLC cache sendiri — saat sync pertama setelah restore, `HLC.receive()` akan merge client HLC dgn server → no data loss

---

## Runbook Drill Schedule

Monthly drill (quarterly min):
1. Deploy ephemeral Vultr instance ($5/bulan cheapest plan)
2. Run full recovery step 1-5
3. Time each step, record di spreadsheet
4. Teardown instance
5. Update runbook ini kalau ada surprise

Goal: RTO <60 menit tercapai konsisten. Kalau step takes >15 menit, automate lebih jauh.

---

## Appendix — File Reference

| File | Purpose |
|---|---|
| `scripts/backup_r2.sh` | Cron backup pg_dump → R2 (every 6h) |
| `scripts/restore_db.sh` | **THIS TASK (#9)** — restore dari R2 ke fresh DB |
| `docker-compose.yml` | Service definitions (backend, db, redis, frontend) |
| `backend/migrations/versions/069_rls_and_indexes.py` | RLS policies + 18 indexes |
| `.env` | Secrets (NOT in git — ambil dari 1Password) |

---

**Status:** ✅ CRITICAL #9 RESOLVED
**Last drill:** _never_ — schedule first drill within 2 weeks of this doc.
**Owner:** Ivan (muhivan752@gmail.com)
