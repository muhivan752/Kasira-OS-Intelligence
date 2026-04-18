"""
Kasira AI Service — AI Chatbot untuk Owner/Manager

Golden Rules yang diimplementasikan:
- Rule #25: Model dipilih via get_model_for_tier() — sekarang SELALU Haiku 4.5
- Rule #26: Haiku untuk semua task. Analisa bisnis UMKM gak butuh Sonnet (bukan coding/math)
- Rule #27: 3 optimasi — batching context, cache Redis, compress context
- Rule #54: Intent classified untuk RESTOCK (actionable). Chat umum langsung ke Claude.
- Rule #55: System prompt max 800 token, cache Redis 5 menit

Design: AI asisten bisnis umum untuk UMKM Indonesia — F&B, retail, vape, sepeda listrik, dll.
Bukan F&B-only. Merchant yang tanya common knowledge (takaran, operasional, pricing) harus dapat jawaban konkret.
"""

import json
import logging
from datetime import datetime, timezone, time as dt_time, timedelta
from typing import AsyncGenerator, Optional
from uuid import UUID

import sqlalchemy
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

INTENT_CHAT = "CHAT"
INTENT_RESTOCK = "RESTOCK"
INTENT_SETUP_RECIPE = "SETUP_RECIPE"

# Keyword detection hanya untuk RESTOCK (actionable — langsung update DB).
# Selain itu semua pertanyaan → CHAT → Claude yang jawab via system prompt.
RESTOCK_KEYWORDS = [
    "restock", "tambah stok", "masukin stok", "isi stok", "stok masuk",
    "baru beli", "beli bahan", "datang bahan", "terima bahan",
    "update stok", "nambah stok", "restok",
    "tambah bahan", "tambahin bahan", "nambah bahan", "tambahkan bahan",
    "stok bahan", "isi bahan", "masukin bahan", "masukkan bahan",
]

# Keyword detection untuk SETUP_RECIPE — AI generate proposal bahan + qty,
# user confirm via tombol di dashboard lalu execute via /ai/apply-recipe.
SETUP_RECIPE_KEYWORDS = [
    "setup resep", "bikin resep", "buat resep", "bikinin resep",
    "atur resep", "tambah resep", "tambahin resep", "tambahkan resep",
    "susun resep", "resep untuk", "resep buat", "isi resep",
    "setup isi", "bikin isi", "atur isi per porsi",
    "setup komposisi", "bikin komposisi",
]


# ─── Model Selector (Rule #25, #26) ───────────────────────────────────────────

async def get_model_for_tier(tier: str, task: str = "routine", tenant_id: str = None) -> str:
    """
    Pilih Claude model — SELALU Haiku 4.5.

    Reasoning: Kasira AI tasks = analisa bisnis UMKM dengan context yang udah dipre-build
    (omzet, stok, HPP, KG, menu engineering). Itu bukan task yang butuh reasoning mendalam
    kayak coding/math proof. Haiku 4.5 fully capable untuk business analytics.

    Sonnet ~4x biaya Haiku. Overkill untuk use case ini. Biaya matters.
    """
    return "claude-haiku-4-5-20251001"


# ─── Intent Classifier (Rule #54, #56) ────────────────────────────────────────

def classify_intent(message: str) -> str:
    """
    Klasifikasi intent pesan owner.
    Returns:
      - SETUP_RECIPE (AI propose recipe, user confirm → apply)
      - RESTOCK (actionable — update DB langsung)
      - CHAT (default — Claude jawab)

    Scope filtering dilakukan di system prompt, bukan di classifier.
    SETUP_RECIPE di-check duluan supaya "tambah bahan untuk resep kopi susu"
    masuk ke SETUP_RECIPE, bukan RESTOCK.
    """
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in SETUP_RECIPE_KEYWORDS):
        return INTENT_SETUP_RECIPE
    if any(kw in msg_lower for kw in RESTOCK_KEYWORDS):
        return INTENT_RESTOCK
    return INTENT_CHAT


# ─── Restock via AI ──────────────────────────────────────────────────────────

UNIT_ALIASES = {
    "kg": ("gram", 1000), "kilo": ("gram", 1000), "kilogram": ("gram", 1000),
    "g": ("gram", 1), "gram": ("gram", 1), "gr": ("gram", 1),
    "l": ("ml", 1000), "liter": ("ml", 1000),
    "ml": ("ml", 1), "mililiter": ("ml", 1),
    "pcs": ("pcs", 1), "butir": ("pcs", 1), "buah": ("pcs", 1), "biji": ("pcs", 1),
    "tray": ("pcs", 30), "dus": ("pcs", 12), "lusin": ("pcs", 12),
    "bungkus": ("bungkus", 1), "bks": ("bungkus", 1), "pack": ("bungkus", 1),
}


