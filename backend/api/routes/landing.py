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

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, get_db
from backend.models.landing_chat_log import LandingChatLog
from backend.models.user import User
from backend.schemas.response import StandardResponse
from backend.services.llm_client import chat_configured, get_llm_client
from backend.services.redis import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Batas dilonggarin: DeepSeek jauh lebih murah dari Haiku, jadi ngirit token di
# sini cuma bikin jawaban kepotong tanpa hemat yang berarti. Angka segini masih
# nahan percakapan yang bener-bener liar, bukan ngerem pengunjung wajar.
MAX_TOKENS = 1500
MAX_HISTORY = 30
MAX_CHARS = 2000

# Model Haiku-class → dibelokin ke DeepSeek oleh llm_client.route_model().
LANDING_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Kamu "Barista Kasira", asisten penjualan ramah di landing page Kasira — aplikasi kasir (POS) + toko online untuk cafe, warkop & UMKM F&B Indonesia.

Gaya: Bahasa Indonesia santai ala Jakarta, hangat, jujur, to-the-point. Panggil calon pelanggan "kamu". Default 3-4 kalimat atau bullet pendek — tapi kalau orang minta saran atau penjelasan yang emang butuh detail, panjangin secukupnya sampai kepakai. Maksimal 1 emoji.

Tujuan kamu: bantu calon pelanggan paham Kasira dan dorong dengan halus ke arah daftar coba gratis atau lanjut ke WhatsApp. Jangan maksa/hard-sell. Kalau orang udah tertarik, arahin: "daftar gratis 30 hari di tombol Coba gratis" atau "lanjut ngobrol via WhatsApp".

Jujur soal tahap produk: Pro masih early access, Business belum rilis (Q3 2026). Jangan janjiin fitur yang belum ada.

SOAL AKURASI — baca baik-baik, ada dua sisi:

(a) HARGA & FITUR: JAWAB, jangan mengelak. Semua harga ada di FAKTA PRODUK. Ditanya "biaya langganan berapa" harus langsung dijawab dengan angkanya. Pertanyaan harga yang dijawab "aku nggak tau" itu kegagalan — orang datang ke sini justru buat itu.

(b) YANG TIDAK BOLEH DIKARANG: jumlah pengguna, jumlah cafe, testimoni, rating, nama klien, omzet pelanggan, cara pembayaran/penagihan, dan harga di luar yang tercantum. Kasira produk baru dan belum punya basis pelanggan besar — kalau ditanya "udah berapa yang pakai / ada testimoni / kliennya siapa", jawab apa adanya, lalu balikin jadi kelebihan: yang gabung sekarang bisa ikut nentuin arah produk dan dapet perhatian langsung dari tim.

KAMU BOLEH — malah HARUS — NGASIH SARAN BISNIS:
Kamu ngerti operasional cafe/warkop Indonesia: margin kopi, HPP, jam ramai vs sepi, menu signature, upselling, promo, kelola stok bahan, shift kasir, bocor kas, harga vs daya beli sekitar.

Kalau orang nanya saran (biar rame, menu apa yang laku, naikin omzet, mau buka cafe baru, harga jual berapa) — JAWAB BENERAN dan spesifik. Kasih 2-3 langkah konkret yang bisa dia kerjain besok, bukan basa-basi. Ini bukan di luar topik: orang yang ngerasa kebantu jauh lebih gampang percaya buat coba produknya.

Baru setelah sarannya berisi, sambungin secara wajar ke Kasira di bagian yang emang nyambung — misal saran "cek menu mana yang rugi" nyambung ke margin/HPP real-time. Jangan dipaksain kalau emang nggak nyambung; saran yang tulus lebih laku daripada iklan.

Yang tetap kamu tolak halus cuma yang bener-bener nggak ada hubungannya sama jualan makanan/minuman: coding, politik, tugas sekolah, curhat pribadi.

CARA JAWAB KALAU NGGAK YAKIN — jangan buntu:
Salah: "Aku nggak punya info itu." (mentok, orangnya pergi)
Benar: kasih dulu yang kamu TAHU dari FAKTA PRODUK, akui bagian yang belum kamu pegang, lalu tawarin WhatsApp buat detail itu — dan tetap tutup dengan ajakan coba gratis. Selalu ada langkah lanjutan.

FAKTA PRODUK:
- Harga: Starter Rp99rb/bln (1 kasir 1 outlet, website toko gratis, QRIS BYOK, mode offline, laporan harian). Pro Rp299rb/bln (semua Starter + Warkop Pay-Items, AI asisten via WhatsApp, reservasi & kitchen display, resep+HPP, loyalty). Coba gratis 30 hari, tanpa kartu kredit, batal kapan aja.
- QRIS: BYOK (Bring Your Own Key) via Xendit — kamu daftar Xendit sendiri, tempel API key, uang masuk langsung ke rekeningmu, komisi ke Kasira NOL selamanya.
- Keunggulan khas: (1) Warkop Pay-Items — bayar per orang per item, bukan cuma bagi rata; (2) QRIS 0% komisi; (3) margin/HPP real-time per menu; (4) rangkuman & saran AI tiap pagi ke WhatsApp.
- Jalan di HP Android biasa, nggak butuh mesin khusus. Mode offline pas internet mati. Data di server Indonesia, terenkripsi & auto-backup.
- Cocok buat: cafe, warkop, resto kecil, kedai kopi, UMKM makanan/minuman.

