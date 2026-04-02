# SESSION — 2026-04-02
# Claude update file ini otomatis tiap task selesai

## ✅ SELESAI SESI INI
- [x] Feature D: Loyalty Points — backend + Flutter
- [x] Feature A: Flutter Dapur App — 8 layar kitchen display
- [x] Feature B: Kasira Connect Storefront — Xendit QRIS + QR display + bugfix

## 🔴 LANJUT DARI SINI → Feature C: AI Chatbot Owner

---

## CHECKPOINT LENGKAP — RESUME DARI SINI

### Branch aktif
```
claude/review-documentation-qqAkC
```
Last commit: `cc54d4e` — "fix: 4 bugs di Feature B Connect Storefront"

### Urutan priority fitur tersisa
```
C → E → F → VPS
```
1. **Feature C: AI Chatbot Owner** ← NEXT
2. Feature E: Reservasi + Booking via Connect
3. Feature F: FASE 5 Pre-Pilot (UptimeRobot, Sentry, APK ke R2)
4. VPS Deployment (kasira-setup.sh sudah siap)

---

## FEATURE C: AI CHATBOT OWNER — Detail Teknikal

### Yang harus dibuat (semuanya BARU):
```
backend/api/routes/ai.py          ← endpoint POST /ai/chat (SSE stream)
backend/services/ai_service.py    ← logic: model selector, intent, context builder
backend/api/api.py                ← include ai router
```

### Golden Rules yang berlaku untuk Feature C:
- Rule #25: Claude API model dipilih via get_model_for_tier(tier, task) — TIDAK BOLEH hardcoded
- Rule #26: Starter + rutin task → Haiku | Sonnet hanya Pro+ untuk task kompleks
- Rule #27: 3 optimasi WAJIB:
  1. Batching context (agregat per 1 jam, bukan raw rows)
  2. Cache system prompt di Redis (sampai 00.00 WIB)
  3. Compress context (kirim agregat, BUKAN raw transaksi)
- Rule #54: AI intent WAJIB classified dulu, WRITE butuh konfirmasi owner
- Rule #55: System prompt max 800 token context agregat, di-cache Redis 5 menit
- Rule #56: UNKNOWN intent = tolak sopan, jangan hallucinate di luar konteks bisnis
- Rule #2: Setiap WRITE endpoint WAJIB tulis audit log
- Rule #9: FastAPI async ONLY

### Spesifikasi teknikal:

#### 1. Intent Classifier
```python
INTENTS = {
    "READ": ["laporan", "omzet", "penjualan", "stok", "produk terlaris", "pelanggan"],
    "WRITE": ["tambah", "ubah", "hapus", "update", "ganti harga"],
    "UNKNOWN": # semua di luar konteks bisnis cafe/restoran
}
```
- WRITE → return response: "Apakah Anda yakin ingin [action]? Ketik YA untuk konfirmasi"
- UNKNOWN → tolak sopan: "Maaf, saya hanya bisa membantu pertanyaan seputar bisnis Anda"

#### 2. Model Selector
```python
def get_model_for_tier(tier: str, task: str) -> str:
    if tier in ('pro', 'enterprise') and task == 'complex':
        return "claude-sonnet-4-6"  # Rule #26
    return "claude-haiku-4-5-20251001"  # Default Starter/rutin
```

#### 3. Context Builder (max 800 token, Rule #55)
```python
async def build_context(outlet_id, tenant_id, db, redis) -> str:
    # Cache key: f"ai:context:{outlet_id}"
    # TTL: sampai 00.00 WIB = hitung detik sampai tengah malam Asia/Jakarta
    # Content (AGREGAT, bukan raw):
    # - Nama outlet, tier, jam buka
    # - Omzet hari ini (total Rp, jumlah transaksi)
    # - Top 3 produk terlaris hari ini
    # - Stok kritis (< 5 unit)
    # - Ringkasan 7 hari terakhir (omzet, trend naik/turun)
```

#### 4. SSE Streaming Endpoint
```python
@router.post("/chat")
async def ai_chat(
    request: ChatRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> StreamingResponse:
    # 1. classify intent
    # 2. if UNKNOWN → return SSE dengan pesan tolak
    # 3. if WRITE → return SSE dengan konfirmasi
    # 4. build context (dari cache Redis atau query DB)
    # 5. call Claude API stream
    # 6. yield SSE chunks
    # 7. audit log (Rule #2)
```

