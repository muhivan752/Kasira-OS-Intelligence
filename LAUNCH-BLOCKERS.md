# Kasira Launch Blockers

**Target launch**: minggu 2026-04-20 s/d 2026-04-26
**Audit date**: 2026-04-18
**Auditor**: multi-agent (Explore security + stock/sync-auditor + manual review)
**Current readiness**: ~75%

---

## 🚨 P0 — SHIP BLOCKER (wajib fix sebelum launch)

Fokus di D1-D3 (sebelum weekend berakhir).

### 1. OpenAPI docs publicly accessible
- **Verified**: `curl https://kasira.online/api/v1/openapi.json` returns **200** — full API schema + endpoint enumeration exposed
- **Risk**: attacker map semua endpoint, parameter, auth flow
- **Fix**: `backend/main.py:69` — conditional disable:
  ```python
  openapi_url=None if settings.ENVIRONMENT == "production" else f"{settings.API_V1_STR}/openapi.json",
  docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
  redoc_url=None,
  ```
- **Effort**: 5 menit

### 2. OTP rate limit = SMS bomb vector
- **File**: `backend/api/routes/auth.py:60` — threshold `>= 10` per 15 menit
- **Risk**: attacker flood victim's WA dengan 40 OTP/jam. Cost Kasira via Fonnte + bad UX victim
- **Fix**: threshold 10 → **3**, TTL 900s → 1800s, add exponential backoff
- **Effort**: 15 menit

### 3. Global rate limiting missing
- **File**: `backend/main.py` — no slowapi/middleware rate limiter
- **Risk**: DDoS, payment webhook overload, cost bomb via AI endpoint abuse
- **Fix**: install `slowapi`, middleware all `/api/*`:
  - Public (auth, webhook): 100 req/min per IP
  - Authenticated: 1000 req/min per user
- **Effort**: 1-2 jam (include testing)

### 4. Xendit webhook signature weak
- **File**: `backend/services/xendit.py:135-137` — token string equality only
- **Risk**: attacker replay/forge webhook → create phantom payment status → gratis order
- **Fix**: HMAC-SHA256 validation dgn `x-xendit-timestamp` + 5-min tolerance
- **Effort**: 1 jam

### 5. Privacy Policy + ToS missing (LEGAL)
- **File**: gak ada di `app/` — `find` returns empty untuk `privacy/terms/legal`
- **Risk**: **UU PDP non-compliance**. Wajib ada consent, data subject rights, deletion procedure
- **Fix**: bikin `app/privacy/page.tsx` + `app/terms/page.tsx` + link di footer/register/onboarding
- **Effort**: 3-4 jam (kalau draft dari template + localize)

### 6. Xendit API key plaintext di DB
- **File**: `backend/models/outlet.py` — `xendit_api_key` column raw string
- **Risk**: DB breach = semua merchant Xendit key leak → fraud cross-merchant
- **Fix**: encrypt pakai existing `ENCRYPTION_KEY` (AES-256). Butuh migration buat encrypt existing rows
- **Effort**: 2-3 jam (include migration)

---

## ⚠️ P1 — STRONGLY RECOMMENDED

Bisa launch tanpa ini tapi resiko, fix sebelum onboard >10 tenant real.

| Issue | File | Effort |
|---|---|---|
| JWT expiry 8 hari → 1 hari | `config.py:41` `ACCESS_TOKEN_EXPIRE_MINUTES` | 10 min |
| `MASTER_OTP` bypass — enforce disabled di prod | `config.py:50` + startup check | 15 min |
| Remove hardcoded defaults (SECRET_KEY, POSTGRES_PASSWORD) — even kalau runtime override, gak boleh ada di git | `config.py:13-14, 39` + startup validation | 30 min |
| Restore from R2 backup **belum pernah dites** | `scripts/` — add `restore_r2.sh` + doc procedure | 1 jam |
| Payment webhook idempotency guard verify actually used | `payments.py:365-367` | 30 min |
| CORS tighten: `localhost:3000` di prod `.env` → hapus | `.env` runtime | 2 min |
| Load test sebelum public launch (k6/Locust) | new script | 2-3 jam |
| Sentry verify actually catching — trigger intentional 500 test | manual | 15 min |
| Startup config validation: reject defaults in production | `config.py` + `main.py` startup | 45 min |

---

## 💡 P2 — POST-LAUNCH (bisa tunda)

