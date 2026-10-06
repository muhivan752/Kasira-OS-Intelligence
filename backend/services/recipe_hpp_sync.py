"""Pull-only HPP snapshots, refreshed by recipe and ingredient dependencies."""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from backend.models.product import Product
from backend.models.recipe import Recipe, RecipeIngredient
from backend.services.unit_utils import decimal_ingredient_cost_contribution


def recipe_hpp_snapshot(recipe):
    total = Decimal(0)
    complete = True
    details = []
    active = recipe.is_active and recipe.deleted_at is None
    if active:
        for ri in recipe.ingredients:
            ing = ri.ingredient
            if ri.deleted_at is not None or ing is None or ing.deleted_at is not None:
                continue
            contributes = not ri.is_optional and (ri.quantity or 0) > 0
            cost = decimal_ingredient_cost_contribution(ri) if contributes else Decimal(0)
            if cost is None:
                complete = False
            else:
                total += cost
            details.append({
                "name": ing.name,
                "quantity": ri.quantity,
                "unit": ri.quantity_unit,
                "cost_per_unit": str(ing.cost_per_base_unit or 0),
                "cost_unit": ing.base_unit,
                "line_cost": str(cost) if cost is not None else None,
                "is_optional": ri.is_optional,
                "needs_review": bool(ing.needs_review),
            })
    return {
        "recipe_id": str(recipe.id),
        "product_id": str(recipe.product_id),
        "is_estimated": bool(recipe.is_estimated),
        "needs_review": any(d["needs_review"] and not d["is_optional"] for d in details),
        "total_cost": str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if active and complete else None,
        "ingredients": details,
    }


async def get_recipe_hpp_changes(db, brand_id, changes):
    recipe_ids = {r["id"] for r in changes.recipes}
    recipe_ids.update(r["recipe_id"] for r in changes.recipe_ingredients)
    ingredient_ids = [r["id"] for r in changes.ingredients]
    if not recipe_ids and not ingredient_ids:
        return []
    # Ingredient prices and soft-deletes do not bump the parent recipe timestamp.
    # Refresh its derived costs whenever either dependency appears on a pull page.
    affected = select(RecipeIngredient.recipe_id).where(
        RecipeIngredient.ingredient_id.in_(ingredient_ids)
    )
    stmt = (
        select(Recipe).join(Product)
        .where(Product.brand_id == brand_id,
               or_(Recipe.id.in_(recipe_ids), Recipe.id.in_(affected)))
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
        .execution_options(populate_existing=True)
    )
    recipes = (await db.execute(stmt)).scalars().all()
    return [recipe_hpp_snapshot(r) for r in recipes]
