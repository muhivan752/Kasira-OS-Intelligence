"""
Kasira Invoice OCR Service — Extract purchase data from invoice photos.

Uses Claude Vision API to parse supplier invoices/receipts into structured data:
- Supplier name
- Invoice date
- Line items: ingredient name, quantity, unit, unit price, total

Then matches items to existing ingredients or suggests new ones.
"""

import base64
import logging
from typing import List, Optional, Dict
from uuid import UUID
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.ingredient import Ingredient

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def extract_invoice_data(image_bytes: bytes, media_type: str) -> Dict:
    """
    Send invoice image to Claude Vision API, get structured extraction.
    Returns: {supplier, date, items: [{name, qty, unit, unit_price, total}]}
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Kamu adalah asisten OCR untuk nota pembelian bahan baku restoran/cafe Indonesia.

Ekstrak data dari foto nota/invoice ini ke format JSON berikut:

```json
{
  "supplier_name": "Nama toko/supplier (atau null jika tidak terlihat)",
  "invoice_date": "YYYY-MM-DD (atau null jika tidak terlihat)",
  "invoice_number": "Nomor nota (atau null)",
  "items": [
    {
      "name": "Nama bahan (bahasa Indonesia, huruf kecil)",
      "quantity": 5.0,
      "unit": "kg",
      "unit_price": 25000,
      "total_price": 125000
    }
  ],
  "grand_total": 500000,
  "notes": "Catatan tambahan jika ada"
}
```

Rules:
- Semua harga dalam Rupiah (tanpa Rp, titik, atau koma — angka bulat saja)
- Unit harus standar: kg, gram, liter, ml, pcs, pack, dus, karung, botol
- Nama bahan harus lowercase bahasa Indonesia
- Jika ada item yang tidak jelas, tetap masukkan dengan best guess
- quantity dan unit_price harus angka (float/int)
- Jika total_price tidak terlihat, hitung dari quantity × unit_price
- HANYA output JSON, tanpa penjelasan""",
                    },
                ],
            }
        ],
    )

    except Exception as e:
        error_msg = str(e)
        if "credit balance" in error_msg.lower():
            raise RuntimeError("Anthropic API credit habis. Top up di console.anthropic.com")
        logger.error(f"Claude Vision API error: {error_msg}")
        raise RuntimeError(f"OCR gagal: {error_msg[:100]}")

    # Parse JSON from response
    import json
    text = response.content[0].text.strip()

    # Strip markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse OCR response: {text[:200]}")
        return {"error": "Gagal membaca nota. Coba foto yang lebih jelas.", "raw": text}


async def match_ingredients(
    items: List[Dict],
    brand_id: UUID,
    db: AsyncSession,
) -> List[Dict]:
    """
    Match extracted items to existing ingredients in the brand.
    Returns items with match info: {name, qty, unit, price, matched_ingredient_id, match_type}
    """
    # Load existing ingredients for this brand
    existing = (await db.execute(
        select(Ingredient).where(
            Ingredient.brand_id == brand_id,
            Ingredient.deleted_at.is_(None),
        )
    )).scalars().all()

    ingredient_map = {ing.name.lower().strip(): ing for ing in existing}

    results = []
    for item in items:
        item_name = (item.get("name") or "").lower().strip()
        match_type = "new"
        matched_id = None
        matched_name = None

        # Exact match
        if item_name in ingredient_map:
            match_type = "exact"
            ing = ingredient_map[item_name]
            matched_id = str(ing.id)
            matched_name = ing.name
        else:
            # Fuzzy: check if item name contains or is contained in existing ingredient
            for ing_name, ing in ingredient_map.items():
                if item_name in ing_name or ing_name in item_name:
                    match_type = "partial"
                    matched_id = str(ing.id)
                    matched_name = ing.name
                    break

        results.append({
            "name": item.get("name", ""),
            "quantity": item.get("quantity", 0),
            "unit": item.get("unit", ""),
            "unit_price": item.get("unit_price", 0),
            "total_price": item.get("total_price", 0),
            "match_type": match_type,
            "matched_ingredient_id": matched_id,
            "matched_ingredient_name": matched_name,
        })

    return results


async def apply_invoice_prices(
    items: List[Dict],
    brand_id: UUID,
    db: AsyncSession,
) -> Dict:
    """
    Update ingredient buy_price/buy_qty for matched items.
    Only updates ingredients with match_type 'exact' or 'partial' (confirmed by user).
    Returns: {updated: int, skipped: int}
    """
    updated = 0
    skipped = 0

    for item in items:
        ing_id = item.get("matched_ingredient_id")
        if not ing_id:
            skipped += 1
            continue

        qty = item.get("quantity", 0)
        price = item.get("unit_price", 0)
        if qty <= 0 or price <= 0:
            skipped += 1
            continue

        ingredient = (await db.execute(
            select(Ingredient).where(
                Ingredient.id == ing_id,
                Ingredient.brand_id == brand_id,
                Ingredient.deleted_at.is_(None),
            )
        )).scalar_one_or_none()

        if not ingredient:
            skipped += 1
            continue

        # Update buy_price and buy_qty
        total = item.get("total_price") or (qty * price)
        ingredient.buy_price = total
        ingredient.buy_qty = qty
        ingredient.cost_per_base_unit = round(total / qty, 2) if qty > 0 else 0
        ingredient.row_version += 1
        updated += 1

    if updated > 0:
        await db.commit()

    return {"updated": updated, "skipped": skipped}
