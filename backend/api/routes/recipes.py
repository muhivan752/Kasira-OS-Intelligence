import uuid
from typing import Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.api import deps
from backend.core.database import get_db
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.ingredient import Ingredient
from backend.models.product import Product
from backend.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeIngredientResponse, HPPProductResponse, HPPIngredientDetail,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])


def _build_recipe_response(recipe: Recipe) -> RecipeResponse:
    """Build RecipeResponse with ingredient details and HPP calculation."""
    total_cost = Decimal("0")
    ing_responses = []

    for ri in recipe.ingredients:
        if ri.deleted_at is not None:
            continue
        ing = ri.ingredient
        line_cost = Decimal(str(ri.quantity)) * (ing.cost_per_base_unit if ing else Decimal("0"))
        total_cost += line_cost

        ing_responses.append(RecipeIngredientResponse(
            id=ri.id,
            ingredient_id=ri.ingredient_id,
            ingredient_name=ing.name if ing else None,
            ingredient_unit=ing.base_unit if ing else None,
            ingredient_cost=ing.cost_per_base_unit if ing else None,
            quantity=ri.quantity,
            quantity_unit=ri.quantity_unit,
            is_optional=ri.is_optional,
            notes=ri.notes,
            line_cost=line_cost,
        ))

    product_name = recipe.product.name if recipe.product else None

    return RecipeResponse(
        id=recipe.id,
        product_id=recipe.product_id,
        product_name=product_name,
        version=recipe.version,
        is_active=recipe.is_active,
        notes=recipe.notes,
        ingredients=ing_responses,
        total_cost=total_cost,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


@router.get("/", response_model=StandardResponse[List[RecipeResponse]])
async def list_recipes(
    request: Request,
    product_id: Optional[uuid.UUID] = None,
    brand_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    stmt = (
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.product),
        )
        .where(Recipe.deleted_at.is_(None), Recipe.is_active == True)
    )
    if product_id:
        stmt = stmt.where(Recipe.product_id == product_id)
    if brand_id:
        stmt = stmt.join(Product).where(Product.brand_id == brand_id)

    result = await db.execute(stmt)
    recipes = result.scalars().all()

    return StandardResponse(
        data=[_build_recipe_response(r) for r in recipes],
        request_id=request.state.request_id,
    )


