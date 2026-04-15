"""
Kasira Embedding Routes — Layer 4: Vector Embeddings

POST /embeddings/generate     — generate product embeddings (Pro+, owner)
GET  /embeddings/search       — semantic product search
GET  /embeddings/similar/{id} — find similar products to a given product
GET  /embeddings/status       — check embedding status
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.brand import Brand
from backend.models.product import Product
from backend.schemas.response import StandardResponse
from backend.services import embedding_service
from sqlalchemy.orm import selectinload

router = APIRouter()
logger = logging.getLogger(__name__)


async def _get_brand_and_outlet(tenant_id: UUID, db: AsyncSession):
    """Get brand_id and outlet_id from tenant."""
    brand = (await db.execute(
        select(Brand).where(Brand.tenant_id == tenant_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not brand:
        return None, None
    outlet = (await db.execute(
        select(Outlet).where(Outlet.brand_id == brand.id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    return brand, outlet


# ─── Schemas ─────────────────────────────────────────────────────────────────

class EmbeddingGenerateResponse(BaseModel):
    total: int
    embedded: int
    skipped: int
    errors: list


class SemanticSearchResult(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    similarity: float


# ─── Status ──────────────────────────────────────────────────────────────────

@router.get("/status")
async def embedding_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Check embedding configuration and product embedding status."""
    brand, outlet = await _get_brand_and_outlet(current_user.tenant_id, db)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    total = (await db.execute(
        select(func.count(Product.id)).where(
            Product.brand_id == brand.id,
            Product.deleted_at.is_(None),
            Product.is_active == True,
        )
    )).scalar() or 0

    embedded = (await db.execute(
        select(func.count(Product.id)).where(
            Product.brand_id == brand.id,
            Product.deleted_at.is_(None),
            Product.is_active == True,
            Product.embedding.isnot(None),
        )
    )).scalar() or 0

    return StandardResponse(
        data={
            "available": embedding_service.is_available(),
            "model": embedding_service.VOYAGE_MODEL,
            "dimensions": embedding_service.VOYAGE_DIMS,
            "total_products": total,
            "embedded_products": embedded,
            "coverage": f"{embedded}/{total}" if total > 0 else "0/0",
        },
        message="Embedding status",
    )


# ─── Generate ────────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    dependencies=[Depends(deps.require_pro_tier)],
)
async def generate_embeddings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Generate embeddings for all active products. Pro+ only.
    Idempotent — safe to call multiple times.
    """
    if not embedding_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Embedding service not configured. Set VOYAGE_API_KEY.",
        )

    brand, outlet = await _get_brand_and_outlet(current_user.tenant_id, db)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    result = await embedding_service.generate_product_embeddings(
        tenant_id=current_user.tenant_id,
        brand_id=brand.id,
        db=db,
    )

    return StandardResponse(
        data=result,
        message=f"Embedded {result['embedded']}/{result['total']} products",
    )


# ─── Semantic Search ─────────────────────────────────────────────────────────

@router.get("/search")
async def semantic_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Semantic product search — find products by meaning, not just keywords.
    Example: "minuman dingin" finds iced coffee, smoothie, es teh, etc.
    """
    if not embedding_service.is_available():
        raise HTTPException(status_code=503, detail="Embedding service not configured")

    brand, outlet = await _get_brand_and_outlet(current_user.tenant_id, db)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    results = await embedding_service.search_similar_products(
        query=q,
        brand_id=brand.id,
        db=db,
        limit=limit,
    )

    return StandardResponse(
        data=results,
        message=f"Found {len(results)} similar products",
    )


# ─── Similar Products ────────────────────────────────────────────────────────

@router.get("/similar/{product_id}")
async def find_similar(
    product_id: str,
    limit: int = Query(5, ge=1, le=10),
    cross_tenant: bool = Query(False, description="Search across all merchants"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Find products similar to a given product.
    cross_tenant=true: find similar products from OTHER merchants (platform intelligence).
    """
    if not embedding_service.is_available():
        raise HTTPException(status_code=503, detail="Embedding service not configured")

    # Get the source product (eager load category to avoid MissingGreenlet)
    product = (await db.execute(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.embedding is None:
        raise HTTPException(status_code=400, detail="Product has no embedding. Run /generate first.")

    brand, outlet = await _get_brand_and_outlet(current_user.tenant_id, db)

    # Use product name as query text
    query_text = embedding_service.build_product_text({
        "name": product.name,
        "description": product.description,
        "category_name": product.category.name if product.category else None,
        "base_price": product.base_price,
    })

    if cross_tenant:
        results = await embedding_service.search_similar_products_cross_tenant(
            query=query_text,
            db=db,
            exclude_brand_id=brand.id if brand else None,
            limit=limit,
        )
    else:
        results = await embedding_service.search_similar_products(
            query=query_text,
            brand_id=brand.id,
            db=db,
            limit=limit + 1,  # +1 because source product will be in results
        )
        # Remove source product from results
        results = [r for r in results if r["id"] != product_id][:limit]

    return StandardResponse(
        data={
            "source": {"id": str(product.id), "name": product.name},
            "similar": results,
        },
        message=f"Found {len(results)} similar products",
    )


# ─── Admin: Bulk Generate All Tenants ──────────────────────────────────────

@router.post("/generate-all")
async def generate_all_embeddings(
    current_user: User = Depends(deps.get_platform_admin),
):
    """
    Generate embeddings for ALL tenants' products. Superadmin only.
    """
    if not embedding_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Embedding service not configured. Set VOYAGE_API_KEY.",
        )

    result = await embedding_service.generate_all_tenants_embeddings()

    return StandardResponse(
        data=result,
        message=f"Embedded {result['total_embedded']}/{result['total_products']} products across {result['total_tenants']} tenants",
    )
