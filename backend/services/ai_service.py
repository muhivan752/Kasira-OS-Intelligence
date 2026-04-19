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
INTENT_MENU_BULK = "MENU_BULK"
INTENT_PRICING_COACH = "PRICING_COACH"

# Pricing coach — pakai Sonnet karena butuh reasoning multi-faktor
# (HPP vs benchmark, margin target, positioning, elasticity).
PRICING_COACH_KEYWORDS = [
    "hpp",
    "margin",
    "profit",
    "laba bersih",
    "harga jual",
    "jual berapa",
    "wajar harga",
    "harga wajar",
    "wajar jual",
    "kemahalan",
    "kemurahan",
    "overprice",
    "underprice",
    "pricing",
    "cost produk",
    "naikin harga",
    "turunin harga",
    "harga kompetitor",
    "cek margin",
    "analisa harga",
    "rekomendasi harga",
]

# Batas Sonnet per tenant/hari (mahal — limit agresif)
SONNET_PER_TENANT_DAILY = 5
SONNET_MODEL_ID = "claude-sonnet-4-5-20250929"
HAIKU_MODEL_ID = "claude-haiku-4-5-20251001"

# Keyword detection hanya untuk RESTOCK (actionable — langsung update DB).
# Selain itu semua pertanyaan → CHAT → Claude yang jawab via system prompt.
RESTOCK_KEYWORDS = [
    "restock", "tambah stok", "masukin stok", "isi stok", "stok masuk",
    "baru beli", "beli bahan", "datang bahan", "terima bahan",
    "update stok", "nambah stok", "restok",
    "tambah bahan", "tambahin bahan", "nambah bahan", "tambahkan bahan",
    "stok bahan", "isi bahan", "masukin bahan", "masukkan bahan",
]

# SETUP_RECIPE action+target word pairs (flexible match — handle variasi
# "buatkan resep", "bikinin resep", "tolong setup resep", dll).
SETUP_RECIPE_ACTION_WORDS = [
    "setup", "bikin", "bikinin", "buat", "buatkan", "buatin",
    "atur", "susun", "tambah", "tambahin", "tambahkan",
    "rancang", "rancangin", "siapin", "siapkan",
    "tolong buat", "tolong bikin", "tolong setup",
    "minta", "mau",
]
SETUP_RECIPE_TARGET_WORDS = [
    "resep", "komposisi", "recipe", "isi per porsi", "racikan",
]

# MENU_BULK — user minta AI susun daftar menu (multi-product).
# Detect kalau "menu" muncul bareng indikator bulk (angka, quantifier,
# atau phrase khas).
MENU_BULK_PHRASE_INDICATORS = [
    "paket menu", "daftar menu", "rekomendasi menu", "usulan menu",
    "saran menu", "ide menu", "suggest menu", "menu populer",
    "menu kekinian", "menu laris", "menu andalan", "menu lengkap",
    "banyak menu", "beberapa menu",
]


# ─── Model Selector (Rule #25, #26) ───────────────────────────────────────────

async def get_model_for_tier(tier: str, task: str = "routine", tenant_id: str = None, intent: str = INTENT_CHAT) -> str:
    """
    Pilih Claude model berdasarkan intent.

    - PRICING_COACH → Sonnet 4.5 (reasoning multi-faktor: HPP vs benchmark,
      margin target, positioning, elasticity) — max 5x/tenant/hari.
    - Selain itu → Haiku 4.5 (business analytics standard, context pre-built).

    Sonnet ~4x biaya Haiku. Dipakai sparingly untuk task yang genuinely butuh
    reasoning mendalam.
    """
    if intent == INTENT_PRICING_COACH:
        return SONNET_MODEL_ID
    return HAIKU_MODEL_ID


# ─── Intent Classifier (Rule #54, #56) ────────────────────────────────────────