@router.post("/", response_model=StandardResponse[RecipeResponse])
async def create_recipe(
    request: Request,
    recipe_in: RecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    # Validate product exists
    product = (await db.execute(
        select(Product).where(Product.id == recipe_in.product_id, Product.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

    if not recipe_in.ingredients:
        raise HTTPException(status_code=400, detail="Resep harus memiliki minimal 1 bahan baku")

    # Deactivate existing active recipes for this product
    await db.execute(
        update(Recipe).where(
            Recipe.product_id == recipe_in.product_id,
            Recipe.is_active == True,
            Recipe.deleted_at.is_(None),
        ).values(is_active=False, updated_at=datetime.now(timezone.utc))
    )

    # Get next version
    existing = (await db.execute(
        select(Recipe.version).where(
            Recipe.product_id == recipe_in.product_id,
            Recipe.deleted_at.is_(None),
        ).order_by(Recipe.version.desc()).limit(1)
    )).scalar()
    next_version = (existing or 0) + 1

    # Create recipe
    recipe = Recipe(
        product_id=recipe_in.product_id,
        version=next_version,
        is_active=True,
        created_by=current_user.id,
        notes=recipe_in.notes,
    )
    db.add(recipe)
    await db.flush()

    # Create recipe ingredients
    for ri_in in recipe_in.ingredients:
        # Validate ingredient exists
        ing = (await db.execute(
            select(Ingredient).where(Ingredient.id == ri_in.ingredient_id, Ingredient.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not ing:
            raise HTTPException(status_code=404, detail=f"Bahan baku {ri_in.ingredient_id} tidak ditemukan")

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ri_in.ingredient_id,
            quantity=ri_in.quantity,
            quantity_unit=ri_in.quantity_unit,
            is_optional=ri_in.is_optional,
            notes=ri_in.notes,
        )
        db.add(ri)

    await log_audit(
        db=db, action="CREATE", entity="recipes", entity_id=recipe.id,
        after_state={"product_id": str(recipe_in.product_id), "version": next_version, "ingredients_count": len(recipe_in.ingredients)},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    # Auto-rebuild knowledge graph (non-blocking)
    try:
        from backend.services.knowledge_graph_service import rebuild_graph
        await rebuild_graph(tenant_id=current_user.tenant_id, brand_id=product.brand_id, db=db)
        await db.commit()
    except Exception as e:
        logger.warning(f"KG rebuild after recipe create: {e}")

    # Reload with relationships
    loaded = (await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.product),
        )
        .where(Recipe.id == recipe.id)
    )).scalar_one()

    return StandardResponse(
        success=True, data=_build_recipe_response(loaded),
        message="Resep berhasil dibuat", request_id=request.state.request_id,
    )


@router.put("/{recipe_id}", response_model=StandardResponse[RecipeResponse])
async def update_recipe(
    request: Request,
    recipe_id: uuid.UUID,
    recipe_in: RecipeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """Update recipe by creating a new version (old version deactivated)."""
    old_recipe = (await db.execute(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not old_recipe:
        raise HTTPException(status_code=404, detail="Resep tidak ditemukan")

    if not recipe_in.ingredients:
        raise HTTPException(status_code=400, detail="Resep harus memiliki minimal 1 bahan baku")

    # Deactivate old recipe
    old_recipe.is_active = False
    old_recipe.updated_at = datetime.now(timezone.utc)

    # Create new version
    new_recipe = Recipe(
        product_id=old_recipe.product_id,
        version=old_recipe.version + 1,
        is_active=True,
        created_by=current_user.id,
        notes=recipe_in.notes or old_recipe.notes,
    )
    db.add(new_recipe)
    await db.flush()

    for ri_in in recipe_in.ingredients:
        ri = RecipeIngredient(
            recipe_id=new_recipe.id,
            ingredient_id=ri_in.ingredient_id,
            quantity=ri_in.quantity,
            quantity_unit=ri_in.quantity_unit,
            is_optional=ri_in.is_optional,
            notes=ri_in.notes,
        )
        db.add(ri)

    await log_audit(
        db=db, action="UPDATE", entity="recipes", entity_id=new_recipe.id,
        before_state={"old_recipe_id": str(recipe_id), "old_version": old_recipe.version},
        after_state={"new_version": new_recipe.version, "ingredients_count": len(recipe_in.ingredients)},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    # Auto-rebuild knowledge graph
    try:
        from backend.services.knowledge_graph_service import rebuild_graph
        product = (await db.execute(select(Product).where(Product.id == old_recipe.product_id))).scalar_one()
        await rebuild_graph(tenant_id=current_user.tenant_id, brand_id=product.brand_id, db=db)
        await db.commit()
    except Exception as e:
        logger.warning(f"KG rebuild after recipe update: {e}")

    loaded = (await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.product),
        )
        .where(Recipe.id == new_recipe.id)
    )).scalar_one()

    return StandardResponse(
        success=True, data=_build_recipe_response(loaded),
        message="Resep berhasil diperbarui", request_id=request.state.request_id,
    )


@router.delete("/{recipe_id}", response_model=StandardResponse[dict])
async def delete_recipe(
    request: Request,
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    recipe = (await db.execute(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Resep tidak ditemukan")

    await db.execute(
        update(Recipe).where(Recipe.id == recipe_id)
        .values(deleted_at=datetime.now(timezone.utc), is_active=False)
    )
    await log_audit(
        db=db, action="DELETE", entity="recipes", entity_id=recipe_id,
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    # Auto-rebuild knowledge graph
    try:
        from backend.services.knowledge_graph_service import rebuild_graph
        product = (await db.execute(select(Product).where(Product.id == recipe.product_id))).scalar_one()
        await rebuild_graph(tenant_id=current_user.tenant_id, brand_id=product.brand_id, db=db)
        await db.commit()
    except Exception as e:
        logger.warning(f"KG rebuild after recipe delete: {e}")

    return StandardResponse(success=True, data={"ok": True}, message="Resep dihapus", request_id=request.state.request_id)


@router.get("/hpp", response_model=StandardResponse[List[HPPProductResponse]])
async def get_hpp_report(
    request: Request,
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """HPP report: cost vs selling price for all products with recipes."""
    products = (await db.execute(
        select(Product).where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
            Product.is_active == True,
        ).order_by(Product.name)
    )).scalars().all()

    # Load all active recipes with ingredients in one query
    product_ids = [p.id for p in products]
    recipes = (await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
        .where(
            Recipe.product_id.in_(product_ids),
            Recipe.is_active == True,
            Recipe.deleted_at.is_(None),
        )
    )).scalars().all()

    recipe_map = {r.product_id: r for r in recipes}

    responses = []
    for product in products:
        recipe = recipe_map.get(product.id)
        ingredient_details = []
        if recipe:
            recipe_cost = Decimal("0")
            for ri in recipe.ingredients:
                if ri.deleted_at is not None:
                    continue
                ing = ri.ingredient
                cost_per_unit = ing.cost_per_base_unit if ing else Decimal("0")
                line_cost = Decimal(str(ri.quantity)) * cost_per_unit
                recipe_cost += line_cost
                ingredient_details.append(HPPIngredientDetail(
                    name=ing.name if ing else "?",
                    quantity=ri.quantity,
                    unit=ri.quantity_unit or (ing.base_unit if ing else ""),
                    buy_price=ing.buy_price if ing and ing.buy_price else Decimal("0"),
                    buy_qty=ing.buy_qty if ing and ing.buy_qty else 1,
                    cost_per_unit=cost_per_unit,
                    line_cost=line_cost,
                ))
        else:
            recipe_cost = Decimal("0")

        selling_price = product.base_price or Decimal("0")
        margin = selling_price - recipe_cost
        margin_pct = float(margin / selling_price * 100) if selling_price > 0 else 0.0

        responses.append(HPPProductResponse(
            product_id=product.id,
            product_name=product.name,
            selling_price=selling_price,
            recipe_cost=recipe_cost,
            margin_amount=margin,
            margin_percent=round(margin_pct, 1),
            has_recipe=recipe is not None,
            ingredients=ingredient_details,
        ))

    return StandardResponse(data=responses, request_id=request.state.request_id)
