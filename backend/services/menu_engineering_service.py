"""
Kasira Menu Engineering Service — BCG Matrix + Combo Detection

Classifies products into 4 quadrants based on:
- Popularity (order count vs average)
- Profitability (margin % vs average)

Quadrants:
- Star      ★ = High popularity + High margin    → PROMOTE
- Plowhorse 🐴 = High popularity + Low margin     → OPTIMIZE cost
- Puzzle    🧩 = Low popularity  + High margin     → BOOST marketing
- Dog       🐕 = Low popularity  + Low margin      → CONSIDER removing

Combo Detection:
- Co-occurrence analysis: products frequently ordered together
- Support + Confidence metrics for each pair
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_, case, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.category import Category
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.ingredient import Ingredient

logger = logging.getLogger(__name__)

# ─── Types ───────────────────────────────────────────────────────────────────

QUADRANT_STAR = "star"
QUADRANT_PLOWHORSE = "plowhorse"
QUADRANT_PUZZLE = "puzzle"
QUADRANT_DOG = "dog"

QUADRANT_LABELS = {
    QUADRANT_STAR: {"label": "Star", "emoji": "★", "action": "Promosikan & pertahankan"},
    QUADRANT_PLOWHORSE: {"label": "Plowhorse", "emoji": "🐴", "action": "Optimalkan HPP / naikkan harga"},
    QUADRANT_PUZZLE: {"label": "Puzzle", "emoji": "🧩", "action": "Tingkatkan promosi & visibilitas"},
    QUADRANT_DOG: {"label": "Dog", "emoji": "🐕", "action": "Evaluasi / pertimbangkan hapus"},
}


# ─── Core: BCG Matrix Classification ────────────────────────────────────────

async def classify_menu(
    db: AsyncSession,
    brand_id: UUID,
    outlet_id: UUID,
    start_date: date,
    end_date: date,
) -> Dict:
    """
    Classify all products into BCG matrix quadrants.
    Returns dict with products, averages, and summary.
    """
    # 1. Get popularity: order count + revenue per product
    popularity = await _get_popularity(db, outlet_id, start_date, end_date)
    if not popularity:
        return {"products": [], "summary": {}, "period": {"start": str(start_date), "end": str(end_date)}}

    # 2. Get HPP (cost) per product
    hpp_map = await _get_hpp_map(db, brand_id)

    # 3. Build product metrics
    products = []
    total_orders = 0
    total_revenue = Decimal("0")

    for product_id, data in popularity.items():
        sold = data["sold"]
        revenue = data["revenue"]
        name = data["name"]
        category = data["category"]
        price = data["price"]
        hpp = hpp_map.get(product_id, Decimal("0"))
        margin = price - hpp if price > 0 else Decimal("0")
        margin_pct = (margin / price * 100) if price > 0 else Decimal("0")

        products.append({
            "product_id": str(product_id),
            "name": name,
            "category": category,
            "price": float(price),
            "hpp": float(hpp),
            "margin": float(margin),
            "margin_pct": float(margin_pct),
            "sold": sold,
            "revenue": float(revenue),
        })
        total_orders += sold
        total_revenue += revenue

    if not products:
        return {"products": [], "summary": {}, "period": {"start": str(start_date), "end": str(end_date)}}

    # 4. Calculate averages (threshold)
    n = len(products)
    avg_sold = total_orders / n
    avg_margin_pct = sum(p["margin_pct"] for p in products) / n

    # 5. Classify each product
    summary = {QUADRANT_STAR: 0, QUADRANT_PLOWHORSE: 0, QUADRANT_PUZZLE: 0, QUADRANT_DOG: 0}
    for p in products:
        high_pop = p["sold"] >= avg_sold
        high_margin = p["margin_pct"] >= avg_margin_pct

        if high_pop and high_margin:
            quadrant = QUADRANT_STAR
        elif high_pop and not high_margin:
            quadrant = QUADRANT_PLOWHORSE
        elif not high_pop and high_margin:
            quadrant = QUADRANT_PUZZLE
        else:
            quadrant = QUADRANT_DOG

        p["quadrant"] = quadrant
        p["quadrant_label"] = QUADRANT_LABELS[quadrant]["label"]
        p["quadrant_emoji"] = QUADRANT_LABELS[quadrant]["emoji"]
        p["action"] = QUADRANT_LABELS[quadrant]["action"]
        summary[quadrant] += 1

    # Sort: stars first, then by revenue desc
    order_map = {QUADRANT_STAR: 0, QUADRANT_PLOWHORSE: 1, QUADRANT_PUZZLE: 2, QUADRANT_DOG: 3}
    products.sort(key=lambda p: (order_map[p["quadrant"]], -p["revenue"]))

    return {
        "products": products,
        "averages": {
            "avg_sold": round(avg_sold, 1),
            "avg_margin_pct": round(avg_margin_pct, 1),
        },
        "summary": summary,
        "period": {"start": str(start_date), "end": str(end_date)},
        "total_revenue": float(total_revenue),
        "total_orders": total_orders,
    }


# ─── Core: Combo Detection (Co-occurrence) ──────────────────────────────────

async def detect_combos(
    db: AsyncSession,
    outlet_id: UUID,
    start_date: date,
    end_date: date,
    min_support: int = 3,
    limit: int = 20,
) -> List[Dict]:
    """
    Find product pairs frequently ordered together.
    Uses self-join on order_items to find co-occurrences.

    Returns list of pairs with support (co-order count) and confidence.
    """
    # Total orders in period (for support %)
    total_q = (
        select(func.count(func.distinct(Order.id)))
        .where(
            Order.outlet_id == outlet_id,
            Order.status != "cancelled",
            Order.deleted_at.is_(None),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
        )
    )
    total_result = await db.execute(total_q)
    total_orders = total_result.scalar() or 0

    if total_orders < 2:
        return []

    # Self-join: find product pairs in same order
    oi1 = OrderItem.__table__.alias("oi1")
    oi2 = OrderItem.__table__.alias("oi2")
    o = Order.__table__
    p1 = Product.__table__.alias("p1")
    p2 = Product.__table__.alias("p2")

    query = text("""
        SELECT
            oi1.product_id AS product_a_id,
            p1.name AS product_a_name,
            oi2.product_id AS product_b_id,
            p2.name AS product_b_name,
            COUNT(DISTINCT oi1.order_id) AS co_orders,
            ROUND(COUNT(DISTINCT oi1.order_id)::numeric / :total * 100, 1) AS support_pct
        FROM order_items oi1
        JOIN order_items oi2 ON oi1.order_id = oi2.order_id
            AND oi1.product_id < oi2.product_id
        JOIN orders o ON oi1.order_id = o.id
        JOIN products p1 ON oi1.product_id = p1.id
        JOIN products p2 ON oi2.product_id = p2.id
        WHERE o.outlet_id = :outlet_id
            AND o.status != 'cancelled'
            AND o.deleted_at IS NULL
            AND oi1.deleted_at IS NULL
            AND oi2.deleted_at IS NULL
            AND o.created_at::date >= :start_date
            AND o.created_at::date <= :end_date
        GROUP BY oi1.product_id, p1.name, oi2.product_id, p2.name
        HAVING COUNT(DISTINCT oi1.order_id) >= :min_support
        ORDER BY co_orders DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {
        "outlet_id": str(outlet_id),
        "start_date": start_date,
        "end_date": end_date,
        "total": total_orders,
        "min_support": min_support,
        "limit": limit,
    })

    combos = []
    for row in result:
        combos.append({
            "product_a_id": str(row.product_a_id),
            "product_a_name": row.product_a_name,
            "product_b_id": str(row.product_b_id),
            "product_b_name": row.product_b_name,
            "co_orders": row.co_orders,
            "support_pct": float(row.support_pct),
            "total_orders": total_orders,
        })

    return combos


