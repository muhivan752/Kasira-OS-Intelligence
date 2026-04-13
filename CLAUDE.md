# KASIRA — Claude Entry Point
# Baca file ini PERTAMA sebelum apapun

## Project
Kasira = POS + Pilot Otomatis + AI untuk cafe Indonesia
Stack: FastAPI + PostgreSQL + Flutter + Next.js 14 + Redis + Claude API

## Wajib Baca Sebelum Coding
- **ARCHITECTURE.md → WAJIB BACA kalau menyentuh stock, recipe, tab, storefront, atau sync**
- ROADMAP.md → Master Plan & Build Order (WAJIB SESUAI FASE)
- MEMORY.md → status terkini + keputusan teknikal
- skills/{domain}/SKILL.md → conventions domain yang relevan

---

## GOLDEN RULES — Dikelompokkan per Domain

### 🗄️ DATA LAYER
| # | Rule |
|---|------|
| 1 | UUID untuk semua PK — TIDAK BOLEH integer auto-increment |
| 7 | Soft delete via `deleted_at`, TIDAK BOLEH hard delete |
| 8 | Event store append-only — TIDAK BOLEH update/delete event yang sudah ada |
| 29 | SEMUA tabel kritikal WAJIB `row_version` — products, customer_points, outlet_stock, tables, subscriptions, invoices |
| 30 | Optimistic lock: `UPDATE ... WHERE row_version = :expected` → kalau `rows_affected=0` → **retry max 3x** → baru error |
| 47 | `CHECK (stock_qty >= 0)` dan `CHECK (computed_stock >= 0)` — wajib di DB level, bukan hanya aplikasi |

### 🌐 API LAYER
| # | Rule |
|---|------|
| 2 | Setiap WRITE endpoint WAJIB tulis audit log — tidak ada pengecualian |
| 3 | Response format wajib: `{success, data, meta, request_id}` |
| 4 | Schema-per-tenant: `SET search_path TO {tenant_id}` di awal setiap request |
| 5 | Idempotency key wajib untuk semua payment endpoint |
| 6 | Timezone: simpan UTC di DB, tampilkan Asia/Jakarta ke user |
| 9 | FastAPI async ONLY — tidak boleh ada sync blocking call |
| 10 | Test sebelum commit — kalau ragu, tanya dulu |

### 🔐 AUTH
| # | Rule |
|---|------|
| 11 | Auth WAJIB via OTP WA — tidak ada email+password |
| 12 | JWT: httpOnly cookie (web), Flutter SecureStorage (mobile) |
| 13 | OTP expire 5 menit, max 3x resend per 15 menit |

### 📦 STOCK
| # | Rule |
|---|------|
| 19 | Starter = transaction-first: stok deduct otomatis dari transaksi. Restock manual HANYA saat terima barang — bukan input harian bebas |
| 20 | Stok = 0 → produk auto-hidden di kasir DAN storefront **serentak** |
| 28 | `order_display_number` WAJIB dari PostgreSQL SEQUENCE — TIDAK BOLEH `MAX()+1` |

### 💳 PAYMENT
| # | Rule |
|---|------|
| 31 | Payment endpoint WAJIB `SELECT FOR UPDATE` — tidak boleh concurrent payment processing |
| 32 | Redis distributed lock = DEFER — row_version cukup sampai ada evidence contention >500 outlet aktif |
| 34 | `connect_orders` WAJIB `idempotency_key` — storefront double submit via slow connection |
| 35 | `point_transactions` WAJIB `UNIQUE(order_id, type)` — double points = trust hancur |
| 36 | Payment error JANGAN tampilkan error teknis ke kasir — selalu human friendly |
| 37 | QRIS gagal → otomatis muncul tombol fallback cash — tidak perlu restart |
| 38 | Payment reconciliation Celery tiap 5 menit — pending >10 menit = auto-resolve |
| 39 | Semua payment event WAJIB masuk audit_log walau gagal |
| 40 | `payments.status` ENUM: `pending/paid/partial/expired/cancelled/refunded/failed` — tidak boleh string bebas |
| 41 | QRIS `expired_at` = `created_at + 15 menit` — Celery auto-expire kalau lewat |
| 42 | Refund > threshold WAJIB approval owner/manager — kasir tidak bisa refund sembarangan |
| 43 | `partial_payments` = Pro+ only — linked ke tab/bon feature |
| 44 | `xendit_raw` (JSONB) WAJIB disimpan — untuk debug kalau ada dispute |

### 🤖 AI
| # | Rule |
|---|------|
| 25 | Claude API model dipilih via `get_model_for_tier(tier, task)` — tidak pernah hardcoded |
| 26 | Starter + rutin task = Haiku — Sonnet hanya Pro+ untuk task kompleks |
| 27 | 3 optimasi wajib: batching (1 jam), cache (sampai 00.00 WIB), compress context (agregat bukan raw) |
| 54 | AI intent WAJIB classified dulu, WRITE butuh konfirmasi owner |
| 55 | System prompt max 800 token context agregat, di-cache Redis 5 menit |
| 56 | UNKNOWN intent = tolak sopan, jangan hallucinate di luar konteks bisnis |

### 📱 MOBILE (Flutter)
| # | Rule |
|---|------|
| 14 | APK hosted di Cloudflare R2 (atau GitHub Releases), cek versi setiap app dibuka |
| 15 | `is_mandatory=true` → force update, block app sampai update |
| 49 | Printer disconnect = TIDAK BOLEH block transaksi — queue struk di SQLite |
| 50 | Printer retry max 3x delay 2 detik, setelah itu queue `pending_receipts` |

### 🛒 CONNECT / STOREFRONT
| # | Rule |
|---|------|
| 16 | Kasira Connect: zero komisi selamanya — tidak ada negosiasi |
| 17 | Semua tier dapat storefront Connect dari hari pertama |
| 18 | Trust badge didapat dari track record — tidak bisa dibeli |
| 21 | Storefront otomatis aktif saat outlet register — slug = nama outlet lowercase |
| 22 | `connect_orders` WAJIB link ke `orders` table — satu sumber kebenaran |
| 23 | ETA dine in disimpan di `connect_orders.eta_minutes` — kitchen display pakai untuk countdown |
| 24 | Meja reserved otomatis saat connect_order confirmed — release saat status=done |
| 33 | `reservations` WAJIB `row_version` — double booking via Connect = real problem |

### 🏢 BISNIS / SLA
| # | Rule |
|---|------|
| 45 | pg_dump ke R2 WAJIB jalan sebelum pilot — cron tiap 6 jam |
| 46 | Backup testing tiap 2 minggu — catat di MEMORY.md |
| 48 | Disaster recovery target: VPS down < 2 jam, DB corrupt < 1 jam |
| 51 | Upgrade tier = efektif hari itu setelah Ivan konfirmasi manual |
| 52 | Suspend flow: H-7 WA → H-3 WA → H+7 suspend → H+60 scheduled deletion |
| 53 | Data retention setelah suspend: 60 hari aktif + 90 hari backup R2 |