def classify_intent(message: str) -> str:
    """
    Klasifikasi intent pesan owner.
    Returns:
      - MENU_BULK (AI propose N products + recipes)
      - SETUP_RECIPE (AI propose single recipe)
      - RESTOCK (actionable — update DB langsung)
      - CHAT (default — Claude jawab)

    Order matters: MENU_BULK > SETUP_RECIPE > RESTOCK > CHAT.
    Sebab "bikinin 10 menu kopi" punya action + "menu" tapi bukan
    target "resep" — harus ke MENU_BULK, bukan CHAT.
    """
    import re as _re
    msg_lower = message.lower()

    has_action = any(aw in msg_lower for aw in SETUP_RECIPE_ACTION_WORDS)

    # MENU_BULK detection — "menu" + (action OR count OR phrase indicator)
    if "menu" in msg_lower:
        has_phrase = any(p in msg_lower for p in MENU_BULK_PHRASE_INDICATORS)
        has_count = bool(_re.search(r'\b\d+\s+menu\b', msg_lower))
        if has_phrase or (has_action and has_count) or (has_action and "menu" in msg_lower and "resep" not in msg_lower and "komposisi" not in msg_lower):
            # Last condition: user bilang "bikin menu kopi" tanpa spesifik
            # jumlah — tetap ke MENU_BULK, AI nanti propose default 5-8 item.
            return INTENT_MENU_BULK

    # SETUP_RECIPE (single)
    has_target = any(tw in msg_lower for tw in SETUP_RECIPE_TARGET_WORDS)
    if has_action and has_target:
        return INTENT_SETUP_RECIPE

    if any(kw in msg_lower for kw in RESTOCK_KEYWORDS):
        return INTENT_RESTOCK

    # PRICING_COACH — check last (karena keywords bisa overlap dengan CHAT biasa)
    if any(kw in msg_lower for kw in PRICING_COACH_KEYWORDS):
        return INTENT_PRICING_COACH

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

