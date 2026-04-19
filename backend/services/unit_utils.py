"""
Unit conversion helpers untuk recipe_ingredient.

Masalah: `ri.quantity_unit` (dari recipe builder) bisa beda dari
`ri.ingredient.base_unit`. Saat compute HPP (cost_per_base_unit tied ke
ingredient.base_unit), perlu konversi ri.quantity ke base_unit.

Untuk STOCK deduct/display: raw qty dipakai langsung (internally consistent
antara deduct dan compute_recipe_stock — keduanya raw). Helper ini KHUSUS
untuk HPP compute.

Lokasi pemakai (per 2026-04-19):
- backend/services/ai_service.py — build_pricing_context
- backend/services/menu_engineering_service.py — _get_hpp_map
- backend/services/knowledge_graph_service.py — compute HPP from KG edges
"""

# Mapping unit alias → (canonical_base_unit, multiplier_ke_canonical)
# Multiplier convert raw qty ke canonical base unit.
UNIT_ALIASES = {
    "kg": ("gram", 1000), "kilo": ("gram", 1000), "kilogram": ("gram", 1000),
    "g": ("gram", 1), "gram": ("gram", 1), "gr": ("gram", 1),
    "l": ("ml", 1000), "liter": ("ml", 1000),
    "ml": ("ml", 1), "mililiter": ("ml", 1),
    "pcs": ("pcs", 1), "butir": ("pcs", 1), "buah": ("pcs", 1), "biji": ("pcs", 1),
    "tray": ("pcs", 30), "dus": ("pcs", 12), "lusin": ("pcs", 12),
    "bungkus": ("bungkus", 1), "bks": ("bungkus", 1), "pack": ("bungkus", 1),
}


def normalize_recipe_qty(ri) -> "float | None":
    """
    Return ri.quantity terkonversi ke ingredient.base_unit.
    None kalau cross-family mismatch (misal kg→ml) atau unknown unit.

    Examples:
      - ri.quantity=1, ri.quantity_unit='kg', base_unit='gram' → 1000
      - ri.quantity=150, ri.quantity_unit='ml', base_unit='ml' → 150
      - ri.quantity=20, ri.quantity_unit='gram', base_unit='ml' → None
    """
    try:
        raw_qty = float(ri.quantity or 0)
    except (TypeError, ValueError):
        return None

    if raw_qty <= 0:
        return 0.0

    ing = getattr(ri, "ingredient", None)
    if ing is None:
        return None
    base_unit = (getattr(ing, "base_unit", None) or "").lower().strip()
    q_unit = (getattr(ri, "quantity_unit", None) or "").lower().strip()

    # Same unit atau empty q_unit (asumsi match) — no conversion
    if q_unit == base_unit or not q_unit:
        return raw_qty

    alias = UNIT_ALIASES.get(q_unit)
    if alias is None:
        return None

    mapped_base, multiplier = alias
    if mapped_base != base_unit:
        return None

    return raw_qty * multiplier


def ingredient_cost_contribution(ri) -> "float | None":
    """
    Cost contribution 1 recipe_ingredient row = normalized_qty * cost_per_base_unit.
    Return None kalau unit mismatch.
    """
    qty = normalize_recipe_qty(ri)
    if qty is None:
        return None

    ing = ri.ingredient
    try:
        cost_per_base = float(ing.cost_per_base_unit or 0)
    except (TypeError, ValueError):
        return None

    if cost_per_base <= 0:
        return 0.0

    return qty * cost_per_base


def cost_from_qty_unit(qty_raw, qty_unit: str, ingredient) -> "float | None":
    """
    Variant untuk caller yang punya qty + unit langsung (tanpa recipe_ingredient).
    Contoh: knowledge_graph_service — qty & unit dari metadata_payload JSONB.

    Return: cost contribution dalam Rupiah, atau None kalau unit mismatch.
    """
    try:
        raw = float(qty_raw or 0)
        cost_per_base = float(getattr(ingredient, "cost_per_base_unit", 0) or 0)
    except (TypeError, ValueError):
        return None

    if raw <= 0 or cost_per_base <= 0:
        return 0.0

    base_unit = (getattr(ingredient, "base_unit", None) or "").lower().strip()
    q_unit = (qty_unit or "").lower().strip()

    if q_unit == base_unit or not q_unit:
        return raw * cost_per_base

    alias = UNIT_ALIASES.get(q_unit)
    if alias is None:
        return None
    mapped_base, multiplier = alias
    if mapped_base != base_unit:
        return None
    return raw * multiplier * cost_per_base