async def parse_restock_intent(message: str, outlet_id: str, tenant_id: str, db: AsyncSession) -> dict:
    """
    Parse restock message and find matching ingredient.
    Returns: {success, ingredient_id, ingredient_name, quantity, unit, error}
    """
    import re
    from backend.models.ingredient import Ingredient
    from backend.models.product import OutletStock

    msg = message.lower().strip()

    # Load all ingredients for this tenant
    from backend.models.outlet import Outlet
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not outlet:
        return {"success": False, "error": "Outlet tidak ditemukan"}

    ingredients = (await db.execute(
        select(Ingredient).where(
            Ingredient.brand_id == outlet.brand_id,
            Ingredient.deleted_at.is_(None),
        )
    )).scalars().all()

    if not ingredients:
        return {"success": False, "error": "Belum ada bahan baku. Tambahkan bahan dulu di halaman Bahan Baku."}

    # Try to parse quantity + unit from message
    # Patterns: "1kg", "1 kg", "500 gram", "2 liter", "30 butir"
    qty_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|kilo|kilogram|gram|gr|g|liter|l|ml|mililiter|pcs|butir|buah|biji|tray|dus|lusin|bungkus|bks|pack)\b', msg)

    raw_qty = None
    raw_unit = None
    if qty_match:
        raw_qty = float(qty_match.group(1).replace(',', '.'))
        raw_unit = qty_match.group(2)

    # Convert to base unit
    base_unit = None
    final_qty = None
    if raw_unit and raw_unit in UNIT_ALIASES:
        base_unit, multiplier = UNIT_ALIASES[raw_unit]
        final_qty = raw_qty * multiplier

    # Fuzzy match ingredient name
    best_match = None
    best_score = 0
    msg_words = set(re.findall(r'[a-zA-Z]+', msg))

    for ing in ingredients:
        ing_words = set(re.findall(r'[a-zA-Z]+', ing.name.lower()))
        # Simple word overlap score
        overlap = len(msg_words & ing_words)
        if overlap > best_score:
            best_score = overlap
            best_match = ing
        # Also try substring match
        if ing.name.lower() in msg or any(w in msg for w in ing_words if len(w) > 3):
            if overlap >= best_score:
                best_match = ing
                best_score = max(overlap, 1)

    if not best_match or best_score == 0:
        names = ", ".join([i.name for i in ingredients[:10]])
        return {"success": False, "error": f"Bahan tidak ditemukan. Bahan yang tersedia: {names}"}

    if final_qty is None or final_qty <= 0:
        return {"success": False, "error": f"Berapa jumlah {best_match.name} yang mau di-restock? Contoh: 'restock {best_match.name} 1kg'"}

    # Validate unit compatibility
    if base_unit and base_unit != best_match.base_unit:
        # Auto-convert if possible (e.g., user says "1kg" but ingredient uses "gram")
        if base_unit == "gram" and best_match.base_unit == "gram":
            pass  # OK
        elif base_unit == "ml" and best_match.base_unit == "ml":
            pass  # OK
        else:
            return {"success": False, "error": f"{best_match.name} dihitung dalam {best_match.base_unit}, tapi Anda memasukkan {raw_unit}. Coba: 'restock {best_match.name} {int(final_qty)} {best_match.base_unit}'"}

    # Get current stock
    stock_row = (await db.execute(
        select(OutletStock).where(
            OutletStock.outlet_id == outlet_id,
            OutletStock.ingredient_id == best_match.id,
            OutletStock.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    current_stock = float(stock_row.computed_stock) if stock_row else 0

    return {
        "success": True,
        "ingredient_id": str(best_match.id),
        "ingredient_name": best_match.name,
        "quantity": final_qty,
        "unit": best_match.base_unit,
        "current_stock": current_stock,
        "stock_after": current_stock + final_qty,
    }


async def execute_restock(ingredient_id: str, outlet_id: str, quantity: float, user_id: str, db: AsyncSession) -> bool:
    """Execute the actual restock operation."""
    from backend.models.product import OutletStock
    from backend.models.event import Event
    from sqlalchemy import update as sql_update

    ing_uuid = UUID(ingredient_id) if isinstance(ingredient_id, str) else ingredient_id
    out_uuid = UUID(outlet_id) if isinstance(outlet_id, str) else outlet_id

    stock = (await db.execute(
        select(OutletStock).where(
            OutletStock.outlet_id == out_uuid,
            OutletStock.ingredient_id == ing_uuid,
            OutletStock.deleted_at.is_(None),
        ).with_for_update()
    )).scalar_one_or_none()

    if not stock:
        # Auto-create stock record if ingredient exists but no stock entry yet
        import uuid as uuid_mod
        stock = OutletStock(
            id=uuid_mod.uuid4(),
            outlet_id=out_uuid,
            ingredient_id=ing_uuid,
            computed_stock=0,
            row_version=0,
        )
        db.add(stock)
        await db.flush()

    stock_before = float(stock.computed_stock)
    stock_after = stock_before + quantity
    now = datetime.now(timezone.utc)

    # Update stock
    await db.execute(
        sql_update(OutletStock).where(OutletStock.id == stock.id).values(
            computed_stock=stock_after,
            row_version=OutletStock.row_version + 1,
            updated_at=now,
        )
    )

    # Event store (append-only)
    event = Event(
        outlet_id=outlet_id,
        stream_id=f"ingredient:{ingredient_id}",
        event_type="stock.ingredient_restock",
        event_data={
            "ingredient_id": ingredient_id,
            "outlet_id": outlet_id,
            "quantity": quantity,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "source": "ai_chat",
            "user_id": user_id,
        },
    )
    db.add(event)
    await db.commit()
    return True


# ─── Recipe Proposal Generator (SETUP_RECIPE intent) ─────────────────────────

RECIPE_EXPERT_SYSTEM_PROMPT = """Kamu adalah "Kopi Asisten" — ahli F&B Indonesia yang bantu pemilik kafe setup resep dengan bahasa casual.

TUGAS: dari pesan user, identify produk yang mau di-setup, lalu propose resep standar cafe Indonesia.

OUTPUT WAJIB 2 BAGIAN:
1. Penjelasan ramah casual (max 4 kalimat) — list bahan + estimasi HPP
2. Blok JSON structured — dipakai sistem untuk eksekusi, TIDAK ditampilkan ke user

KNOWLEDGE BASE harga market Indonesia (average 2025-2026):
- Kopi Arabica bubuk: Rp 120.000/kg | Kopi Robusta bubuk: Rp 80.000/kg
- Susu UHT Full Cream: Rp 15.000/liter | Susu Evaporasi: Rp 18.000/liter
- Gula pasir: Rp 14.000/kg | Gula aren cair: Rp 25.000/kg | Gula aren bubuk: Rp 45.000/kg
- Bubuk Matcha: Rp 180.000/kg | Bubuk Coklat: Rp 80.000/kg | Bubuk Red Velvet: Rp 120.000/kg
- Bubuk Taro: Rp 90.000/kg | Bubuk Caramel: Rp 100.000/kg
- Es batu: Rp 2.000/kg | Air mineral: Rp 3.000/liter
- Tea bag (grosir): Rp 500/pcs | Daun teh: Rp 40.000/kg
- Sirup rasa (vanilla/hazelnut/caramel): Rp 35.000/liter
- Whipping cream: Rp 60.000/liter | Butter: Rp 80.000/kg
- Telur ayam: Rp 28.000/kg (Rp 1.800/butir)
- Roti burger bun / croissant: Rp 5.000/pcs
- Keju mozzarella: Rp 90.000/kg | Keju parmesan: Rp 120.000/kg

RESEP STANDAR CAFE INDONESIA (per 1 porsi):
- Kopi Susu Gula Aren: 15g kopi arabica + 150ml susu UHT + 20g gula aren cair
- Kopi Hitam / Americano: 18g kopi + 200ml air
- Es Kopi Susu: 15g kopi + 120ml susu UHT + 15g gula pasir + 30g es batu
- Cappuccino: 18g kopi + 150ml susu UHT
- Latte: 18g kopi + 200ml susu UHT
- Matcha Latte: 3g bubuk matcha + 200ml susu UHT + 15g gula pasir
- Es Matcha Latte: 3g matcha + 150ml susu + 15g gula + 30g es batu
- Red Velvet Latte: 15g bubuk red velvet + 200ml susu UHT + 10g gula
- Taro Latte: 20g bubuk taro + 200ml susu UHT + 10g gula
- Es Teh Manis: 1 tea bag + 200ml air + 20g gula pasir
- Teh Tawar: 1 tea bag + 250ml air
- Teh Tarik: 1 tea bag + 100ml susu UHT + 100ml air + 15g gula
- Kopi Vietnam Drip: 20g kopi robusta + 150ml air + 40ml susu kental

FORMAT JSON (exactly between <RECIPE_PROPOSAL> tags, no markdown fences inside):
<RECIPE_PROPOSAL>
{
  "product_name": "Kopi Susu Gula Aren",
  "ingredients": [
    {"name": "Kopi Arabica Bubuk", "qty": 15, "unit": "gram", "buy_price": 120000, "buy_qty": 1000},
    {"name": "Susu UHT Full Cream", "qty": 150, "unit": "ml", "buy_price": 15000, "buy_qty": 1000},
    {"name": "Gula Aren Cair", "qty": 20, "unit": "gram", "buy_price": 25000, "buy_qty": 1000}
  ],
  "hpp_estimate": 4550,
  "suggested_price_range": [20000, 28000]
}
</RECIPE_PROPOSAL>

ATURAN JSON:
- unit HANYA: "gram" | "ml" | "pcs" | "bungkus"
- qty + buy_qty dalam base_unit (gram/ml/pcs). Jangan pake kg/liter di field ini.
- buy_price = harga beli dalam Rupiah (integer).
- hpp_estimate = integer total modal per 1 porsi.
- suggested_price_range = [min, max] integer.

ATURAN RESPONSE TEXT:
- Bahasa Indonesia casual (pake "gue" atau "kamu" fleksibel). Hangat dan supportive.
- Tampilkan bahan dengan bullet **tebal** nama bahan + qty + estimasi harga per porsi.
- Sebut HPP total + range harga jual umum.
- Akhir: "Mau gue bikinin otomatis? Klik tombol di bawah."
- JANGAN pake tabel, JANGAN pake emoji berlebihan (max 1-2 emoji subtle).

KALAU PRODUK GAK JELAS dari pesan user (contoh: cuma bilang "setup resep"), JANGAN generate JSON. Balas: "Produk apa yang mau kamu set resepnya? Contoh: 'setup resep kopi susu gula aren'."

KALAU PRODUK di luar knowledge base (misalnya menu unik cafe), tetap propose berdasarkan perkiraan bahan umum Indonesia yang masuk akal.
"""


async def generate_recipe_proposal(
    message: str,
    outlet_id: str,
    tenant_id: str,
    outlet_name: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Generate recipe proposal via Haiku.
    Yields SSE-ready text chunks dengan embedded <RECIPE_PROPOSAL> block.
    Caller handle 'done' event setelah generator selesai.
    """
    if not settings.ANTHROPIC_API_KEY:
        yield "Maaf, fitur AI belum dikonfigurasi. Hubungi admin."
        return

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,  # proposal text + JSON block
            system=RECIPE_EXPERT_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Outlet: {outlet_name}\n\nPermintaan user: {message}",
            }],
        ) as stream:
            async for text_chunk in stream.text_stream:
                yield text_chunk

            final_msg = await stream.get_final_message()
            # Tokens usage diserap caller via separate channel
            yield f"\n\n[__TOKENS__:{final_msg.usage.input_tokens + final_msg.usage.output_tokens}]"

    except Exception as e:
        logger.error(f"Recipe proposal generation error: {e}")
        yield "Maaf, terjadi gangguan saat generate resep. Coba lagi dalam beberapa saat."


def classify_task_complexity(message: str) -> str:
    """
    DEPRECATED — semua request pakai Haiku 4.5. Function ini tetap ada untuk
    backward-compat dengan caller yang masih manggil, tapi return value gak
    ngaruh lagi ke get_model_for_tier().
    """
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
    from backend.models.reservation import Reservation, ReservationSettings, Table

    today = datetime.now(timezone.utc).date()
    start_today = datetime.combine(today, dt_time.min).replace(tzinfo=timezone.utc)
    start_week = start_today - timedelta(days=6)

    try:
        # Set tenant schema
        await db.execute(text(f'SET search_path TO "{tenant_id}", public'))

        # Get brand_id + stock_mode from outlet
        from backend.models.outlet import Outlet
        outlet_row = await db.execute(
            select(Outlet.brand_id, Outlet.stock_mode).where(Outlet.id == outlet_id)
        )
        outlet_info = outlet_row.first()
        brand_id = outlet_info.brand_id if outlet_info else None
        stock_mode = (outlet_info.stock_mode if outlet_info else "simple") or "simple"

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

        # 4. Stok kritis — recipe mode pakai compute_recipe_stock, simple pakai stock_qty
        low_list = []
        if stock_mode == "recipe":
            # Recipe mode: hitung porsi dari stok bahan baku
            from backend.api.routes.products import compute_recipe_stock
            import math
            stock_products = await db.execute(
                select(Product.id, Product.name)
                .where(
                    Product.brand_id == brand_id,
                    Product.stock_enabled == True,
                    Product.deleted_at.is_(None),
                )
            )
            stock_prods = stock_products.all()
            if stock_prods:
                prod_ids = [p.id for p in stock_prods]
                recipe_stocks = await compute_recipe_stock(db, UUID(outlet_id) if isinstance(outlet_id, str) else outlet_id, prod_ids)
                prod_name_map = {p.id: p.name for p in stock_prods}
                for pid, portions in recipe_stocks.items():
                    if portions < 5:
                        low_list.append(f"{prod_name_map.get(pid, '?')} (sisa {portions} porsi)")
                low_list = low_list[:5]
        else:
            # Simple mode: langsung dari product.stock_qty
            low_stock = await db.execute(
                select(Product.name, Product.stock_qty)
                .where(
                    Product.brand_id == brand_id,
                    Product.stock_enabled == True,
                    Product.stock_qty < 5,
                    Product.stock_qty >= 0,
                    Product.deleted_at.is_(None),
                )
                .limit(5)
            )
            low_list = [
                f"{r.name} (sisa {int(r.stock_qty)})" for r in low_stock.all()
            ]

        # 4b. Stok bahan baku (ingredient stock) — untuk jawab "berapa stok X?"
        ingredient_stock_list = []
        if stock_mode == "recipe":
            from backend.models.ingredient import Ingredient
            ing_stocks = await db.execute(
                select(Ingredient.name, Ingredient.base_unit, OutletStock.computed_stock)
                .select_from(OutletStock)
                .join(Ingredient, OutletStock.ingredient_id == Ingredient.id)
                .where(
                    OutletStock.outlet_id == outlet_id,
                    OutletStock.deleted_at.is_(None),
                    Ingredient.deleted_at.is_(None),
                )
                .order_by(Ingredient.name)
                .limit(20)
            )
            for r in ing_stocks.all():
                stock_val = float(r.computed_stock) if r.computed_stock else 0
                # Format: integer untuk gram/ml, 1 decimal untuk kg/liter
                unit = r.base_unit or ''
                if unit in ('kg', 'liter', 'l'):
                    stock_str = f"{stock_val:.1f}"
                else:
                    stock_str = f"{int(stock_val)}"
                ingredient_stock_list.append(f"{r.name}: {stock_str} {unit}")

        # 4c. Daftar semua produk/menu — supaya AI tau apa aja yang dijual
        all_products_q = await db.execute(
            select(Product.name, Product.base_price, Product.stock_enabled, Product.stock_qty, Product.is_active)
            .where(
                Product.brand_id == brand_id,
                Product.deleted_at.is_(None),
            )
            .order_by(Product.name)
            .limit(30)
        )
        all_products = all_products_q.all()
        product_menu_list = []
        for p in all_products:
            status = "aktif" if p.is_active else "nonaktif"
            product_menu_list.append(f"{p.name} — Rp{float(p.base_price):,.0f} ({status})")

        # 5. Event-sourced insights (order patterns, cancel rate, payment methods)
        from backend.models.event import Event

        # Cancel rate today
        cancel_count_q = await db.execute(
            select(func.count(Event.id)).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.cancelled",
                Event.created_at >= start_today,
            )
        )
        cancel_count = cancel_count_q.scalar() or 0

        # Payment method breakdown today (from events)
        method_col = Event.event_data["method"].astext
        pay_methods_q = await db.execute(
            select(
                method_col.label("method"),
                func.count(Event.id).label("cnt"),
                func.coalesce(func.sum(Event.event_data["amount_paid"].astext.cast(sqlalchemy.Numeric)), 0).label("total"),
            ).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "payment.completed",
                Event.created_at >= start_today,
            ).group_by(method_col)
        )
        pay_breakdown = []
        try:
            for r in pay_methods_q.all():
                pay_breakdown.append(f"{r.method}: {r.cnt}x (Rp{float(r.total):,.0f})")
        except Exception:
            pass

        # Storefront vs POS ratio today
        source_col = Event.event_data["source"].astext
        source_q = await db.execute(
            select(
                source_col.label("source"),
                func.count(Event.id).label("cnt"),
            ).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.created",
                Event.created_at >= start_today,
            ).group_by(source_col)
        )
        source_breakdown = []
        try:
            for r in source_q.all():
                source_breakdown.append(f"{r.source}: {r.cnt} order")
        except Exception:
            pass

        # Dine-in vs takeaway breakdown today
        order_type_col = Event.event_data["order_type"].astext
        otype_q = await db.execute(
            select(
                order_type_col.label("otype"),
                func.count(Event.id).label("cnt"),
            ).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.created",
                Event.created_at >= start_today,
            ).group_by(order_type_col)
        )
        order_type_breakdown = []
        try:
            type_labels = {"dine_in": "Dine In", "takeaway": "Takeaway", "delivery": "Delivery"}
            for r in otype_q.all():
                label = type_labels.get(r.otype, r.otype)
                order_type_breakdown.append(f"{label}: {r.cnt}")
        except Exception:
            pass

        # Peak hour (from order.created events this week)
        peak_hour_q = await db.execute(
            select(
                func.extract("hour", Event.created_at).label("hour"),
                func.count(Event.id).label("cnt"),
            ).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.created",
                Event.created_at >= start_week,
            ).group_by(func.extract("hour", Event.created_at))
            .order_by(func.count(Event.id).desc())
            .limit(3)
        )
        peak_hours = []
        try:
            for r in peak_hour_q.all():
                h = int(r.hour) + 7  # UTC → WIB
                if h >= 24:
                    h -= 24
                peak_hours.append(f"{h:02d}:00 ({r.cnt} order)")
        except Exception:
            pass

        # 6. Reservation data
        res_settings_row = await db.execute(
            select(ReservationSettings).where(
                ReservationSettings.outlet_id == outlet_id,
                ReservationSettings.deleted_at.is_(None),
            )
        )
        res_settings = res_settings_row.scalar_one_or_none()

        # Today's reservations
        today_reservations = await db.execute(
            select(func.count(Reservation.id)).where(
                Reservation.outlet_id == outlet_id,
                Reservation.reservation_date == today,
                Reservation.status.in_(["pending", "confirmed", "seated"]),
                Reservation.deleted_at.is_(None),
            )
        )
        reservation_count = today_reservations.scalar() or 0

        # Available tables
        total_tables_q = await db.execute(
            select(func.count(Table.id)).where(
                Table.outlet_id == outlet_id,
                Table.is_active == True,
                Table.deleted_at.is_(None),
            )
        )
        total_tables = total_tables_q.scalar() or 0

        available_tables_q = await db.execute(
            select(func.count(Table.id)).where(
                Table.outlet_id == outlet_id,
                Table.is_active == True,
                Table.status == "available",
                Table.deleted_at.is_(None),
            )
        )
        available_tables = available_tables_q.scalar() or 0

        # Tab/Bon info (Pro feature) — active tabs + today stats + table occupancy
        tab_info = ""
        try:
            from backend.models.tab import Tab as TabModel

            # 1. Active tabs
            open_tabs_q = await db.execute(
                select(
                    TabModel.tab_number,
                    TabModel.status,
                    TabModel.total_amount,
                    TabModel.guest_count,
                    TabModel.table_id,
                    TabModel.opened_at,
                ).where(
                    TabModel.outlet_id == outlet_id,
                    TabModel.status.in_(['open', 'asking_bill', 'splitting']),
                    TabModel.deleted_at.is_(None),
                )
            )
            open_tabs = open_tabs_q.all()

            # 2. Today's tab stats from event store
            tab_opened_today = await db.execute(
                select(func.count(Event.id)).where(
                    Event.outlet_id == outlet_id,
                    Event.event_type == "tab.opened",
                    Event.created_at >= start_today,
                )
            )
            tabs_opened_count = tab_opened_today.scalar() or 0

            tab_paid_today_q = await db.execute(
                select(
                    func.count(Event.id),
                    func.sum(Event.event_data["total_amount"].astext.cast(sqlalchemy.Numeric)),
                ).where(
                    Event.outlet_id == outlet_id,
                    Event.event_type == "tab.paid",
                    Event.created_at >= start_today,
                )
            )
            tab_paid_row = tab_paid_today_q.one()
            tabs_paid_count = tab_paid_row[0] or 0
            tabs_revenue = float(tab_paid_row[1] or 0)

            # 3. Average tab duration (opened → paid) from events today
            avg_duration_str = ""
            try:
                avg_q = await db.execute(text("""
                    SELECT AVG(EXTRACT(EPOCH FROM (closed.created_at - opened.created_at))) / 60 as avg_min
                    FROM events opened
                    JOIN events closed ON closed.stream_id = opened.stream_id
                        AND closed.event_type = 'tab.paid'
                    WHERE opened.outlet_id = :oid
                        AND opened.event_type = 'tab.opened'
                        AND opened.created_at >= :start
                """), {"oid": str(outlet_id), "start": start_today})
                avg_min = avg_q.scalar()
                if avg_min and avg_min > 0:
                    avg_duration_str = f"\n- Rata-rata durasi tab: {avg_min:.0f} menit (buka → bayar)"
            except Exception:
                pass

            # 4. Table occupancy detail
            table_detail_q = await db.execute(
                select(
                    Table.name,
                    Table.status,
                ).where(
                    Table.outlet_id == outlet_id,
                    Table.is_active == True,
                    Table.deleted_at.is_(None),
                ).order_by(Table.name)
            )
            all_tables = table_detail_q.all()
            occupied_names = [t.name for t in all_tables if t.status == 'occupied']
            available_names = [t.name for t in all_tables if t.status == 'available']

            # 5. Tab event patterns (cancellations, splits, merges today)
            tab_event_stats_q = await db.execute(
                select(
                    Event.event_type,
                    func.count(Event.id),
                ).where(
                    Event.outlet_id == outlet_id,
                    Event.event_type.like("tab.%"),
                    Event.created_at >= start_today,
                ).group_by(Event.event_type)
            )
            tab_event_map = {r[0]: r[1] for r in tab_event_stats_q.all()}

            # Build tab info string
            tab_lines_parts = []

            # Stats
            tab_lines_parts.append(f"\nTAB/BON HARI INI:")
            tab_lines_parts.append(f"- Dibuka: {tabs_opened_count} tab | Selesai dibayar: {tabs_paid_count} tab")
            if tabs_revenue > 0:
                tab_lines_parts.append(f"- Revenue via tab: Rp{tabs_revenue:,.0f}")
            if avg_duration_str:
                tab_lines_parts.append(avg_duration_str.strip())
            cancel_count_tab = tab_event_map.get("tab.cancelled", 0)
            merge_count_tab = tab_event_map.get("tab.merged", 0)
            split_count_tab = tab_event_map.get("tab.split", 0)
            asking_bill_events = tab_event_map.get("tab.asking_bill", 0)
            if cancel_count_tab or merge_count_tab or split_count_tab:
                parts = []
                if split_count_tab:
                    parts.append(f"{split_count_tab} split")
                if merge_count_tab:
                    parts.append(f"{merge_count_tab} gabung meja")
                if cancel_count_tab:
                    parts.append(f"{cancel_count_tab} dibatalkan")
                tab_lines_parts.append(f"- Aktivitas: {', '.join(parts)}")

            # Active tabs
            if open_tabs:
                asking_bill_count = 0
                tab_detail_lines = []
                now = datetime.now(timezone.utc)
                for t in open_tabs:
                    status_label = {"open": "aktif", "asking_bill": "MINTA BILL", "splitting": "split bill"}.get(t.status, t.status)
                    duration = ""
                    if t.opened_at:
                        mins = int((now - t.opened_at).total_seconds() / 60)
                        duration = f", {mins} menit"
                    # Find table name
                    tbl_name = "?"
                    for tbl in all_tables:
                        if t.table_id and tbl.name:
                            # Match by checking occupied tables
                            pass
                    tab_detail_lines.append(f"{t.tab_number} ({status_label}, {t.guest_count} tamu, Rp{float(t.total_amount):,.0f}{duration})")
                    if t.status == 'asking_bill':
                        asking_bill_count += 1
                tab_lines_parts.append(f"\nTAB AKTIF ({len(open_tabs)} tab):")
                for line in tab_detail_lines:
                    tab_lines_parts.append(f"- {line}")
                if asking_bill_count > 0:
                    tab_lines_parts.append(f"⚠️ {asking_bill_count} tab MINTA BILL — perlu segera diproses!")

            # Table occupancy
            if all_tables:
                tab_lines_parts.append(f"\nMEJA ({len(available_names)}/{len(all_tables)} tersedia):")
                if occupied_names:
                    tab_lines_parts.append(f"- Terisi: {', '.join(occupied_names)}")
                if available_names:
                    tab_lines_parts.append(f"- Kosong: {', '.join(available_names)}")

            tab_info = "\n".join(tab_lines_parts)
        except Exception:
            pass

        reservation_info = ""
        if res_settings and res_settings.is_enabled:
            open_h = res_settings.opening_hour.strftime("%H:%M") if res_settings.opening_hour else "08:00"
            close_h = res_settings.closing_hour.strftime("%H:%M") if res_settings.closing_hour else "22:00"
            reservation_info = f"""
RESERVASI:
- Jam operasional: {open_h} - {close_h}
- Reservasi hari ini: {reservation_count} booking aktif
- Meja: {available_tables}/{total_tables} tersedia
- Max booking advance: {res_settings.max_advance_days} hari
- Auto confirm: {"ya" if res_settings.auto_confirm else "perlu konfirmasi manual"}"""
        elif total_tables > 0:
            reservation_info = f"""
MEJA:
- Total: {total_tables} meja, {available_tables} tersedia sekarang
- Reservasi: belum diaktifkan"""

        reservation_info += tab_info

    except Exception as e:
        logger.warning(f"Context build error: {e}")
        revenue_today = revenue_week = 0.0
        order_count_today = order_count_week = 0
        top_list = []
        low_list = []
        ingredient_stock_list = []
        product_menu_list = []
        reservation_info = ""
        cancel_count = 0
        pay_breakdown = []
        source_breakdown = []
        order_type_breakdown = []
        peak_hours = []

    today_str = today.strftime("%d %B %Y")
    context = f"""Kamu adalah asisten AI Kasira untuk {outlet_name} di Indonesia.

SIAPA USER LO: owner/kasir UMKM Indonesia. Bisnisnya bisa apa aja — cafe, resto, toko sepeda listrik, toko vape, fashion, kelontong, laundry, dll. LIHAT daftar produk di bawah untuk tau jenis bisnisnya, lalu jawab sesuai konteks itu. Banyak user baru pertama kali jualan dan butuh bimbingan konkret.

Tanggal: {today_str}

PRODUK YANG DIJUAL:
{chr(10).join("- " + p for p in product_menu_list) if product_menu_list else "- Belum ada produk"}

DATA BISNIS HARI INI:
- Omzet: Rp{revenue_today:,.0f} dari {order_count_today} transaksi
- Produk terlaris: {", ".join(top_list) if top_list else "belum ada transaksi"}

DATA 7 HARI TERAKHIR:
- Total omzet: Rp{revenue_week:,.0f} dari {order_count_week} transaksi
- Rata-rata/hari: Rp{revenue_week/7:,.0f}

STOK KRITIS (perlu restock):
{chr(10).join("- " + s for s in low_list) if low_list else "- Semua stok aman"}
{"" if not ingredient_stock_list else chr(10) + "STOK BAHAN BAKU (angka sudah dalam satuan yang tertulis, JANGAN ubah format):" + chr(10) + chr(10).join("- " + s for s in ingredient_stock_list)}

INSIGHT OPERASIONAL:
- Order dibatalkan hari ini: {cancel_count}
- Tipe order: {", ".join(order_type_breakdown) if order_type_breakdown else "belum ada data"}
- Sumber order: {", ".join(source_breakdown) if source_breakdown else "belum ada data"}
- Metode bayar: {", ".join(pay_breakdown) if pay_breakdown else "belum ada data"}
- Jam tersibuk (7 hari): {", ".join(peak_hours) if peak_hours else "belum cukup data"}
{reservation_info}
GAYA JAWAB:
- Bahasa Indonesia casual tapi sopan, jangan bertele-tele
- Angka dalam format Rupiah (Rp x.xxx)
- Kalau data outlet ada di atas, pakai itu (omzet, stok, HPP, tab, meja)
- Kalau user nanya hal umum yang gak ada datanya, JAWAB dari pengetahuan umum — jangan tolak. Contoh:
  * "gula putih untuk 1 es teh biasanya berapa gr" → kasih angka konkret (misal 15-20g) + tips
  * "harga jual pod vape yang wajar" → kasih range margin 30-50% + tips pricing
  * "cara jaga stok sparepart sepeda listrik" → kasih tips inventory retail
  * "cara bikin latte art" → jelasin step
- User banyak yang baru belajar — kasih contoh konkret (gram/ml/persen/range harga), bukan jawaban abstrak
- Untuk restock: bisa langsung eksekusi via chat (contoh: "restock gula 5kg")
- Untuk HPP: jelasin komponen biaya, margin, dampak perubahan harga
- Untuk tab/meja: laporkan tab aktif, yang minta bill, durasi, meja terisi

BATASAN:
- Tolak topik benar-benar di luar bisnis (politik, medis serius, curhat pribadi, coding, hukum). Untuk ini bilang sopan: "Aku fokus bantu bisnis lo. Coba tanya yang lain ya."
- Kalau user minta ubah data (harga, produk, diskon, promo) — arahin ke menu settings app, jangan ngaku bisa eksekusi
- Kalau gak tau jawabannya, bilang jujur gak tau — jangan ngarang angka bisnis"""

    # Knowledge graph context (non-blocking)
    kg_context = ""
    try:
        from backend.services.knowledge_graph_service import build_ai_context_from_graph
        kg_context = await build_ai_context_from_graph(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            db=db,
            outlet_id=UUID(outlet_id) if isinstance(outlet_id, str) else outlet_id,
        )
    except Exception as e:
        logger.debug(f"KG context skipped: {e}")

    context += kg_context

    # Cross-tenant benchmark context (platform intelligence)
    platform_context = ""
    try:
        from backend.services.platform_intelligence import build_cross_tenant_context
        platform_context = await build_cross_tenant_context(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            outlet_id=UUID(outlet_id) if isinstance(outlet_id, str) else outlet_id,
            db=db,
        )
    except Exception as e:
        logger.debug(f"Platform context skipped: {e}")

    context += platform_context

    # Menu Engineering context (BCG matrix + combos)
    menu_eng_context = ""
    try:
        from backend.services.menu_engineering_service import build_menu_engineering_context
        menu_eng_context = await build_menu_engineering_context(
            db=db,
            brand_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            outlet_id=UUID(outlet_id) if isinstance(outlet_id, str) else outlet_id,
        )
    except Exception as e:
        logger.debug(f"Menu engineering context skipped: {e}")

    context += menu_eng_context

    # Layer 4: Embedding-based RAG context is NOT cached here.
    # It's injected per-query in stream_ai_response() for relevance.

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
    user_id: str = "",
) -> AsyncGenerator[str, None]:
    """
    Generator untuk SSE stream.
    Yields: "data: {...}\n\n" strings
    """

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # 1. Classify intent — SETUP_RECIPE / RESTOCK = actionable, selain itu langsung ke Claude
    intent = classify_intent(message)

    if intent == INTENT_SETUP_RECIPE:
        # AI propose resep via Haiku — user confirm di dashboard lalu apply
        tokens_used = 0
        async for chunk in generate_recipe_proposal(
            message=message,
            outlet_id=outlet_id,
            tenant_id=tenant_id,
            outlet_name=outlet_name,
            db=db,
        ):
            # Tokens info di-strip dari chunk, propagate ke done event
            if chunk.startswith("\n\n[__TOKENS__:"):
                try:
                    tokens_used = int(chunk.split(":")[1].rstrip("]\n "))
                except Exception:
                    pass
                continue
            yield sse({"type": "chunk", "content": chunk})

        yield sse({
            "type": "done",
            "intent": INTENT_SETUP_RECIPE,
            "tokens_used": tokens_used,
            "model": "claude-haiku-4-5-20251001",
        })
        return

    if intent == INTENT_RESTOCK:
        # Parse and execute restock
        result = await parse_restock_intent(message, outlet_id, tenant_id, db)
        if not result["success"]:
            # Parse gagal (mis. user gak nyebut bahan/qty spesifik) → fall through ke Claude
            # supaya AI bisa ask clarifying question dengan context KG + stok kritis.
            # Intent tetap CHAT, error info diinjeksi ke context.
            intent = INTENT_CHAT
            message = (
                f"{message}\n\n"
                f"[CONTEXT: User mau restock tapi parse gagal — {result['error']}. "
                f"Tanya balik bahan mana + jumlah berapa. Tunjukin stok kritis dari context kalau ada.]"
            )
        else:
            # Execute restock
            ok = await execute_restock(
                ingredient_id=result["ingredient_id"],
                outlet_id=outlet_id,
                quantity=result["quantity"],
                user_id=user_id,
                db=db,
            )
            if ok:
                qty_display = f"{result['quantity']:,.0f}" if result['quantity'] == int(result['quantity']) else f"{result['quantity']:,.1f}"
                yield sse({"type": "chunk", "content": (
                    f"Stok **{result['ingredient_name']}** berhasil ditambah **{qty_display} {result['unit']}**.\n\n"
                    f"Stok sekarang: **{result['stock_after']:,.0f} {result['unit']}**"
                )})
            else:
                yield sse({"type": "chunk", "content": f"Gagal restock {result['ingredient_name']}. Coba lagi atau restock manual di halaman Bahan Baku."})

            # Invalidate context cache (stock changed)
            try:
                await redis_client.delete(f"ai:context:{outlet_id}")
            except Exception:
                pass

            yield sse({"type": "done", "intent": INTENT_RESTOCK, "tokens_used": 0})
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

    # 3b. Layer 4 RAG: embed user query, find relevant products (per-query, not cached)
    try:
        from backend.services.embedding_service import enrich_ai_context
        from backend.models.outlet import Outlet
        outlet_row = await db.execute(
            select(Outlet.brand_id).where(Outlet.id == outlet_id)
        )
        brand_id = outlet_row.scalar()
        if brand_id:
            rag_context = await enrich_ai_context(message, brand_id, db)
            if rag_context:
                system_prompt += rag_context
    except Exception as e:
        logger.debug(f"RAG enrichment skipped: {e}")

    # 4. Pilih model (Rule #25/#26)
    task_complexity = classify_task_complexity(message)
    model = await get_model_for_tier(tier, task_complexity, tenant_id=tenant_id)

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