RECIPE_EXPERT_SYSTEM_PROMPT = """Kamu "Asisten Setup" — ahli UMKM Indonesia (F&B, retail, vape, dll) yang propose resep/komposisi bahan.

OUTPUT FORMAT WAJIB (super strict — user liat form editable, bukan text):

Baris 1: "Oke, ini tebakan gue. Sesuaiin sama kondisi usaha kamu, terus klik **Buat Resep**:"
Baris 2+: <RECIPE_PROPOSAL>JSON</RECIPE_PROPOSAL>

TIDAK ADA KALIMAT LAIN. Jangan list bahan di text — JSON sudah cover itu, UI render sebagai form editable. Jangan sebut HPP/modal di text — UI kalkulasi sendiri real-time.

FORMAT JSON (wajib valid, cuma dalam tag, no markdown fence):
{
  "product_name": "...",
  "ingredients": [
    {"name": "Kopi Arabica Bubuk", "qty": 15, "unit": "gram", "buy_price": 120000, "buy_qty": 1000, "initial_stock": 1000}
  ],
  "hpp_estimate": 4550,
  "suggested_price_range": [20000, 28000]
}

ATURAN JSON:
- unit HANYA: "gram" | "ml" | "pcs" | "bungkus"
- qty + buy_qty + initial_stock dalam base_unit (gram/ml/pcs). Jangan pake kg/liter.
- buy_price = integer IDR. hpp_estimate = integer. suggested_price_range = [min, max] integer.
- name gunakan Title Case (contoh: "Susu UHT Full Cream").
- initial_stock = ukuran package default di market Indonesia (contoh kopi/tepung 1000g, susu 1000ml, gula 500g,
  matcha 100g, es batu 2000g, tea bag 25pcs, telur 10pcs, roti bun 10pcs). Set berdasarkan UMUM BELI cafe.

HARGA MARKET INDONESIA (average 2025-2026, pakai sebagai default):
F&B:
- Kopi Arabica bubuk 120k/kg | Robusta 80k/kg | Kopi instant 60k/kg
- Susu UHT 15k/L | Evaporasi 18k/L | Kental manis 20k/kg | Bubuk susu 100k/kg
- Gula pasir 14k/kg | Gula aren cair 25k/kg | Gula aren bubuk 45k/kg
- Matcha bubuk 180k/kg | Coklat bubuk 80k/kg | Red velvet bubuk 120k/kg | Taro 90k/kg
- Sirup rasa 35k/L | Whipping cream 60k/L | Butter 80k/kg
- Tea bag 500/pcs | Daun teh 40k/kg | Air 3k/L | Es batu 2k/kg
- Nasi putih 10k/kg (modal) | Ayam 45k/kg | Telur 1800/butir | Sosis 30k/kg | Bumbu dasar 30k/kg
- Mie basah 15k/kg | Mie instant 3k/pcs | Saos sambal 25k/L | Kecap manis 20k/L
- Tepung 12k/kg | Minyak 18k/L | Terigu 13k/kg | Roti/bun 5k/pcs | Keju mozzarella 90k/kg

Retail/lainnya:
- E-liquid base 60k/L | Nikotin base 100k/L | Coil ready 8k/pcs
- Detergen 25k/L | Pewangi laundry 30k/L

KNOWLEDGE KOMPOSISI STANDAR (contoh — jadi base, adjust jika user minta variasi):
- Kopi Susu Gula Aren: 15g kopi arabica + 150ml susu UHT + 20g gula aren cair
- Americano: 18g kopi + 200ml air
- Es Kopi Susu: 15g kopi + 120ml susu + 15g gula + 30g es
- Cappuccino: 18g kopi + 150ml susu
- Matcha Latte: 3g matcha + 200ml susu + 15g gula
- Es Teh Manis: 1 tea bag + 200ml air + 20g gula
- Teh Tarik: 1 tea bag + 100ml susu + 100ml air + 15g gula
- Nasi Goreng: 150g nasi + 50g ayam + 1 telur + 30g bumbu + 10ml minyak
- Mie Ayam: 80g mie basah + 60g ayam + 30g bumbu + 5ml minyak
- E-liquid mangga: 30ml base + 3ml flavor mangga (jika vape)

KALAU PESAN USER GAK SEBUT PRODUK (misal cuma "setup resep"), TANPA JSON, balas pendek:
"Produk apa yang mau di-setup? Contoh: 'setup resep Kopi Susu Gula Aren'."

KALAU PRODUK di luar knowledge, tetap propose perkiraan masuk akal berdasarkan kategori (F&B/vape/retail).
"""


