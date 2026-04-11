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

    # 6. Bulk insert
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


async def build_ai_context_from_graph(
    tenant_id: UUID, db: AsyncSession
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

    return "\n".join(lines)
