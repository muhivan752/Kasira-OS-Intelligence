"""
Kasira Ingredient Stock Service — Deduct bahan baku berdasarkan resep saat order.

Digunakan saat outlet.stock_mode == 'recipe':
  - Cari active recipe untuk product
  - Deduct setiap ingredient dari outlet_stock
  - Event-sourced: append stock.ingredient_sale event

Golden Rules: #8 (event append-only), #30 (optimistic lock), #47 (CHECK >= 0)
"""

import logging
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.product import OutletStock
from backend.models.event import Event

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def deduct_ingredients_for_product(
    db: AsyncSession,
    *,
    product_id: UUID,
    quantity: int,
    outlet_id: UUID,
    order_id: UUID,
    user_id: UUID,
    tier: str,
) -> None:
    """
    Deduct ingredient stock based on active recipe for a product.
    Called from create_order when outlet.stock_mode == 'recipe'.
    """
    # 1. Load active recipe with ingredients
    recipe = (await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
        .where(
            Recipe.product_id == product_id,
            Recipe.is_active == True,
            Recipe.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    if not recipe:
        raise HTTPException(status_code=400, detail="Produk belum memiliki resep aktif. Tambahkan resep terlebih dahulu.")

    # Filter active, non-optional ingredients
    active_ingredients = [
        ri for ri in recipe.ingredients
        if ri.deleted_at is None and not ri.is_optional
    ]

    if not active_ingredients:
        raise HTTPException(status_code=400, detail="Resep produk ini belum memiliki bahan baku. Tambahkan bahan dan jumlah per porsi di menu Resep.")

    # Validate all quantities > 0
    zero_qty = [
        ri.ingredient.name if ri.ingredient else str(ri.ingredient_id)
        for ri in active_ingredients if ri.quantity <= 0
    ]
    if zero_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Bahan berikut belum diisi jumlah per porsi: {', '.join(zero_qty[:5])}. Edit resep dan isi qty yang benar."
        )

    # 2. Pre-check: load all outlet_stock records and verify sufficient stock
    ingredient_ids = [ri.ingredient_id for ri in active_ingredients]

    stocks = (await db.execute(
        select(OutletStock)
        .where(
            OutletStock.outlet_id == outlet_id,
            OutletStock.ingredient_id.in_(ingredient_ids),
            OutletStock.deleted_at.is_(None),
        )
        .with_for_update()
    )).scalars().all()

    stock_map = {s.ingredient_id: s for s in stocks}

    # Check all ingredients have sufficient stock before deducting any
    insufficient = []
    for ri in active_ingredients:
        needed = ri.quantity * quantity
        stock = stock_map.get(ri.ingredient_id)
        available = stock.computed_stock if stock else 0.0
        if available < needed:
            ing_name = ri.ingredient.name if ri.ingredient else str(ri.ingredient_id)
            insufficient.append(f"{ing_name} (butuh {needed} {ri.quantity_unit}, sisa {available})")

    if insufficient:
        raise HTTPException(
            status_code=400,
            detail=f"Stok bahan baku tidak cukup: {'; '.join(insufficient)}"
        )

    # 3. Deduct each ingredient with optimistic lock
    now = datetime.now(timezone.utc)
    for ri in active_ingredients:
        deduct_qty = ri.quantity * quantity
        stock = stock_map.get(ri.ingredient_id)

        if not stock:
            # Should not happen (caught above), but safety net
            raise HTTPException(status_code=400, detail=f"Stok {ri.ingredient.name} belum diinisialisasi")

        stock_before = stock.computed_stock
        stock_after = stock_before - deduct_qty

        # Append event
        event = Event(
            outlet_id=outlet_id,
            stream_id=f"ingredient:{ri.ingredient_id}",
            event_type="stock.ingredient_sale",
            event_data={
                "ingredient_id": str(ri.ingredient_id),
                "outlet_id": str(outlet_id),
                "product_id": str(product_id),
                "order_id": str(order_id),
                "recipe_id": str(recipe.id),
                "quantity_per_unit": ri.quantity,
                "order_quantity": quantity,
                "total_deducted": deduct_qty,
                "stock_before": stock_before,
                "stock_after": stock_after,
                "tier": tier,
                "user_id": str(user_id),
            },
        )
        db.add(event)

        # Update outlet_stock with optimistic lock + retry
        for attempt in range(MAX_RETRIES):
            result = await db.execute(
                update(OutletStock).where(
                    OutletStock.id == stock.id,
                    OutletStock.row_version == stock.row_version + attempt,
                ).values(
                    computed_stock=OutletStock.computed_stock - deduct_qty,
                    row_version=OutletStock.row_version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount > 0:
                break
            # Refresh for next attempt
            await db.refresh(stock)
        else:
            raise HTTPException(status_code=409, detail=f"Concurrent update pada stok {ri.ingredient.name}, coba lagi")

    logger.info(
        "Ingredient stock deducted for order %s, product %s, %d ingredients",
        order_id, product_id, len(active_ingredients),
    )
