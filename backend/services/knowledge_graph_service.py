"""
Kasira Knowledge Graph Service

Builds and queries a knowledge graph from recipe/ingredient/category data.
Used by AI chatbot for context-aware answers like:
- "Bahan apa yang paling sering dipakai?"
- "Produk mana yang terdampak kalau gula habis?"
- "HPP naik karena harga bahan X naik"
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID

import sqlalchemy
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledge_graph import KnowledgeGraphEdge
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.ingredient import Ingredient
from backend.models.product import Product
from backend.models.category import Category

logger = logging.getLogger(__name__)


# ─── Graph Builder ───────────────────────────────────────────────────────────

async def rebuild_graph(tenant_id: UUID, brand_id: UUID, db: AsyncSession) -> Dict:
    """
    Rebuild knowledge graph for a tenant from current recipe/ingredient/category data.
    Deletes old edges and creates fresh ones. Idempotent.

    Edge types created:
    - product --contains--> ingredient  (from recipes)
    - product --belongs_to--> category
    - ingredient --used_by--> product   (reverse of contains)
    - ingredient --affects--> ingredient (shared products = co-dependency)
    """
    # 1. Delete old edges for this tenant
    await db.execute(
        delete(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )

    edges = []
    stats = {"product_ingredient": 0, "product_category": 0, "co_dependency": 0}

    # 2. Load all active recipes with ingredients
    recipes = (await db.execute(
        select(Recipe)
        .where(Recipe.is_active == True, Recipe.deleted_at.is_(None))
        .join(Product, Recipe.product_id == Product.id)
        .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
    )).scalars().all()

    recipe_ids = [r.id for r in recipes]
    if recipe_ids:
        recipe_ingredients = (await db.execute(
            select(RecipeIngredient)
            .where(
                RecipeIngredient.recipe_id.in_(recipe_ids),
                RecipeIngredient.deleted_at.is_(None),
            )
        )).scalars().all()
    else:
        recipe_ingredients = []

    # Map recipe_id -> product_id
    recipe_product_map = {r.id: r.product_id for r in recipes}

    # 3. Product --contains--> Ingredient edges
    # Also track ingredient -> [products] for co-dependency
    ingredient_products: Dict[UUID, List[UUID]] = {}

    for ri in recipe_ingredients:
        product_id = recipe_product_map.get(ri.recipe_id)
        if not product_id:
            continue

        # product --contains--> ingredient
        edges.append(KnowledgeGraphEdge(
            tenant_id=tenant_id,
            source_node_type="product",
            source_node_id=product_id,
            target_node_type="ingredient",
            target_node_id=ri.ingredient_id,
            relation_type="contains",
            weight=Decimal("1.0"),
            metadata_payload={
                "quantity": ri.quantity,
                "unit": ri.quantity_unit,
            },
        ))

        # ingredient --used_by--> product (reverse)
        edges.append(KnowledgeGraphEdge(
            tenant_id=tenant_id,
            source_node_type="ingredient",
            source_node_id=ri.ingredient_id,
            target_node_type="product",
            target_node_id=product_id,
            relation_type="used_by",
            weight=Decimal("1.0"),
        ))
        stats["product_ingredient"] += 1

        # Track for co-dependency
        if ri.ingredient_id not in ingredient_products:
            ingredient_products[ri.ingredient_id] = []
        ingredient_products[ri.ingredient_id].append(product_id)

    # 4. Product --belongs_to--> Category edges
    products = (await db.execute(
        select(Product).where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
            Product.category_id.isnot(None),
        )
    )).scalars().all()

    for p in products:
        edges.append(KnowledgeGraphEdge(
            tenant_id=tenant_id,
            source_node_type="product",
            source_node_id=p.id,
            target_node_type="category",
            target_node_id=p.category_id,
            relation_type="belongs_to",
            weight=Decimal("1.0"),
        ))
        stats["product_category"] += 1

    # 5. Ingredient --affects--> Ingredient (co-dependency via shared products)
    # If ingredient A and B are both in product X, they co-depend
    seen_pairs = set()
    for ing_id, prod_ids in ingredient_products.items():
        for other_ing_id, other_prod_ids in ingredient_products.items():
            if ing_id >= other_ing_id:
                continue
            shared = set(prod_ids) & set(other_prod_ids)
            if shared and (ing_id, other_ing_id) not in seen_pairs:
                seen_pairs.add((ing_id, other_ing_id))
                weight = min(Decimal(str(len(shared))) / Decimal("10"), Decimal("1.0"))
                edges.append(KnowledgeGraphEdge(
                    tenant_id=tenant_id,
                    source_node_type="ingredient",
                    source_node_id=ing_id,
                    target_node_type="ingredient",
                    target_node_id=other_ing_id,
                    relation_type="co_dependency",
                    weight=weight,
                    metadata_payload={"shared_products": len(shared)},
                ))
                stats["co_dependency"] += 1

    # 6. Table → Product edges (via tabs + orders — which products sold at which table)
    try:
        from backend.models.tab import Tab
        from backend.models.order import Order, OrderItem
        from backend.models.reservation import Table as TableModel

        # Get all paid tabs for this tenant's outlets
        tab_orders_q = await db.execute(
            select(
                TableModel.id.label("table_id"),
                TableModel.name.label("table_name"),
                OrderItem.product_id,
                func.count(OrderItem.id).label("cnt"),
            )
            .join(Tab, Tab.table_id == TableModel.id)
            .join(Order, Order.tab_id == Tab.id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Tab.status == 'paid',
                Tab.deleted_at.is_(None),
                Order.deleted_at.is_(None),
                OrderItem.deleted_at.is_(None),
                TableModel.outlet_id.in_(
                    select(Product.id).where(False)  # placeholder
                ) if False else True,
            )
            .join(Product, Product.id == OrderItem.product_id)
            .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
            .group_by(TableModel.id, TableModel.name, OrderItem.product_id)
        )
        table_product_rows = tab_orders_q.all()

        # table --served--> product (what gets ordered at this table)
        table_products: Dict[UUID, int] = {}  # table_id → total orders
        for row in table_product_rows:
            weight = min(Decimal(str(row.cnt)) / Decimal("20"), Decimal("1.0"))
            edges.append(KnowledgeGraphEdge(
                tenant_id=tenant_id,
                source_node_type="table",
                source_node_id=row.table_id,
                target_node_type="product",
                target_node_id=row.product_id,
                relation_type="served",
                weight=weight,
                metadata_payload={"count": row.cnt, "table_name": row.table_name},
            ))
            table_products[row.table_id] = table_products.get(row.table_id, 0) + row.cnt
            stats["table_product"] = stats.get("table_product", 0) + 1
    except Exception as e:
        logger.debug(f"Table→Product KG edges skipped: {e}")

    # 7. Bulk insert
    if edges:
        db.add_all(edges)
        await db.flush()

    return {"edges_created": len(edges), **stats}


# ─── Graph Queries ───────────────────────────────────────────────────────────

async def get_affected_products(
    tenant_id: UUID, ingredient_id: UUID, db: AsyncSession
) -> List[Dict]:
    """Get all products affected if an ingredient runs out or price changes."""
    edges = (await db.execute(
        select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.source_node_type == "ingredient",
            KnowledgeGraphEdge.source_node_id == ingredient_id,
            KnowledgeGraphEdge.relation_type == "used_by",
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).scalars().all()

    if not edges:
        return []

    product_ids = [e.target_node_id for e in edges]
    products = (await db.execute(
        select(Product.id, Product.name, Product.base_price).where(
            Product.id.in_(product_ids),
            Product.deleted_at.is_(None),
        )
    )).all()

    return [{"id": str(p.id), "name": p.name, "price": float(p.base_price or 0)} for p in products]


async def get_product_ingredients(
    tenant_id: UUID, product_id: UUID, db: AsyncSession
) -> List[Dict]:
    """Get all ingredients for a product via knowledge graph."""
    edges = (await db.execute(
        select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.source_node_type == "product",
            KnowledgeGraphEdge.source_node_id == product_id,
            KnowledgeGraphEdge.relation_type == "contains",
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).scalars().all()

    if not edges:
        return []

    ingredient_ids = [e.target_node_id for e in edges]
    ingredients = (await db.execute(
        select(Ingredient.id, Ingredient.name, Ingredient.cost_per_base_unit, Ingredient.base_unit).where(
            Ingredient.id.in_(ingredient_ids),
            Ingredient.deleted_at.is_(None),
        )
    )).all()

    ing_map = {i.id: i for i in ingredients}
    result = []
    for e in edges:
        ing = ing_map.get(e.target_node_id)
        if ing:
            meta = e.metadata_payload or {}
            result.append({
                "id": str(ing.id),
                "name": ing.name,
                "cost_per_unit": float(ing.cost_per_base_unit or 0),
                "unit": ing.base_unit,
                "quantity": meta.get("quantity", 0),
            })
    return result


async def get_most_used_ingredients(
    tenant_id: UUID, db: AsyncSession, limit: int = 5
) -> List[Dict]:
    """Get ingredients used in the most products."""
    results = (await db.execute(
        select(
            KnowledgeGraphEdge.source_node_id.label("ingredient_id"),
            func.count(KnowledgeGraphEdge.id).label("product_count"),
        ).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.source_node_type == "ingredient",
            KnowledgeGraphEdge.relation_type == "used_by",
            KnowledgeGraphEdge.deleted_at.is_(None),
        ).group_by(KnowledgeGraphEdge.source_node_id)
        .order_by(func.count(KnowledgeGraphEdge.id).desc())
        .limit(limit)
    )).all()

    if not results:
        return []

    ingredient_ids = [r.ingredient_id for r in results]
    ingredients = (await db.execute(
        select(Ingredient.id, Ingredient.name).where(
            Ingredient.id.in_(ingredient_ids),
            Ingredient.deleted_at.is_(None),
        )
    )).all()
    name_map = {i.id: i.name for i in ingredients}

    return [
        {"name": name_map.get(r.ingredient_id, "?"), "product_count": r.product_count}
        for r in results
    ]


async def compute_hpp_for_products(
    tenant_id: UUID, brand_id: UUID, db: AsyncSession
) -> List[Dict]:
    """
    Compute HPP (Harga Pokok Penjualan) for all products with recipes.
    Uses KG edges (product→ingredient) + ingredient cost_per_base_unit.
    Returns: [{product_name, price, hpp, margin_pct, ingredients: [{name, qty, unit, cost}]}]
    """
    # Get all contains edges
    edges = (await db.execute(
        select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.relation_type == "contains",
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).scalars().all()

    if not edges:
        return []

    # Collect all IDs
    product_ids = set(e.source_node_id for e in edges)
    ingredient_ids = set(e.target_node_id for e in edges)

    # Fetch products + ingredients
    products = {p.id: p for p in (await db.execute(
        select(Product).where(Product.id.in_(list(product_ids)), Product.deleted_at.is_(None))
    )).scalars().all()}

    ingredients = {i.id: i for i in (await db.execute(
        select(Ingredient).where(Ingredient.id.in_(list(ingredient_ids)), Ingredient.deleted_at.is_(None))
    )).scalars().all()}

    # Group edges by product
    product_edges: Dict[UUID, list] = {}
    for e in edges:
        product_edges.setdefault(e.source_node_id, []).append(e)

    from backend.services.unit_utils import cost_from_qty_unit

    result = []
    for pid, pedges in product_edges.items():
        prod = products.get(pid)
        if not prod:
            continue

        hpp = Decimal("0")
        ing_list = []
        has_mismatch = False
        for e in pedges:
            ing = ingredients.get(e.target_node_id)
            if not ing:
                continue
            meta = e.metadata_payload or {}
            qty_raw = meta.get("quantity", 0)
            unit_raw = meta.get("unit") or ing.base_unit
            try:
                qty_float = float(qty_raw or 0)
            except (TypeError, ValueError):
                qty_float = 0.0

            # Unit-aware cost (handle kg→gram, flag cross-family mismatch)
            cost_float = cost_from_qty_unit(qty_raw, str(unit_raw), ing)
            if cost_float is None:
                has_mismatch = True
                cost_float = 0.0  # exclude dari HPP sum, flag item

            hpp += Decimal(str(cost_float))
            ing_list.append({
                "name": ing.name,
                "qty": qty_float,
                "unit": str(unit_raw),
                "cost": cost_float,
                "unit_mismatch": cost_from_qty_unit(qty_raw, str(unit_raw), ing) is None,
            })

        price = float(prod.base_price or 0)
        margin_pct = ((price - float(hpp)) / price * 100) if price > 0 else 0

        result.append({
            "product_name": prod.name,
            "price": price,
            "hpp": float(hpp),
            "margin_pct": round(margin_pct, 1),
            "has_unit_mismatch": has_mismatch,
            "ingredients": ing_list,
        })

    # Sort by margin ascending (worst margin first — most useful for alerts)
    result.sort(key=lambda x: x["margin_pct"])
    return result


async def get_ingredient_stock_levels(
    tenant_id: UUID, outlet_id: UUID, db: AsyncSession
) -> List[Dict]:
    """Get current stock levels for all ingredients, highlight critical ones."""
    from backend.models.product import OutletStock
    from backend.models.outlet import Outlet

    outlet = await db.get(Outlet, outlet_id)
    if not outlet:
        return []

    stocks = (await db.execute(
        select(OutletStock, Ingredient).join(
            Ingredient, OutletStock.ingredient_id == Ingredient.id
        ).where(
            OutletStock.outlet_id == outlet_id,
            Ingredient.brand_id == outlet.brand_id,
            Ingredient.deleted_at.is_(None),
        )
    )).all()

    result = []
    for stock, ing in stocks:
        is_critical = stock.computed_stock <= stock.min_stock_base and stock.min_stock_base > 0
        result.append({
            "name": ing.name,
            "stock": float(stock.computed_stock),
            "unit": ing.base_unit,
            "min_stock": float(stock.min_stock_base),
            "is_critical": is_critical,
        })
    return result


async def build_ai_context_from_graph(
    tenant_id: UUID, db: AsyncSession, outlet_id: Optional[UUID] = None
) -> str:
    """Build a compact AI context string from knowledge graph data."""
    # Most used ingredients
    top_ingredients = await get_most_used_ingredients(tenant_id, db, limit=5)

    # Co-dependencies
    co_deps = (await db.execute(
        select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.relation_type == "co_dependency",
            KnowledgeGraphEdge.deleted_at.is_(None),
        ).limit(5)
    )).scalars().all()

    # Get ingredient names for co-deps
    co_dep_ing_ids = set()
    for e in co_deps:
        co_dep_ing_ids.add(e.source_node_id)
        co_dep_ing_ids.add(e.target_node_id)

    if co_dep_ing_ids:
        ing_names = (await db.execute(
            select(Ingredient.id, Ingredient.name).where(
                Ingredient.id.in_(list(co_dep_ing_ids)),
                Ingredient.deleted_at.is_(None),
            )
        )).all()
        name_map = {i.id: i.name for i in ing_names}
    else:
        name_map = {}

    # Edge count
    edge_count = (await db.execute(
        select(func.count(KnowledgeGraphEdge.id)).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).scalar() or 0

    if edge_count == 0:
        return ""

    lines = ["\nKNOWLEDGE GRAPH:"]

    if top_ingredients:
        items = [f"{i['name']} ({i['product_count']} produk)" for i in top_ingredients]
        lines.append(f"- Bahan paling sering dipakai: {', '.join(items)}")

    if co_deps:
        pairs = []
        for e in co_deps[:3]:
            a = name_map.get(e.source_node_id, "?")
            b = name_map.get(e.target_node_id, "?")
            pairs.append(f"{a} & {b}")
        lines.append(f"- Bahan saling terkait (ada di produk yang sama): {', '.join(pairs)}")
        lines.append("- Jika salah satu bahan habis, produk yang menggunakan keduanya terdampak")

    # HPP data from KG edges
    try:
        from backend.models.outlet import Outlet
        # Get brand_id from tenant's outlet
        outlet_row = None
        if outlet_id:
            outlet_row = await db.get(Outlet, outlet_id)
        if not outlet_row:
            outlet_res = await db.execute(
                select(Outlet).where(Outlet.tenant_id == tenant_id, Outlet.deleted_at.is_(None)).limit(1)
            )
            outlet_row = outlet_res.scalar_one_or_none()

        if outlet_row:
            hpp_data = await compute_hpp_for_products(tenant_id, outlet_row.brand_id, db)
            if hpp_data:
                lines.append("\nHPP (HARGA POKOK PENJUALAN):")
                for item in hpp_data[:8]:  # Max 8 products to keep context compact
                    margin_label = "🔴" if item["margin_pct"] < 15 else ("🟡" if item["margin_pct"] < 30 else "🟢")
                    lines.append(
                        f"- {item['product_name']}: HPP Rp{item['hpp']:,.0f} | "
                        f"Harga Rp{item['price']:,.0f} | "
                        f"Margin {item['margin_pct']}% {margin_label}"
                    )
                # Alert low margin
                low_margin = [x for x in hpp_data if x["margin_pct"] < 20]
                if low_margin:
                    names = ", ".join(x["product_name"] for x in low_margin[:3])
                    lines.append(f"- ⚠️ MARGIN RENDAH (<20%): {names}")

            # Ingredient stock levels
            oid = outlet_id or outlet_row.id
            ing_stocks = await get_ingredient_stock_levels(tenant_id, oid, db)
            critical = [s for s in ing_stocks if s["is_critical"]]
            if critical:
                lines.append("\nBAHAN BAKU KRITIS:")
                for s in critical[:5]:
                    lines.append(f"- {s['name']}: sisa {s['stock']:.0f} {s['unit']} (min: {s['min_stock']:.0f})")
    except Exception as e:
        logger.debug(f"HPP/stock context skipped: {e}")

    # Table popularity from KG (served edges)
    try:
        table_pop_q = await db.execute(
            select(
                KnowledgeGraphEdge.source_node_id,
                func.sum(KnowledgeGraphEdge.metadata_payload["count"].astext.cast(sqlalchemy.Integer)).label("total"),
                func.count(KnowledgeGraphEdge.id).label("product_variety"),
            ).where(
                KnowledgeGraphEdge.tenant_id == tenant_id,
                KnowledgeGraphEdge.relation_type == "served",
                KnowledgeGraphEdge.deleted_at.is_(None),
            ).group_by(KnowledgeGraphEdge.source_node_id)
            .order_by(func.sum(KnowledgeGraphEdge.metadata_payload["count"].astext.cast(sqlalchemy.Integer)).desc())
            .limit(5)
        )
        table_pop = table_pop_q.all()
        if table_pop:
            # Get table names
            table_ids = [r.source_node_id for r in table_pop]
            from backend.models.reservation import Table as TableModel
            table_names_q = await db.execute(
                select(TableModel.id, TableModel.name).where(TableModel.id.in_(table_ids))
            )
            tbl_name_map = {t.id: t.name for t in table_names_q.all()}

            lines.append("\nMEJA PALING RAMAI (dari history tab):")
            for r in table_pop:
                tname = tbl_name_map.get(r.source_node_id, "?")
                lines.append(f"- {tname}: {r.total} pesanan, {r.product_variety} jenis produk")
    except Exception as e:
        logger.debug(f"Table popularity context skipped: {e}")

    return "\n".join(lines)