MENU_BULK_SYSTEM_PROMPT = """Kamu "Asisten Setup" — ahli UMKM Indonesia (F&B, retail, vape) yang bantu susun **daftar menu** lengkap untuk usaha.

TUGAS: propose 5-10 produk sesuai kategori bisnis user. Tiap produk ada: nama, harga jual estimasi, kategori, resep (bahan + qty).

OUTPUT FORMAT WAJIB (super strict):

Baris 1: "Nih proposal [N] menu untuk [kategori]. Edit dulu kalau ada yang kurang pas, terus klik **Buat Semua**:"
Baris 2+: <MENU_PROPOSAL>JSON</MENU_PROPOSAL>

TIDAK ADA KALIMAT LAIN. JANGAN list menu di text — JSON cover itu, UI render form editable.

FORMAT JSON (wajib valid):
{
  "business_type": "Coffee Shop Kekinian",
  "products": [
    {
      "name": "Kopi Susu Gula Aren",
      "suggested_price": 25000,
      "category_name": "Kopi Susu",
      "ingredients": [
        {"name": "Kopi Arabica Bubuk", "qty": 15, "unit": "gram", "buy_price": 120000, "buy_qty": 1000, "initial_stock": 1000},
        {"name": "Susu UHT Full Cream", "qty": 150, "unit": "ml", "buy_price": 15000, "buy_qty": 1000, "initial_stock": 1000},
        {"name": "Gula Aren Cair", "qty": 20, "unit": "gram", "buy_price": 25000, "buy_qty": 1000, "initial_stock": 500}
      ]
    }
    // ... total 5-10 produk
  ]
}

ATURAN:
- Jumlah produk: 5-10 (default 8 kalau user gak sebut angka). Kalau user minta "10 menu" → kasih tepat 10.
- unit HANYA: "gram" | "ml" | "pcs" | "bungkus"
- suggested_price integer IDR, realistic sesuai tier usaha (warteg cheaper, coffee shop kekinian 20-35rb).
- category_name: grouping logical (e.g., "Kopi", "Kopi Susu", "Tea & Matcha", "Makanan Berat").
- initial_stock = ukuran package umum beli cafe (kopi 1000g, susu 1000ml, gula 500g, matcha 100g, es batu 2000g,
  tea bag 25pcs, telur 10pcs, roti bun 10pcs). Merchant bisa edit — set yang realistic.

HARGA MARKET INDONESIA (avg 2025-2026):
F&B: Kopi Arabica 120k/kg | Robusta 80k/kg | Susu UHT 15k/L | Gula pasir 14k/kg | Gula aren 25k/kg |
Matcha 180k/kg | Tea bag 500/pcs | Air 3k/L | Es batu 2k/kg | Sirup 35k/L | Whip cream 60k/L |
Nasi 10k/kg | Ayam 45k/kg | Telur 1800/butir | Sosis 30k/kg | Bumbu 30k/kg | Mie 15k/kg |
Tepung 12k/kg | Minyak 18k/L | Keju moz 90k/kg | Roti/bun 5k/pcs
Retail: E-liquid base 60k/L | Coil 8k/pcs | Detergen 25k/L

TEMPLATE MENU POPULER (sebagai dasar, adjust sesuai request):
- **Coffee Shop Kekinian**: Americano, Kopi Susu Gula Aren, Es Kopi Susu, Cappuccino, Latte, Matcha Latte, Red Velvet Latte, Es Teh Tawar, Croissant, Sandwich
- **Warung Kopi Klasik**: Kopi Hitam, Kopi Susu, Kopi Tubruk, Teh Manis, Teh Tawar, Es Teh, Indomie Rebus, Nasi Goreng, Mie Goreng, Roti Bakar
- **Warteg / Rumah Makan**: Nasi Putih, Ayam Goreng, Telur Dadar, Sayur Asem, Tahu Tempe, Sambal, Teh Manis, Es Jeruk
- **Dessert Cafe**: Es Campur, Puding Coklat, Gelato Vanilla, Smoothie Buah, Teh Tarik, Matcha Latte
- **Vape Shop**: E-liquid Mangga, E-liquid Strawberry, E-liquid Mint, Coil Kanthal, Battery 18650

KALAU USER GAK SEBUT KATEGORI BISNIS: default "Coffee Shop Kekinian" 8 menu.
KALAU USER SEBUT KATEGORI: pilih template yang cocok atau adjust.
"""