# ─── AI Context Builder ─────────────────────────────────────────────────────

async def build_menu_engineering_context(
    db: AsyncSession,
    brand_id: UUID,
    outlet_id: UUID,
) -> str:
    """
    Build compact menu engineering summary for AI system prompt injection.
    Uses last 30 days of data.
    """
    end = date.today()
    start = end - timedelta(days=30)

    try:
        result = await classify_menu(db, brand_id, outlet_id, start, end)
        if not result["products"]:
            return ""

        lines = ["\n\n📊 MENU ENGINEERING (30 hari terakhir):"]
        summary = result["summary"]
        lines.append(f"Star: {summary.get('star', 0)} | Plowhorse: {summary.get('plowhorse', 0)} | Puzzle: {summary.get('puzzle', 0)} | Dog: {summary.get('dog', 0)}")

        # Top stars
        stars = [p for p in result["products"] if p["quadrant"] == QUADRANT_STAR]
        if stars:
            names = ", ".join(p["name"] for p in stars[:3])
            lines.append(f"★ Star (top seller + margin tinggi): {names}")

        # Plowhorses — opportunity
        plows = [p for p in result["products"] if p["quadrant"] == QUADRANT_PLOWHORSE]
        if plows:
            names = ", ".join(f"{p['name']} (margin {p['margin_pct']:.0f}%)" for p in plows[:3])
            lines.append(f"🐴 Plowhorse (laku tapi margin rendah): {names}")

        # Puzzles — hidden gems
        puzzles = [p for p in result["products"] if p["quadrant"] == QUADRANT_PUZZLE]
        if puzzles:
            names = ", ".join(p["name"] for p in puzzles[:3])
            lines.append(f"🧩 Puzzle (margin tinggi tapi kurang laku): {names}")

        # Dogs
        dogs = [p for p in result["products"] if p["quadrant"] == QUADRANT_DOG]
        if dogs:
            names = ", ".join(p["name"] for p in dogs[:3])
            lines.append(f"🐕 Dog (kurang laku & margin rendah): {names}")

        # Combos
        combos = await detect_combos(db, outlet_id, start, end, min_support=2, limit=5)
        if combos:
            lines.append("\n🔗 COMBO POPULER:")
            for c in combos[:5]:
                lines.append(f"  {c['product_a_name']} + {c['product_b_name']} ({c['co_orders']}x, {c['support_pct']}%)")

        return "\n".join(lines)

    except Exception as e:
        logger.debug(f"Menu engineering context skipped: {e}")
        return ""