#### 5. Request/Response schema
```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # untuk multi-turn

# SSE format:
# data: {"type": "chunk", "content": "..."}
# data: {"type": "done", "tokens_used": 123}
# data: {"type": "error", "message": "..."}
```

#### 6. Claude API call
```python
import anthropic
client = anthropic.AsyncAnthropic()

async with client.messages.stream(
    model=get_model_for_tier(user.tier, classify_task(message)),
    max_tokens=1024,
    system=system_prompt,  # max 800 token
    messages=[{"role": "user", "content": message}],
) as stream:
    async for text in stream.text_stream:
        yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"
```

### File yang perlu dibaca sebelum coding Feature C:
1. `backend/api/api.py` — untuk include router baru
2. `backend/api/deps.py` — untuk get_current_user + get_db
3. `backend/api/routes/reports.py` — untuk memahami query omzet yang sudah ada
4. `backend/services/redis.py` — untuk caching pattern yang sudah dipakai
5. `backend/core/config.py` — untuk ANTHROPIC_API_KEY config

### Package yang mungkin perlu ditambah ke requirements.txt:
- `anthropic` — Claude API SDK (cek dulu apakah sudah ada)

---

## SUMMARY FEATURE B — Apa yang Sudah Selesai

### backend/api/routes/connect.py
- Hapus Midtrans, pakai Xendit QRIS
- `xendit_service.create_qris_transaction(reference_id=f"{tenant_id}::{payment_id}", ...)`
- Tambah `payment_method` field di `ConnectOrderInput` (default: 'qris')
- Cash: status langsung paid, order ke 'preparing'
- POST response include: `payment: { method, status, qris_url, qris_expired_at }`
- GET /orders/{order_id}: return full data (items, outlet, payment)

### backend/api/routes/payments.py (webhook)
- Setelah order confirmed → query ConnectOrder → set status = 'accepted'

### app/[slug]/cart/page.tsx
- Redirect: `res.data.id` → `res.data.order_id` (BUG FIX)
- Tambah `idempotency_key` di payload (Golden Rule #34)
- Item field: `quantity` → `qty` (sesuai backend schema)

### app/[slug]/order/[id]/page.tsx
- State: qrisUrl, qrisExpiredAt, qrisCountdown
- QRIS display: render via `api.qrserver.com` (bukan img src langsung dari qr_string)
- Countdown MM:SS, merah saat < 60 detik
- Polling berhenti saat status = completed/cancelled/failed

### app/actions/storefront.ts
- Error handling real (bukan silently fallback ke mock)
- Mock data include payment object lengkap

---

## CARA RESUME SESI BARU

Ketika mulai sesi baru, Claude harus:
1. Baca CLAUDE.md (Golden Rules)
2. Baca MEMORY.md (status + keputusan teknikal)
3. Baca SESSION.md ini (checkpoint + spesifikasi Feature C)
4. Lanjut langsung ke Feature C tanpa tanya-tanya

Perintah untuk Claude di sesi baru:
> "baca claude.md, memory.md, session.md dulu lalu lanjut ke feature C AI chatbot"

---

## BLOCKER
- Tidak ada.

## FILE YANG DIUBAH SESI INI

### Feature D (Loyalty):
- `backend/api/routes/loyalty.py` (baru)
- `backend/api/api.py`
- `kasir_app/lib/features/loyalty/` (semua file baru)
- `kasir_app/lib/features/pos/presentation/widgets/cart_panel.dart`
- `kasir_app/lib/main.dart`

### Feature A (Dapur):
- `kasir_app/lib/main_dapur.dart` (baru)
- `kasir_app/lib/features/dapur/` (semua file baru)
- `backend/api/routes/auth.py` (tambah POST /auth/pin/verify)
- `kasir_app/lib/features/auth/presentation/pages/login_page.dart`
- `.github/workflows/build-apk.yml`

### Feature B (Connect Storefront):
- `backend/api/routes/connect.py`
- `backend/api/routes/payments.py`
- `app/actions/storefront.ts`
- `app/[slug]/order/[id]/page.tsx`
- `app/[slug]/cart/page.tsx`