async def generate_menu_proposal(
    message: str,
    outlet_id: str,
    tenant_id: str,
    outlet_name: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Generate multi-product menu proposal via Haiku.
    Yields SSE-ready text chunks dengan embedded <MENU_PROPOSAL> block.
    """
    if not settings.ANTHROPIC_API_KEY:
        yield "Maaf, fitur AI belum dikonfigurasi. Hubungi admin."
        return

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=3500,  # 10 produk × 3-5 ingredient = butuh banyak token
            system=MENU_BULK_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Outlet: {outlet_name}\n\nPermintaan user: {message}",
            }],
        ) as stream:
            async for text_chunk in stream.text_stream:
                yield text_chunk

            final_msg = await stream.get_final_message()
            yield f"\n\n[__TOKENS__:{final_msg.usage.input_tokens + final_msg.usage.output_tokens}]"

    except Exception as e:
        logger.error(f"Menu proposal generation error: {e}")
        yield "Maaf, terjadi gangguan saat generate menu. Coba lagi dalam beberapa saat."


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
            max_tokens=1200,  # proposal text pendek + JSON block — buffer aman
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


# ─── Pricing Coach Helpers ────────────────────────────────────────────────────

async def build_pricing_context(outlet_id: str, db: AsyncSession) -> str:
    """
    Hitung HPP + margin per produk outlet ini (yang punya active recipe).
    Return markdown table. Kalau tenant simple stock (gak ada recipe), return
    notice supaya AI kasih guidance umum tanpa data resep.
    """
    from backend.models.recipe import Recipe, RecipeIngredient
    from backend.models.ingredient import Ingredient
    from backend.models.product import Product
    from backend.models.outlet import Outlet
    from sqlalchemy.orm import selectinload

    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not outlet:
        return ""

    # Load semua recipe aktif untuk brand ini, beserta ingredients + product
    recipes = (await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.product),
        )
        .join(Product, Product.id == Recipe.product_id)
        .where(
            Product.brand_id == outlet.brand_id,
            Recipe.is_active == True,
            Recipe.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
    )).scalars().all()

    if not recipes:
        return (
            "\n\n## Catatan Pricing Coach\n"
            "Outlet ini belum punya resep aktif — HPP per produk tidak bisa "
            "dihitung otomatis. Kasih advice berdasarkan harga jual + rata-rata "
            "margin cafe Indonesia (60-75%). Kalau user mau analisa akurat, "
            "minta dia setup resep dulu via AI Asisten Setup Resep.\n"
        )

    rows = []
    for r in recipes:
        # Skip kalau ingredient sudah soft-deleted (pattern dari CLAUDE.md)
        active_ingredients = [
            ri for ri in r.ingredients
            if ri.ingredient is not None and ri.ingredient.deleted_at is None
        ]
        if not active_ingredients:
            continue

        hpp = 0.0
        for ri in active_ingredients:
            cost_per_unit = float(ri.ingredient.cost_per_base_unit or 0)
            qty = float(ri.quantity or 0)
            hpp += qty * cost_per_unit

        product = r.product
        if product is None:
            continue
        base_price = float(product.base_price or 0)
        if base_price <= 0:
            continue

        margin_rp = base_price - hpp
        margin_pct = (margin_rp / base_price * 100) if base_price > 0 else 0
        rows.append({
            "name": product.name,
            "hpp": hpp,
            "price": base_price,
            "margin_pct": margin_pct,
        })

    if not rows:
        return (
            "\n\n## Catatan Pricing Coach\n"
            "Resep ada tapi semua ingredient belum diisi harga (cost_per_base_unit=0). "
            "Minta user update harga beli bahan di halaman Bahan Baku dulu.\n"
        )

    # Sort: margin terendah di atas (prioritas review)
    rows.sort(key=lambda x: x["margin_pct"])

    lines = [
        "\n\n## HPP & Margin Produk Outlet Ini",
        "(Diurut margin terendah → tertinggi)",
        "",
        "| Produk | HPP | Harga Jual | Margin |",
        "|---|---|---|---|",
    ]
    for r in rows[:15]:  # Cap 15 biar prompt gak bengkak
        lines.append(
            f"| {r['name']} | Rp {r['hpp']:,.0f} | Rp {r['price']:,.0f} | {r['margin_pct']:.1f}% |"
        )
    if len(rows) > 15:
        lines.append(f"| _(+{len(rows)-15} produk lain)_ | | | |")

    return "\n".join(lines)


PRICING_COACH_SYSTEM_APPEND = """

## MODE: PRICING COACH

User sedang minta analisa harga/HPP/margin. Fokus jawab seperti ini:

1. **Data-driven**: rujuk angka HPP + margin dari tabel di atas. Kalau user
   nanya produk spesifik, jawab per produk. Kalau umum, pilih 2-3 produk
   paling bermasalah (margin rendah <50% atau sangat tinggi >85%).

2. **Bandingkan dengan benchmark cafe Indonesia**:
   - Kopi/minuman: margin wajar 60-80% (HPP 20-40% dari harga jual)
   - Makanan: 50-65% (HPP lebih tinggi karena bahan mentah)
   - Paket/combo: 55-70%
   Kalau ada data cross-tenant benchmark di context, pake itu juga.

3. **Rekomendasi konkret**:
   - Margin <50% → usul naikin harga Rp X atau turunin HPP (ganti supplier,
     kurangi porsi bahan mahal).
   - Margin >85% → mungkin underprice — ada ruang naikin harga untuk
     kualitas/positioning. Atau HPP underestimate (kelupaan overhead?).
   - Margin 60-75% → aman. Tunjukin produk lain yang perlu perhatian.

4. **Psikologi harga Indonesia**: rekomendasi naikin harga usulkan angka bulat
   (2.000/5.000 kelipatan), atau ke bawah (18rb → 19rb lebih smooth dari
   18rb → 20rb dalam 1x). Atau strategi bundling.

5. **Action step**: tutup dengan 1-2 langkah konkret ("coba naikin X jadi Y
   selama 2 minggu, monitor penjualan").

Format markdown: **bold** untuk angka penting, bullet list untuk rekomendasi.
Jawab ringkas — max 300 kata. Bahasa Indonesia casual (pake 'kamu'), jangan
formal. Jangan pake emoji.
"""


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

    if intent in (INTENT_SETUP_RECIPE, INTENT_MENU_BULK):
        # AI propose resep/menu via Haiku — user confirm di dashboard lalu apply
        generator = (
            generate_menu_proposal if intent == INTENT_MENU_BULK
            else generate_recipe_proposal
        )
        tokens_used = 0
        async for chunk in generator(
            message=message,
            outlet_id=outlet_id,
            tenant_id=tenant_id,
            outlet_name=outlet_name,
            db=db,
        ):
            if chunk.startswith("\n\n[__TOKENS__:"):
                try:
                    tokens_used = int(chunk.split(":")[1].rstrip("]\n "))
                except Exception:
                    pass
                continue
            yield sse({"type": "chunk", "content": chunk})

        yield sse({
            "type": "done",
            "intent": intent,
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

    # 3c. Pricing coach — inject HPP + margin data + coach system prompt
    if intent == INTENT_PRICING_COACH:
        # Cek quota Sonnet per tenant (Sonnet 4x biaya Haiku)
        try:
            from datetime import date as dt_date
            today = dt_date.today().isoformat()
            sonnet_key = f"ai_sonnet:{tenant_id}:{today}"
            sonnet_count = await redis_client.incr(sonnet_key)
            if sonnet_count == 1:
                await redis_client.expire(sonnet_key, 86400)
            if sonnet_count > SONNET_PER_TENANT_DAILY:
                yield sse({
                    "type": "chunk",
                    "content": (
                        f"Analisa pricing (Sonnet) udah dipakai **{SONNET_PER_TENANT_DAILY}x** hari ini. "
                        "Coba lagi besok — atau tanya biasa (pake Haiku) untuk info harga saja."
                    ),
                })
                yield sse({"type": "done", "intent": INTENT_PRICING_COACH, "tokens_used": 0})
                return
        except Exception:
            pass

        # Track extra spend (Sonnet ~2 cents vs Haiku 1 cent)
        try:
            from datetime import date as dt_date
            spend_key = f"ai_spend:{dt_date.today().isoformat()}"
            await redis_client.incrby(spend_key, 1)  # tambah 1 lagi (total 2)
        except Exception:
            pass

        pricing_ctx = await build_pricing_context(outlet_id, db)
        system_prompt += pricing_ctx + PRICING_COACH_SYSTEM_APPEND

    # 4. Pilih model (intent-aware — PRICING_COACH → Sonnet)
    task_complexity = classify_task_complexity(message)
    model = await get_model_for_tier(tier, task_complexity, tenant_id=tenant_id, intent=intent)

    # 5. Stream dari Claude API
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        tokens_used = 0
        # Pricing coach perlu ruang lebih besar untuk reasoning multi-produk
        max_tok = 1500 if intent == INTENT_PRICING_COACH else 512
        async with client.messages.stream(
            model=model,
            max_tokens=max_tok,
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
