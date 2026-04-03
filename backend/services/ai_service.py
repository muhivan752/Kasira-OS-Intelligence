"""
Kasira AI Service — AI Chatbot untuk Owner/Manager

Golden Rules yang diimplementasikan:
- Rule #25: Model dipilih via get_model_for_tier() — TIDAK pernah hardcoded
- Rule #26: Starter/rutin = Haiku, Pro+ kompleks = Sonnet
- Rule #27: 3 optimasi — batching context, cache Redis, compress context
- Rule #54: Intent WAJIB classified, WRITE butuh konfirmasi
- Rule #55: System prompt max 800 token, cache Redis 5 menit
- Rule #56: UNKNOWN intent = tolak sopan
"""

import json
import logging
from datetime import datetime, timezone, time as dt_time, timedelta
from typing import AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

INTENT_READ = "READ"
INTENT_WRITE = "WRITE"
INTENT_UNKNOWN = "UNKNOWN"

# Keywords untuk intent classification (Bahasa Indonesia + sedikit Inggris)
READ_KEYWORDS = [
    "laporan", "omzet", "pendapatan", "revenue", "penjualan", "berapa",
    "transaksi", "order", "pesanan", "produk terlaris", "best seller",
    "stok", "stock", "sisa", "pelanggan", "customer", "kasir",
    "shift", "hari ini", "kemarin", "minggu ini", "bulan ini",
    "performa", "statistik", "analisa", "trend", "grafik", "summary",
    "total", "rata-rata", "average", "tertinggi", "terendah",
]

WRITE_KEYWORDS = [
    "tambah", "buat", "create", "hapus", "delete", "ubah", "update",
    "ganti", "edit", "set", "jadikan", "nonaktifkan", "aktifkan",
    "harga", "nama produk", "stok tambah", "restock", "diskon",
    "promo", "tutup outlet", "buka outlet",
]

BUSINESS_CONTEXT_KEYWORDS = [
    "menu", "produk", "makanan", "minuman", "cafe", "restoran", "warung",
    "kasir", "pembayaran", "qris", "cash", "tunai", "pelanggan",
    "meja", "takeaway", "dine in", "delivery", "pesanan", "order",
    "omzet", "penjualan", "pendapatan", "shift", "laporan", "stok",
    "bahan", "ingredient", "supplier", "dapur", "kitchen",
    "promo", "diskon", "loyalty", "poin", "voucher",
]


# ─── Model Selector (Rule #25, #26) ───────────────────────────────────────────

def get_model_for_tier(tier: str, task: str = "routine") -> str:
    """
    Pilih Claude model berdasarkan tier outlet dan kompleksitas task.
    Rule #25: Tidak pernah hardcoded.
    Rule #26: Starter/rutin = Haiku. Sonnet hanya Pro+ task kompleks.
    """
    if tier in ("pro", "enterprise", "business") and task == "complex":
        return "claude-sonnet-4-6"
    return "claude-haiku-4-5-20251001"


# ─── Intent Classifier (Rule #54, #56) ────────────────────────────────────────

def classify_intent(message: str) -> str:
    """
    Klasifikasi intent pesan owner.
    Returns: READ | WRITE | UNKNOWN
    """
    msg_lower = message.lower()

    # Cek apakah pesan relevan dengan konteks bisnis
    has_business_context = any(kw in msg_lower for kw in BUSINESS_CONTEXT_KEYWORDS)
    has_read = any(kw in msg_lower for kw in READ_KEYWORDS)
    has_write = any(kw in msg_lower for kw in WRITE_KEYWORDS)

    if has_write:
        return INTENT_WRITE
    if has_read or has_business_context:
        return INTENT_READ
    return INTENT_UNKNOWN


def classify_task_complexity(message: str) -> str:
    """Tentukan apakah task ini kompleks atau rutin."""
    complex_patterns = [
        "analisa", "prediksi", "rekomendasi", "strategi",
        "bandingkan", "compare", "insight", "kenapa", "why",
    ]
    msg_lower = message.lower()
    if any(p in msg_lower for p in complex_patterns):
        return "complex"
    return "routine"


