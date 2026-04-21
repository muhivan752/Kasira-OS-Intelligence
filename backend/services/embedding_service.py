"""
Kasira Embedding Service — Layer 4: Vector Embeddings

Generates embeddings via Voyage AI API for:
- Product semantic search (find similar menu items)
- Cross-tenant product similarity
- AI context enrichment (RAG pattern)

Uses httpx (already in deps) — no new packages needed.
Graceful degrade: if VOYAGE_API_KEY not set, embedding features disabled.

Voyage AI model: voyage-3-lite (512 dims, fast, cheap)
"""

import logging
from typing import List, Optional, Dict
from uuid import UUID

import httpx
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3-lite"
VOYAGE_DIMS = 512  # voyage-3-lite default
BATCH_SIZE = 32  # Voyage supports up to 128 texts per request


def is_available() -> bool:
    """Check if embedding service is configured."""
    return bool(getattr(settings, "VOYAGE_API_KEY", None))


# ─── Core Embed ──────────────────────────────────────────────────────────────

async def embed_texts(
    texts: List[str],
    input_type: str = "document",
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts via Voyage AI.

    Args:
        texts: List of strings to embed
        input_type: "document" for stored content, "query" for search queries

    Returns:
        List of embedding vectors (each is List[float] of VOYAGE_DIMS dimensions)

    Raises:
        RuntimeError if API key not configured or API call fails
    """
    api_key = getattr(settings, "VOYAGE_API_KEY", None)
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY not configured")

    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                VOYAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": VOYAGE_MODEL,
                    "input": batch,
                    "input_type": input_type,
                },
            )

            if response.status_code != 200:
                logger.error(f"Voyage API error {response.status_code}: {response.text}")
                raise RuntimeError(f"Voyage API error: {response.status_code}")

            data = response.json()
            batch_embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def embed_query(text: str) -> List[float]:
    """Embed a single query text for search."""
    results = await embed_texts([text], input_type="query")
    return results[0]


# ─── Product Embedding ───────────────────────────────────────────────────────

def build_product_text(product: dict) -> str:
    """
    Build a rich text representation of a product for embedding.
    Includes: name, description, category, ingredients, price range.
    """
    parts = [product["name"]]

    if product.get("description"):
        parts.append(product["description"])

    if product.get("category_name"):
        parts.append(f"kategori: {product['category_name']}")

    if product.get("ingredients"):
        ing_text = ", ".join(product["ingredients"])
        parts.append(f"bahan: {ing_text}")

    if product.get("base_price"):
        price = float(product["base_price"])
        if price < 15000:
            parts.append("harga murah")
        elif price < 30000:
            parts.append("harga menengah")
        else:
            parts.append("harga premium")

    return " | ".join(parts)


async def generate_product_embeddings(
    tenant_id: UUID,
    brand_id: UUID,
    db: AsyncSession,
    force: bool = False,
) -> Dict:
    """
    Generate embeddings for all active products of a tenant.
    force=False: skip products that already have embeddings.
    Returns: {total, embedded, skipped, errors}
    """
    from backend.models.product import Product
    from backend.models.category import Category
    from backend.models.recipe import Recipe, RecipeIngredient
    from backend.models.ingredient import Ingredient

    if not is_available():
        return {"total": 0, "embedded": 0, "skipped": 0, "errors": ["VOYAGE_API_KEY not configured"]}

    # Load all active products with category (eager load to avoid MissingGreenlet)
    from sqlalchemy.orm import selectinload
    query = (
        select(Product)
        .options(selectinload(Product.category))
        .where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
            Product.is_active == True,
        )
    )
    if not force:
        query = query.where(Product.embedding.is_(None))

    products = (await db.execute(query)).scalars().all()

    if not products:
        return {"total": 0, "embedded": 0, "skipped": 0, "errors": []}

    # Load recipe ingredients for each product (Recipe has no brand_id, join via Product)
    recipe_map: Dict[str, List[str]] = {}
    product_ids = [p.id for p in products]
    recipes = (await db.execute(
        select(Recipe.product_id, Ingredient.name)
        .select_from(Recipe)
        .join(RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .where(
            Recipe.product_id.in_(product_ids),
            Recipe.deleted_at.is_(None),
            Ingredient.deleted_at.is_(None),
        )
    )).all()

    for row in recipes:
        pid = str(row[0])
        recipe_map.setdefault(pid, []).append(row[1])

    # Build texts
    product_data = []
    for p in products:
        product_data.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "category_name": p.category.name if p.category else None,
            "ingredients": recipe_map.get(str(p.id), []),
            "base_price": p.base_price,
        })

    texts = [build_product_text(pd) for pd in product_data]

    # Generate embeddings
    try:
        embeddings = await embed_texts(texts, input_type="document")
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return {"total": len(products), "embedded": 0, "skipped": 0, "errors": [str(e)]}

    # Store embeddings
    embedded = 0
    errors = []
    for pd, emb in zip(product_data, embeddings):
        try:
            await db.execute(
                sql_update(Product)
                .where(Product.id == pd["id"])
                .values(embedding=emb)
            )
            embedded += 1
        except Exception as e:
            errors.append(f"{pd['name']}: {e}")

    await db.commit()

    logger.info(f"Embedded {embedded}/{len(products)} products for tenant {tenant_id}")
    return {
        "total": len(products),
        "embedded": embedded,
        "skipped": len(products) - embedded,
        "errors": errors,
    }


# ─── Bulk Generate All Tenants ──────────────────────────────────────────────

async def generate_all_tenants_embeddings() -> Dict:
    """
    Generate embeddings for ALL tenants' products.
    Used by admin endpoint — bypasses RLS via own session.
    Returns per-tenant results.
    """
    if not is_available():
        return {"error": "VOYAGE_API_KEY not configured", "tenants": []}

    from backend.core.database import AsyncSessionLocal
    from backend.models.brand import Brand
    from sqlalchemy import text

    results = []

    from backend.models.tenant import Tenant

    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        # Exclude demo tenants from bulk embedding
        brands = (await db.execute(
            select(Brand)
            .join(Tenant, Brand.tenant_id == Tenant.id)
            .where(Brand.deleted_at.is_(None), Tenant.is_demo == False)
        )).scalars().all()

    for brand in brands:
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
                result = await generate_product_embeddings(
                    tenant_id=brand.tenant_id,
                    brand_id=brand.id,
                    db=db,
                )
                result["brand_id"] = str(brand.id)
                result["brand_name"] = brand.name
                result["tenant_id"] = str(brand.tenant_id)
                results.append(result)
        except Exception as e:
            results.append({
                "brand_name": brand.name,
                "error": str(e),
            })

    total_embedded = sum(r.get("embedded", 0) for r in results)
    total_products = sum(r.get("total", 0) for r in results)

    return {
        "total_tenants": len(brands),
        "total_products": total_products,
        "total_embedded": total_embedded,
        "tenants": results,
    }


# ─── Silent Single-Product Embedding ────────────────────────────────────────

async def embed_single_product_silent(product_id: UUID, brand_id: UUID, tenant_id: Optional[UUID] = None):
    """
    Fire-and-forget: embed one product after create/update.
    Uses its own DB session. Never raises — logs errors silently.
    Called via asyncio.create_task() from product API.
    """
    if not is_available():
        return

    try:
        from backend.core.database import AsyncSessionLocal
        from backend.models.product import Product
        from backend.models.category import Category
        from backend.models.recipe import Recipe, RecipeIngredient
        from backend.models.ingredient import Ingredient
        from sqlalchemy.orm import selectinload
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            # Set search_path and RLS context for new session
            await db.execute(text('SET search_path TO public'))
            if tenant_id:
                await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
            # Load product with category
            product = (await db.execute(
                select(Product)
                .options(selectinload(Product.category))
                .where(Product.id == product_id)
            )).scalar_one_or_none()

            if not product or product.deleted_at is not None:
                return

            # Load recipe ingredients
            ingredients = []
            recipes = (await db.execute(
                select(Ingredient.name)
                .select_from(Recipe)
                .join(RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id)
                .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
                .where(
                    Recipe.product_id == product_id,
                    Recipe.deleted_at.is_(None),
                    Ingredient.deleted_at.is_(None),
                )
            )).scalars().all()
            ingredients = list(recipes)

            # Build text and embed
            product_data = {
                "name": product.name,
                "description": product.description,
                "category_name": product.category.name if product.category else None,
                "ingredients": ingredients,
                "base_price": product.base_price,
            }
            text = build_product_text(product_data)
            embeddings = await embed_texts([text], input_type="document")

            # Store
            await db.execute(
                sql_update(Product)
                .where(Product.id == product_id)
                .values(embedding=embeddings[0])
            )
            await db.commit()
            logger.info(f"Silent embed OK: {product.name} ({product_id})")

    except Exception as e:
        logger.warning(f"Silent embed failed for {product_id}: {e}")


# ─── Semantic Search ─────────────────────────────────────────────────────────

async def search_similar_products(
    query: str,
    brand_id: UUID,
    db: AsyncSession,
    limit: int = 5,
    threshold: float = 0.3,
) -> List[Dict]:
    """
    Find products semantically similar to a query.
    Uses pgvector cosine distance (<=> operator).

    Returns list of {id, name, description, category, price, similarity}
    """
    from backend.models.product import Product
    from backend.models.category import Category

    if not is_available():
        return []

    # Embed the query
    query_embedding = await embed_query(query)

    # pgvector cosine distance: lower = more similar
    # Cosine similarity = 1 - cosine_distance
    results = (await db.execute(
        select(
            Product.id,
            Product.name,
            Product.description,
            Product.base_price,
            Category.name.label("category_name"),
            Product.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
            Product.is_active == True,
            Product.embedding.isnot(None),
        )
        .order_by(Product.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )).all()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "price": float(r.base_price),
            "category": r.category_name,
            "similarity": round(1 - r.distance, 4),
        }
        for r in results
        if (1 - r.distance) >= threshold
    ]


async def search_similar_products_cross_tenant(
    query: str,
    db: AsyncSession,
    exclude_brand_id: Optional[UUID] = None,
    limit: int = 10,
) -> List[Dict]:
    """
    Cross-tenant semantic search — find similar products across ALL merchants.
    Used for platform intelligence: "produk serupa di cafe lain".
    Bypasses RLS to query across all tenants.
    """
    from backend.models.product import Product
    from backend.models.category import Category
    from backend.models.brand import Brand
    from sqlalchemy import text

    if not is_available():
        return []

    query_embedding = await embed_query(query)

    # Bypass RLS — cross-tenant query needs access to all products
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    from backend.models.tenant import Tenant

    # Get demo tenant IDs to exclude
    demo_ids = [t for t in (await db.execute(
        select(Tenant.id).where(Tenant.is_demo == True)
    )).scalars().all()]

    query_stmt = (
        select(
            Product.id,
            Product.name,
            Product.description,
            Product.base_price,
            Product.brand_id,
            Brand.name.label("brand_name"),
            Category.name.label("category_name"),
            Product.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Brand, Product.brand_id == Brand.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Product.deleted_at.is_(None),
            Product.is_active == True,
            Product.embedding.isnot(None),
        )
    )

    # Exclude demo tenants from cross-tenant results
    if demo_ids:
        query_stmt = query_stmt.where(Brand.tenant_id.notin_(demo_ids))

    if exclude_brand_id:
        query_stmt = query_stmt.where(Product.brand_id != exclude_brand_id)

    results = (await db.execute(
        query_stmt
        .order_by(Product.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )).all()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "price": float(r.base_price),
            "category": r.category_name,
            "brand_id": str(r.brand_id),
            "brand_name": r.brand_name,
            "similarity": round(1 - r.distance, 4),
        }
        for r in results
        if (1 - r.distance) >= 0.2
    ]


# ─── AI Context Enrichment (RAG) ─────────────────────────────────────────────

async def enrich_ai_context(
    user_message: str,
    brand_id: UUID,
    db: AsyncSession,
) -> str:
    """
    RAG: embed user's question, find relevant products/data,
    return context string to inject into AI system prompt.
    """
    if not is_available():
        return ""

    try:
        similar = await search_similar_products(
            query=user_message,
            brand_id=brand_id,
            db=db,
            limit=3,
            threshold=0.25,
        )

        if not similar:
            return ""

        lines = ["\nPRODUK RELEVAN (berdasarkan pertanyaan):"]
        for p in similar:
            line = f"- {p['name']}"
            if p.get("category"):
                line += f" ({p['category']})"
            line += f" — Rp{p['price']:,.0f}"
            if p.get("description"):
                line += f" — {p['description'][:60]}"
            lines.append(line)

        return "\n".join(lines)

    except Exception as e:
        logger.debug(f"RAG context skipped: {e}")
        return ""