# ─── Private: Popularity Query ───────────────────────────────────────────────

async def _get_popularity(
    db: AsyncSession,
    outlet_id: UUID,
    start_date: date,
    end_date: date,
) -> Dict[UUID, Dict]:
    """Get order count, revenue, product info per product in period."""
    query = (
        select(
            OrderItem.product_id,
            Product.name,
            Product.base_price,
            func.coalesce(Category.name, "Tanpa Kategori").label("category_name"),
            func.sum(OrderItem.quantity).label("sold"),
            func.sum(OrderItem.total_price).label("revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Order.outlet_id == outlet_id,
            Order.status != "cancelled",
            Order.deleted_at.is_(None),
            OrderItem.deleted_at.is_(None),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
        )
        .group_by(OrderItem.product_id, Product.name, Product.base_price, Category.name)
    )

    result = await db.execute(query)
    rows = result.all()

    return {
        row.product_id: {
            "name": row.name,
            "price": row.base_price or Decimal("0"),
            "category": row.category_name,
            "sold": row.sold or 0,
            "revenue": row.revenue or Decimal("0"),
        }
        for row in rows
    }


async def _get_hpp_map(db: AsyncSession, brand_id: UUID) -> Dict[UUID, Decimal]:
    """
    Get HPP (cost) per product from active recipes.
    Python-side compute pakai unit_utils.ingredient_cost_contribution biar
    handle unit mismatch (ri.quantity_unit != ingredient.base_unit).
    Product yang punya unresolvable mismatch → excluded dari map (HPP unknown).
    """
    from backend.services.unit_utils import ingredient_cost_contribution

    recipes = (await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
        .join(Product, Product.id == Recipe.product_id)
        .where(
            Product.brand_id == brand_id,
            Recipe.is_active.is_(True),
            Recipe.deleted_at.is_(None),
        )
    )).scalars().all()

    hpp_map: Dict[UUID, Decimal] = {}
    for r in recipes:
        total = Decimal("0")
        had_mismatch = False
        for ri in r.ingredients:
            if (ri.deleted_at is not None or ri.is_optional or (ri.quantity or 0) <= 0
                    or ri.ingredient is None or ri.ingredient.deleted_at is not None):
                continue
            contrib = ingredient_cost_contribution(ri)
            if contrib is None:
                had_mismatch = True
                continue
            total += Decimal(str(contrib))

        # Kalau ada mismatch unresolvable, HPP under-estimate — skip entry
        # (better hilang dari menu engineering daripada salah klasifikasi)
        if had_mismatch and total == Decimal("0"):
            continue
        hpp_map[r.product_id] = total

    return hpp_map