# ─── Cache TTL (Rule #27) ─────────────────────────────────────────────────────

def seconds_until_midnight_wib() -> int:
    """Hitung detik sampai 00.00 WIB (UTC+7). Untuk cache context harian."""
    now_utc = datetime.now(timezone.utc)
    # Tengah malam WIB = 17:00 UTC
    midnight_wib_utc = now_utc.replace(
        hour=17, minute=0, second=0, microsecond=0
    )
    if now_utc >= midnight_wib_utc:
        midnight_wib_utc += timedelta(days=1)
    secs = int((midnight_wib_utc - now_utc).total_seconds())
    return max(secs, 300)  # minimum 5 menit


# ─── Context Builder (Rule #27, #55) ──────────────────────────────────────────

async def build_context(
    outlet_id: str,
    tenant_id: str,
    outlet_name: str,
    db: AsyncSession,
    redis_client,
) -> str:
    """
    Bangun context bisnis untuk system prompt.
    - Di-cache di Redis sampai 00.00 WIB (Rule #27)
    - Max ~800 token agregat (Rule #55)
    - Compress: kirim ringkasan, BUKAN raw rows
    """
    cache_key = f"ai:context:{outlet_id}"

    # Try Redis cache
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    # Build fresh context
    from backend.models.order import Order, OrderItem
    from backend.models.payment import Payment
    from backend.models.product import Product, OutletStock

    today = datetime.now(timezone.utc).date()
    start_today = datetime.combine(today, dt_time.min).replace(tzinfo=timezone.utc)
    start_week = start_today - timedelta(days=6)

    try:
        # Set tenant schema
        await db.execute(text(f'SET search_path TO "{tenant_id}", public'))

        # 1. Omzet hari ini
        today_stats = await db.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
                func.count(Order.id).label("count"),
            ).where(
                Order.outlet_id == outlet_id,
                Order.created_at >= start_today,
                Order.status != "cancelled",
                Order.id.in_(
                    select(Payment.order_id).where(Payment.status == "paid")
                ),
            )
        )
        today_row = today_stats.first()
        revenue_today = float(today_row.revenue) if today_row else 0.0
        order_count_today = int(today_row.count) if today_row else 0

        # 2. Top 3 produk hari ini
        top_products = await db.execute(
            select(
                Product.name,
                func.sum(OrderItem.quantity).label("sold"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(
                Order.outlet_id == outlet_id,
                Order.created_at >= start_today,
                Order.status != "cancelled",
                Order.id.in_(
                    select(Payment.order_id).where(Payment.status == "paid")
                ),
            )
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(3)
        )
        top_list = [f"{r.name} ({r.sold} pcs)" for r in top_products.all()]

        # 3. Omzet 7 hari
        week_stats = await db.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
                func.count(Order.id).label("count"),
            ).where(
                Order.outlet_id == outlet_id,
                Order.created_at >= start_week,
                Order.status != "cancelled",
                Order.id.in_(
                    select(Payment.order_id).where(Payment.status == "paid")
                ),
            )
        )
        week_row = week_stats.first()
        revenue_week = float(week_row.revenue) if week_row else 0.0
        order_count_week = int(week_row.count) if week_row else 0

        # 4. Stok kritis (computed_stock < 5)
        low_stock = await db.execute(
            select(Product.name, OutletStock.computed_stock)
            .join(OutletStock, Product.id == OutletStock.product_id)
            .where(
                OutletStock.outlet_id == outlet_id,
                OutletStock.computed_stock < 5,
                OutletStock.computed_stock >= 0,
                Product.deleted_at.is_(None),
            )
            .limit(5)
        )
        low_list = [
            f"{r.name} (sisa {int(r.computed_stock)})" for r in low_stock.all()
        ]

    except Exception as e:
        logger.warning(f"Context build error: {e}")
        revenue_today = revenue_week = 0.0
        order_count_today = order_count_week = 0
        top_list = []
        low_list = []

    today_str = today.strftime("%d %B %Y")
    context = f"""Kamu adalah asisten AI untuk {outlet_name}, sebuah cafe di Indonesia.
Tanggal: {today_str}

DATA BISNIS HARI INI:
- Omzet: Rp{revenue_today:,.0f} dari {order_count_today} transaksi
- Produk terlaris: {", ".join(top_list) if top_list else "belum ada transaksi"}

DATA 7 HARI TERAKHIR:
- Total omzet: Rp{revenue_week:,.0f} dari {order_count_week} transaksi
- Rata-rata/hari: Rp{revenue_week/7:,.0f}

STOK KRITIS (perlu restock):
{chr(10).join("- " + s for s in low_list) if low_list else "- Semua stok aman"}

INSTRUKSI:
- Jawab hanya pertanyaan seputar bisnis cafe ini
- Gunakan bahasa Indonesia yang ramah dan profesional
- Angka dalam format Rupiah (Rp x.xxx)
- Jawaban singkat dan langsung to the point"""

    # Cache sampai 00.00 WIB
    ttl = seconds_until_midnight_wib()
    try:
        await redis_client.setex(cache_key, ttl, context)
    except Exception:
        pass

    return context