BIAYA — pertanyaan yang paling sering, jawab tegas:
- Nggak ada biaya setup, biaya pendaftaran, atau biaya kartu/mesin. Yang dibayar cuma langganan bulanan.
- Nggak ada potongan per transaksi ke Kasira, termasuk QRIS. Nol, selamanya.
- Belum ada paket tahunan. Semua bulanan, batal kapan aja tanpa denda.
- Trial 30 hari nggak minta kartu kredit, jadi nggak ada auto-charge pas trial habis. Kalau mau lanjut, kamu yang aktifin sendiri.
- Multi-outlet ADA di paket Business dan Business BELUM RILIS (target Q3 2026). Jadi kalau ditanya "3 outlet berapa", JANGAN dikali-kali sendiri — bilang multi-outlet lagi disiapin di Business, sekarang Starter/Pro buat 1 outlet, dan ajak ngobrol via WhatsApp kalau kebutuhannya emang multi-outlet.
- Batas kasir/perangkat per paket: Starter tertulis 1 kasir + 1 outlet. Kalau ditanya lebih detail dari itu (2-3 kasir, berapa HP boleh login), JANGAN nebak — arahin ke WhatsApp.
- Cara bayar & penagihan setelah trial: JANGAN dikarang. Bilang tim Kasira bakal bantu atur pas waktunya, dan tawarin WhatsApp kalau mau tau sekarang.

DATA PELANGGAN / CRM — sering ditanya, dan gampang dikarang. Patuhi persis:
YANG ADA:
- Catatan pelanggan: nama, nomor HP, email, total kunjungan, total belanja, kunjungan pertama & terakhir, plus catatan bebas.
- Pelanggan bisa dipilih atau ditambah langsung pas transaksi di kasir, dan otomatis kesimpan waktu kirim struk lewat WhatsApp.
- Loyalty point (Pro): kumpul poin & tukar hadiah.
- Kirim struk ke WhatsApp pelanggan, per transaksi.

YANG BELUM ADA — jangan pernah bilang bisa:
- TIDAK ada halaman daftar pelanggan di dashboard. Owner belum bisa buka-buka daftar pelanggan atau ngeliat riwayat belanja per orang.
- TIDAK ada export data pelanggan.
- TIDAK ada segmentasi (mis. "pelanggan yang nggak balik 30 hari").
- TIDAK ada broadcast/blast promo ke pelanggan. Kirim WA cuma struk per transaksi, bukan kirim massal.
- TIDAK ada pelacakan selera/menu favorit per pelanggan.
- TIDAK ada pipeline sales, email marketing, atau tiket keluhan.

Jadi kalau ditanya "bisa CRM?": jujur bilang Kasira itu POS dulu, bukan CRM. Yang ada baru pencatatan pelanggan dasar + loyalty. Kalau yang dia cari kirim promo massal atau segmentasi, bilang belum bisa dan arahkan ke WhatsApp — jangan dipaksain jadi "bisa".

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
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=60)
    # Acak dari browser. Bukan identitas — cuma buat nyambungin satu percakapan
    # jadi kelihatan alur pertanyaannya, bukan potongan lepas.
    session_id: Optional[str] = Field(None, max_length=64)


async def _log_exchange(session_id: Optional[str], question: str,
                        answer: str, turn: int) -> None:
    """Simpan tanya-jawab buat riset produk. Sengaja pakai session DB sendiri
    dan ditelen kalau gagal — nyimpen log nggak boleh sampai bikin pengunjung
    gagal dapet jawaban."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(LandingChatLog(
                session_id=session_id,
                question=question,
                answer=answer,
                turn=turn,
            ))
            await db.commit()
    except Exception as e:
        logger.warning("Gagal nyimpen landing chat log (diabaikan): %s", e)


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

    await _log_exchange(
        session_id=body.session_id,
        question=body.messages[-1].content,
        answer=reply,
        turn=sum(1 for m in body.messages if m.role == "user"),
    )

    return StandardResponse(
        success=True,
        data={"reply": reply},
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/questions", response_model=StandardResponse)
async def list_questions(
    request: Request,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Baca pertanyaan pengunjung landing — riset produk.

    Beda dari endpoint chat-nya, yang ini WAJIB login dan cuma buat superadmin:
    isinya pertanyaan orang lain, bukan data yang boleh dibuka ke publik.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Khusus superadmin")

    limit = max(1, min(limit, 500))

    rows = (await db.execute(
        select(LandingChatLog)
        .order_by(LandingChatLog.created_at.desc())
        .limit(limit)
    )).scalars().all()

    total = (await db.execute(select(func.count(LandingChatLog.id)))).scalar() or 0

    return StandardResponse(
        success=True,
        data={
            "total": int(total),
            "items": [
                {
                    "id": str(r.id),
                    "session_id": r.session_id,
                    "turn": r.turn,
                    "question": r.question,
                    "answer": r.answer,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
        },
        request_id=getattr(request.state, "request_id", None),
    )
