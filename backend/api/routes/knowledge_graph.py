"""
Knowledge Graph API — Build and query ingredient/product relationships.
Pro+ only. Used by AI chatbot and dashboard insights.
"""

import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.schemas.response import StandardResponse
from backend.services.knowledge_graph_service import (
    rebuild_graph,
    get_affected_products,
    get_product_ingredients,
    get_most_used_ingredients,
)
from sqlalchemy import select

router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])


@router.post("/rebuild", response_model=StandardResponse)
async def rebuild_knowledge_graph(
    request: Request,
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Rebuild knowledge graph from current recipe/ingredient/category data."""
    result = await rebuild_graph(
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        db=db,
    )
    await db.commit()
    return StandardResponse(data=result, request_id=request.state.request_id)


@router.get("/affected-products/{ingredient_id}", response_model=StandardResponse)
async def affected_products(
    ingredient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get products affected if an ingredient runs out or price changes."""
    result = await get_affected_products(
        tenant_id=current_user.tenant_id,
        ingredient_id=ingredient_id,
        db=db,
    )
    return StandardResponse(data=result, request_id=request.state.request_id)


@router.get("/product-ingredients/{product_id}", response_model=StandardResponse)
async def product_ingredients(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get ingredient graph for a product."""
    result = await get_product_ingredients(
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        db=db,
    )
    return StandardResponse(data=result, request_id=request.state.request_id)


@router.get("/top-ingredients", response_model=StandardResponse)
async def top_ingredients(
    request: Request,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get most-used ingredients across all products."""
    result = await get_most_used_ingredients(
        tenant_id=current_user.tenant_id,
        db=db,
        limit=limit,
    )
    return StandardResponse(data=result, request_id=request.state.request_id)