# ─── SSE Generator (Rule #9 async) ────────────────────────────────────────────

async def stream_ai_response(
    message: str,
    outlet_id: str,
    tenant_id: str,
    outlet_name: str,
    tier: str,
    db: AsyncSession,
    redis_client,
) -> AsyncGenerator[str, None]:
    """
    Generator untuk SSE stream.
    Yields: "data: {...}\n\n" strings
    """

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # 1. Classify intent (Rule #54, #56)
    intent = classify_intent(message)

    if intent == INTENT_UNKNOWN:
        yield sse({
            "type": "chunk",
            "content": "Maaf, saya hanya bisa membantu pertanyaan seputar bisnis cafe Anda. "
                       "Contoh: omzet hari ini, produk terlaris, atau stok yang perlu diisi.",
        })
        yield sse({"type": "done", "intent": intent, "tokens_used": 0})
        return

    if intent == INTENT_WRITE:
        yield sse({
            "type": "chunk",
            "content": "⚠️ Permintaan ini akan mengubah data bisnis Anda. "
                       "Silakan lakukan perubahan langsung di menu pengaturan aplikasi Kasira "
                       "untuk memastikan keamanan data.",
        })
        yield sse({"type": "done", "intent": intent, "tokens_used": 0})
        return

    # 2. Cek API key
    if not settings.ANTHROPIC_API_KEY:
        yield sse({
            "type": "chunk",
            "content": "Maaf, fitur AI belum dikonfigurasi. Hubungi admin untuk mengaktifkan.",
        })
        yield sse({"type": "done", "intent": intent, "tokens_used": 0})
        return

    # 3. Build context (cached, Rule #27/#55)
    system_prompt = await build_context(
        outlet_id=outlet_id,
        tenant_id=tenant_id,
        outlet_name=outlet_name,
        db=db,
        redis_client=redis_client,
    )

    # 4. Pilih model (Rule #25/#26)
    task_complexity = classify_task_complexity(message)
    model = get_model_for_tier(tier, task_complexity)

    # 5. Stream dari Claude API
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        tokens_used = 0
        async with client.messages.stream(
            model=model,
            max_tokens=512,  # Hemat token — jawaban ringkas
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
        ) as stream:
            async for text_chunk in stream.text_stream:
                yield sse({"type": "chunk", "content": text_chunk})

            # Usage dari final message
            final_msg = await stream.get_final_message()
            tokens_used = (
                final_msg.usage.input_tokens + final_msg.usage.output_tokens
            )

        yield sse({"type": "done", "intent": intent, "tokens_used": tokens_used, "model": model})

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        yield sse({
            "type": "error",
            "message": "Maaf, terjadi gangguan pada layanan AI. Coba lagi dalam beberapa saat.",
        })