- PII redaction di AI context/prompts (Rule #54 compliance)
- Uvicorn workers 2 → 4 (Dockerfile)
- DB connection pool tuning + `statement_timeout=30s`
- IP whitelist superadmin endpoints
- Encryption key rotation mechanism
- Audit log untuk semua payment webhook event
- File upload virus scan integration
- Frontend layer security audit (separate pass)

---

## ✅ CLEAN — Udah solid, gak perlu action

| Aspek | Evidence |
|---|---|
| SQL injection | SQLAlchemy ORM + Pydantic everywhere, no raw SQL string interpolation |
| Password hashing | bcrypt via `CryptContext` |
| Row-Level Security (RLS) | PostgreSQL RLS via `app.current_tenant_id` (migration 069) |
| Token blacklist on logout | Redis blacklist checked in `get_current_user` |
| JWT secret runtime | 64-char custom in `.env`, NOT default |
| POSTGRES_PASSWORD runtime | Custom in `.env`, NOT `"postgres"` |
| CORS production origins | `kasira.online` + `www.kasira.online` set in `.env` |
| SSL cert | Let's Encrypt valid **until 2026-07-14** (~3 bulan buffer) |
| Sentry error tracking | DSN configured, initialized conditionally in `main.py` |
| Xendit production mode | `XENDIT_IS_PRODUCTION=true` |
| Input validation | Pydantic schemas dengan `ge=0, min_length, max_length` |
| Stock logic correctness | Post-fix 2026-04-18 (commit 6f2da0a + a22cb36) |
| Sync CRDT correctness | Post-fix 2026-04-18 (commit fe65c13 — cross-tenant leak patched) |
| Tier gating consistency | Post-fix 2026-04-18 (commit 59d5fbf) |
| Backup to R2 | Cron 6 jam, verified running (latest 2026-04-18 06:00 UTC, 148.9 KB) |
| Tenant isolation | `get_current_tenant` + RLS + filter_kwargs (fixed order_items + cash_activities) |
| CI/CD | GitHub Actions Build APK workflow 3x consecutive success |
| Storefront idempotency | `connect_orders.idempotency_key` required + unique |
| Event sourcing | append-only events table, idempotency guard di stock_service + ingredient_stock_service |

---

## 📋 Launch Timeline Proposed

| Hari | Task |
|---|---|
| **Sabtu 04-18** (hari ini) | ✅ Security audit done. Launch-blockers identified. Start P0 #1-#3 (code-only, gak butuh legal review) |
| **Minggu 04-19** | P0 #4 (Xendit HMAC) + P0 #6 (Xendit encryption). Mulai draft P0 #5 (privacy/ToS) |
| **Senin 04-20** | Finalisasi privacy/ToS + publish. P1 items (JWT expiry, MASTER_OTP, defaults cleanup) |
| **Selasa 04-21** | Restore backup test + load test (k6 target 500 concurrent). Sentry intentional-500 test |
| **Rabu 04-22** | Buffer day — fix apapun yg ketemu di load test. Re-audit via agents |
| **Kamis 04-23** | Final smoke test + dokumen launch (press release, WA broadcast ke waitlist) |
| **Jumat 04-24** | Soft launch (5-10 beta tenant, invite-only) |
| **Senin 04-27** | Public launch kalau soft launch sukses |

**Total P0 effort**: ~12-15 jam code + 3-4 jam legal = **~2 hari full focus**
**Total P1 effort**: ~6-8 jam = **1 hari**
**Buffer untuk test + polish**: **2-3 hari**

Fit dengan 1 minggu target, TAPI perlu Ivan full focus di P0 Sabtu-Senin.

---

## 🎯 Decision Points untuk Ivan

Gw gak bisa decide, lo yg mesti jawab:

1. **Privacy Policy + ToS**: mau pake template + konsul lawyer cepet? Atau punya draft sendiri?
2. **Load test target**: berapa concurrent user realistic? 100? 500? 1000?
3. **Soft launch size**: beta tester ada list siap dipanggil?
4. **Onboarding flow polish**: lo udah test end-to-end pake akun Dita? Kalau belum, itu P0 tambahan
5. **WA bot suspend/remind (Rule #52)**: H-7 → H-3 → H+7 workflow udah live atau belum?

---

## Next Step Rekomendasi

Saran gw mulai P0 #1, #2, #3 sekarang (total ~2-3 jam) — technical only, gak butuh lo decide apapun. Sisanya (#4, #5, #6) butuh pertimbangan + legal.

Mau gw gas P0 #1-3?
