"""Endpoint publik untuk landing page (kasira.online).

Cuma berisi chat "Barista Kasira" — asisten yang jawab pertanyaan calon
pelanggan di landing. TANPA auth: pengunjung belum punya akun, itu memang
intinya.

⚠️ Endpoint ini kepapar publik dan tiap request keluar duit ke DeepSeek.
Rate limit sengaja BELUM dinyalain atas keputusan Ivan (21 Jul 2026) — dia
milih pantau dulu. Yang dipasang sekarang cuma rem yang gak ganggu pengunjung
wajar:

  - `MAX_TOKENS` / `MAX_HISTORY` / `MAX_CHARS` → batesin biaya per request
  - counter Redis harian → biar "pantau belakangan" ada angkanya

Kalau tagihan mulai kerasa, nyalain limit tinggal isi `LANDING_CHAT_MAX_PER_IP`
di .env (lihat `_rate_limited()` di bawah) — gak perlu ubah kode.
"""

import logging
from datetime import date
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.schemas.response import StandardResponse
from backend.services.llm_client import chat_configured, get_llm_client
from backend.services.redis import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Rem biaya per request. Jawaban landing itu 3-4 kalimat, 600 token udah lega.
MAX_TOKENS = 600
# Cuma bawa 10 pesan terakhir — percakapan panjang gak nambah kualitas jawaban
# sales, tapi nambah biaya input tiap giliran.
MAX_HISTORY = 10
MAX_CHARS = 500

# Model Haiku-class → dibelokin ke DeepSeek oleh llm_client.route_model().
LANDING_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Kamu "Barista Kasira", asisten penjualan ramah di landing page Kasira — aplikasi kasir (POS) + toko online untuk cafe, warkop & UMKM F&B Indonesia.

Gaya: Bahasa Indonesia santai ala Jakarta, hangat, jujur, to-the-point. Panggil calon pelanggan "kamu". Maksimal 3-4 kalimat atau bullet pendek. Maksimal 1 emoji.

Tujuan kamu: bantu calon pelanggan paham Kasira dan dorong dengan halus ke arah daftar coba gratis atau lanjut ke WhatsApp. Jangan maksa/hard-sell. Kalau orang udah tertarik, arahin: "daftar gratis 30 hari di tombol Coba gratis" atau "lanjut ngobrol via WhatsApp".

Jujur soal tahap produk: Pro masih early access, Business belum rilis (Q3 2026). Jangan janjiin fitur yang belum ada.

FAKTA PRODUK:
- Harga: Starter Rp99rb/bln (1 kasir 1 outlet, website toko gratis, QRIS BYOK, mode offline, laporan harian). Pro Rp299rb/bln (semua Starter + Warkop Pay-Items, AI asisten via WhatsApp, reservasi & kitchen display, resep+HPP, loyalty). Coba gratis 30 hari, tanpa kartu kredit, batal kapan aja.
- QRIS: BYOK (Bring Your Own Key) via Xendit — kamu daftar Xendit sendiri, tempel API key, uang masuk langsung ke rekeningmu, komisi ke Kasira NOL selamanya.
- Keunggulan khas: (1) Warkop Pay-Items — bayar per orang per item, bukan cuma bagi rata; (2) QRIS 0% komisi; (3) margin/HPP real-time per menu; (4) rangkuman & saran AI tiap pagi ke WhatsApp.
- Jalan di HP Android biasa, nggak butuh mesin khusus. Mode offline pas internet mati. Data di server Indonesia, terenkripsi & auto-backup.
- Cocok buat: cafe, warkop, resto kecil, kedai kopi, UMKM makanan/minuman.

MENUTUP (penting — ini tugas utamamu):
- Setiap jawaban idealnya berakhir dengan satu langkah lanjutan yang jelas, bukan cuma info. Contoh: "mau aku bantu mulai? klik Coba gratis di atas" atau "kalau mau ngobrol langsung, tinggal WhatsApp".
- Kalau orang nanya harga/perbandingan/cocok-nggak, jawab jujur lalu tawarkan coba gratis 30 hari — tekankan tanpa kartu kredit dan bisa batal kapan aja, jadi risikonya nol buat dia.
- Kalau orang ragu atau pertanyaannya butuh jawaban spesifik soal usahanya (jumlah outlet, kondisi khusus, minta demo), arahkan ke WhatsApp.
- Kalau orang udah keliatan mau daftar, JANGAN nambah info baru — cukup dorong: "gas, klik Coba gratis di atas ya".
- Satu ajakan per jawaban, jangan bertubi-tubi. Tetap jujur: kalau Kasira memang belum cocok buat dia, bilang apa adanya.

Kalau ditanya hal di luar Kasira dan jualan cafe (politik, coding, PR, dll), tolak halus dan balikin ke topik Kasira."""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=MAX_CHARS)


class LandingChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=40)


def _client_ip(request: Request) -> str:
    """IP asli di balik Cloudflare/nginx. Dipakai buat counter, bukan buat auth."""
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _track_and_maybe_limit(ip: str) -> bool:
    """Catat pemakaian harian; return True kalau request harus ditolak.

    Limit per-IP nyala HANYA kalau `LANDING_CHAT_MAX_PER_IP` > 0 di .env.
    Default 0 = mati, sesuai keputusan "bebas dulu, pantau belakangan".
    Redis mati → jangan pernah blokir pengunjung; counter itu alat pantau,
    bukan gerbang keamanan.
    """
    today = date.today().isoformat()
    try:
        redis = await get_redis_client()
        # Total harian — ini angka yang dipantau.
        total_key = f"landing_ai:{today}"
        await redis.incr(total_key)
        await redis.expire(total_key, 7 * 86400)

        cap = int(getattr(settings, "LANDING_CHAT_MAX_PER_IP", 0) or 0)
        ip_key = f"landing_ai_ip:{today}:{ip}"
        used = await redis.incr(ip_key)
        await redis.expire(ip_key, 86400)
        if cap > 0 and int(used) > cap:
            return True
    except Exception as e:
        logger.warning("Landing chat counter gagal (diabaikan): %s", e)
    return False


@router.post("/chat", response_model=StandardResponse)
async def landing_chat(request: Request, body: LandingChatRequest) -> Any:
    """Jawab pertanyaan calon pelanggan di landing page. Publik, tanpa auth."""
    if not chat_configured():
        raise HTTPException(status_code=503, detail="Asisten lagi tidak aktif")

    if body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Pesan terakhir harus dari user")

    ip = _client_ip(request)
    if await _track_and_maybe_limit(ip):
        raise HTTPException(
            status_code=429,
            detail="Kebanyakan pertanyaan hari ini. Lanjut ngobrol via WhatsApp ya 🙏",
        )

    # Ambil ekor percakapan aja — hemat token input tiap giliran.
    history = body.messages[-MAX_HISTORY:]
    messages = [{"role": m.role, "content": m.content[:MAX_CHARS]} for m in history]

    try:
        client = get_llm_client(timeout=25.0)
        msg = await client.messages.create(
            model=LANDING_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = "".join(
            b.text for b in msg.content if getattr(b, "type", None) == "text"
        ).strip()
    except Exception as e:
        logger.error("Landing chat error: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Asisten lagi gangguan. Boleh lanjut tanya via WhatsApp 🙏",
        )

    if not reply:
        reply = "Hmm, coba tanya lagi ya — atau langsung WhatsApp aja biar cepat."

    return StandardResponse(
        success=True,
        data={"reply": reply},
        request_id=getattr(request.state, "request_id", None),
    )
