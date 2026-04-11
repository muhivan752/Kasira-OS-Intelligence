import uuid
from typing import Any, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from backend.api import deps
from backend.core.database import get_db
from backend.models.ingredient import Ingredient
from backend.models.product import OutletStock
from backend.models.event import Event
from backend.schemas.ingredient import IngredientCreate, IngredientUpdate, IngredientResponse, IngredientRestock
from backend.schemas.response import StandardResponse, ResponseMeta
from backend.services.audit import log_audit

router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])


@router.get("/", response_model=StandardResponse[List[IngredientResponse]])
async def list_ingredients(
    request: Request,
    brand_id: uuid.UUID,
    outlet_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    stmt = select(Ingredient).where(
        Ingredient.brand_id == brand_id,
        Ingredient.deleted_at.is_(None),
    ).order_by(Ingredient.name).offset(skip).limit(limit)

    result = await db.execute(stmt)
    ingredients = result.scalars().all()

    # Optionally join outlet_stock for current stock levels
    stock_map: dict = {}
    if outlet_id and ingredients:
        ing_ids = [i.id for i in ingredients]
        stock_result = await db.execute(
            select(OutletStock.ingredient_id, OutletStock.computed_stock, OutletStock.min_stock_base)
            .where(
                OutletStock.outlet_id == outlet_id,
                OutletStock.ingredient_id.in_(ing_ids),
                OutletStock.deleted_at.is_(None),
            )
        )
        for row in stock_result.all():
            stock_map[row.ingredient_id] = {
                "current_stock": row.computed_stock,
                "min_stock": row.min_stock_base,
            }

    responses = []
    for ing in ingredients:
        resp = IngredientResponse.model_validate(ing)
        stock_info = stock_map.get(ing.id)
        if stock_info:
            resp.current_stock = stock_info["current_stock"]
            resp.min_stock = stock_info["min_stock"]
        responses.append(resp)

    meta = ResponseMeta(page=(skip // limit) + 1, per_page=limit, total=len(responses))
    return StandardResponse(data=responses, meta=meta, request_id=request.state.request_id)


@router.post("/", response_model=StandardResponse[IngredientResponse])
async def create_ingredient(
    request: Request,
    ingredient_in: IngredientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    ingredient = Ingredient(**ingredient_in.model_dump())
    db.add(ingredient)
    await db.flush()

    await log_audit(
        db=db, action="CREATE", entity="ingredients", entity_id=ingredient.id,
        after_state=ingredient_in.model_dump(mode="json"),
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(ingredient)

    return StandardResponse(
        success=True, data=IngredientResponse.model_validate(ingredient),
        message="Bahan baku berhasil ditambahkan", request_id=request.state.request_id,
    )


@router.get("/{ingredient_id}", response_model=StandardResponse[IngredientResponse])
async def get_ingredient(
    request: Request,
    ingredient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    ingredient = (await db.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id, Ingredient.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Bahan baku tidak ditemukan")

    return StandardResponse(data=IngredientResponse.model_validate(ingredient), request_id=request.state.request_id)


@router.put("/{ingredient_id}", response_model=StandardResponse[IngredientResponse])
async def update_ingredient(
    request: Request,
    ingredient_id: uuid.UUID,
    ingredient_in: IngredientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    ingredient = (await db.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id, Ingredient.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Bahan baku tidak ditemukan")

    if ingredient.row_version != ingredient_in.row_version:
        raise HTTPException(status_code=409, detail="Data sudah diubah, silakan refresh")

    update_data = ingredient_in.model_dump(exclude_unset=True, exclude={"row_version"})
    before_state = {k: getattr(ingredient, k) for k in update_data}

    await db.execute(
        update(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.row_version == ingredient_in.row_version,
        ).values(**update_data, row_version=Ingredient.row_version + 1, updated_at=datetime.now(timezone.utc))
    )

    await log_audit(
        db=db, action="UPDATE", entity="ingredients", entity_id=ingredient_id,
        before_state=before_state, after_state=update_data,
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(ingredient)

    return StandardResponse(
        success=True, data=IngredientResponse.model_validate(ingredient),
        message="Bahan baku berhasil diperbarui", request_id=request.state.request_id,
    )


@router.delete("/{ingredient_id}", response_model=StandardResponse[dict])
async def delete_ingredient(
    request: Request,
    ingredient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    ingredient = (await db.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id, Ingredient.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Bahan baku tidak ditemukan")

    await db.execute(
        update(Ingredient).where(Ingredient.id == ingredient_id)
        .values(deleted_at=datetime.now(timezone.utc))
    )
    await log_audit(
        db=db, action="DELETE", entity="ingredients", entity_id=ingredient_id,
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    return StandardResponse(success=True, data={"ok": True}, message="Bahan baku dihapus", request_id=request.state.request_id)


@router.post("/{ingredient_id}/restock", response_model=StandardResponse[IngredientResponse])
async def restock_ingredient(
    request: Request,
    ingredient_id: uuid.UUID,
    restock_in: IngredientRestock,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    ingredient = (await db.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id, Ingredient.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Bahan baku tidak ditemukan")

    # Get or create outlet_stock record
    outlet_stock = (await db.execute(
        select(OutletStock).where(
            OutletStock.outlet_id == restock_in.outlet_id,
            OutletStock.ingredient_id == ingredient_id,
            OutletStock.deleted_at.is_(None),
        ).with_for_update()
    )).scalar_one_or_none()

    if not outlet_stock:
        outlet_stock = OutletStock(
            outlet_id=restock_in.outlet_id,
            ingredient_id=ingredient_id,
            computed_stock=0.0,
        )
        db.add(outlet_stock)
        await db.flush()

    stock_before = outlet_stock.computed_stock
    stock_after = stock_before + restock_in.quantity

    # Append event
    event = Event(
        stream_id=f"ingredient:{ingredient_id}",
        event_type="stock.ingredient_restock",
        event_data={
            "ingredient_id": str(ingredient_id),
            "outlet_id": str(restock_in.outlet_id),
            "quantity": restock_in.quantity,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "notes": restock_in.notes,
            "user_id": str(current_user.id),
        },
    )
    db.add(event)

    # Update outlet_stock with optimistic lock
    result = await db.execute(
        update(OutletStock).where(
            OutletStock.id == outlet_stock.id,
            OutletStock.row_version == outlet_stock.row_version,
        ).values(
            computed_stock=stock_after,
            row_version=OutletStock.row_version + 1,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=409, detail="Concurrent update, coba lagi")

    await log_audit(
        db=db, action="RESTOCK", entity="ingredients", entity_id=ingredient_id,
        after_state={"quantity": restock_in.quantity, "stock_after": stock_after},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(ingredient)

    resp = IngredientResponse.model_validate(ingredient)
    resp.current_stock = stock_after
    return StandardResponse(
        success=True, data=resp,
        message=f"Restock {restock_in.quantity} {ingredient.base_unit} berhasil",
        request_id=request.state.request_id,
    )


@router.get("/low-stock", response_model=StandardResponse[List[IngredientResponse]])
async def low_stock_ingredients(
    request: Request,
    outlet_id: uuid.UUID,
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """Ingredients where current stock <= min_stock_base."""
    stmt = (
        select(Ingredient, OutletStock.computed_stock, OutletStock.min_stock_base)
        .outerjoin(OutletStock, (OutletStock.ingredient_id == Ingredient.id) & (OutletStock.outlet_id == outlet_id))
        .where(
            Ingredient.brand_id == brand_id,
            Ingredient.deleted_at.is_(None),
            Ingredient.ingredient_type == "recipe",
        )
        .having(
            func.coalesce(OutletStock.computed_stock, 0) <= func.coalesce(OutletStock.min_stock_base, 0)
        )
        .group_by(Ingredient.id, OutletStock.computed_stock, OutletStock.min_stock_base)
    )

    result = await db.execute(stmt)
    responses = []
    for row in result.all():
        ing = row[0]
        resp = IngredientResponse.model_validate(ing)
        resp.current_stock = row[1] or 0.0
        resp.min_stock = row[2] or 0.0
        responses.append(resp)

    return StandardResponse(data=responses, request_id=request.state.request_id)
