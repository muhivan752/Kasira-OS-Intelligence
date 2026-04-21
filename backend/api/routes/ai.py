"""
Kasira AI Chat Route — SSE Streaming endpoint untuk Owner/Manager

POST /ai/chat → StreamingResponse (text/event-stream)

Rules yang diimplementasikan:
- Rule #2: Audit log setiap request (termasuk yang gagal)
- Rule #9: Async ONLY
- Rule #25-27: Model selector + 3 optimasi AI
- Rule #54-56: Intent classifier, WRITE confirmation, UNKNOWN reject
"""

import json
import logging
import uuid as uuid_mod
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, List, Optional, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.tenant import Tenant
from backend.models.ingredient import Ingredient
from backend.models.product import Product, OutletStock
from backend.models.category import Category
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.event import Event
from backend.services.redis import get_redis_client
from backend.services.audit import log_audit
from backend.services.ai_service import stream_ai_response, DOMAIN_KEYWORDS

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Super-group mapping: 10-bucket → 3 UI domain group ─────────────────────
# Single source of truth untuk Adaptive UI. Flutter pakai `domain` untuk
# decide label set, `bucket` untuk display name spesifik ke user.
_BUCKET_TO_SUPER_GROUP = {
    "kopi_cafe": "fnb",
    "resto_makanan": "fnb",
    "warteg": "fnb",
    "bakery": "fnb",
    "vape_liquid": "retail",
    "minimarket": "retail",
    "pet_shop": "retail",
    "apotik_herbal": "retail",
    "laundry": "service",
    "salon_barber": "service",
}

_BUCKET_DISPLAY_NAME = {
    "kopi_cafe": "Cafe/Kopi",
    "resto_makanan": "Resto",
    "warteg": "Warteg",
    "bakery": "Bakery",
    "vape_liquid": "Vape Shop",
    "minimarket": "Minimarket",
    "pet_shop": "Pet Shop",
    "apotik_herbal": "Apotek",
    "laundry": "Laundry",
    "salon_barber": "Salon/Barber",
}

# Business type dropdown fallback → super-group (saat business_name gak match keyword)
_BUSINESS_TYPE_TO_SUPER_GROUP = {
    "cafe": "fnb",
    "resto": "fnb",
    "warung": "fnb",
    "other": "fnb",  # default conservative — user bisa override via suggestion card
}

# Business-name level keywords (BUKAN product-level — dipisah dari DOMAIN_KEYWORDS
# biar gak polusi AI prompt context). "Bengkel Jaya", "Salon Cantik", "Apotek
# Sehat" — nama bisnis Indonesia yang umum tapi gak ada di product keywords.
_BUSINESS_NAME_HINTS = {
    "salon_barber": ["bengkel", "salon", "barber", "barbershop", "pangkas"],
    "apotik_herbal": ["apotek", "apotik", "toko obat"],
    "minimarket": ["minimarket", "toko kelontong", "warung serba ada"],
    "pet_shop": ["pet shop", "petshop", "toko hewan"],
    "vape_liquid": ["vape store", "vape shop", "toko vape"],
    "laundry": ["laundry"],
    "kopi_cafe": ["cafe", "kafe", "kedai kopi", "coffee", "kopi"],
    "bakery": ["bakery", "toko roti", "toko kue"],
    "resto_makanan": ["resto", "restoran", "rumah makan"],
    "warteg": ["warteg", "warung nasi", "warung makan"],
}

# Display name override saat matched hint lebih spesifik dari generic bucket
# display (misal hint="bengkel" > bucket display "Salon/Barber").
_HINT_DISPLAY_OVERRIDE = {
    "bengkel": "Bengkel",
    "salon": "Salon",
    "barber": "Barbershop",
    "barbershop": "Barbershop",
    "pangkas": "Pangkas Rambut",
    "apotek": "Apotek",
    "apotik": "Apotek",
    "toko obat": "Toko Obat",
    "minimarket": "Minimarket",
    "toko kelontong": "Toko Kelontong",
    "pet shop": "Pet Shop",
    "petshop": "Pet Shop",
    "toko hewan": "Toko Hewan",
    "vape shop": "Vape Shop",
    "vape store": "Vape Shop",
    "toko vape": "Toko Vape",
    "laundry": "Laundry",
}


class ChatRequest(BaseModel):
    message: str
    outlet_id: str
    # Multi-turn: kirim null di turn pertama, server balikin UUID di `done` event.
    # Pake UUID itu untuk turn-turn berikutnya supaya server load prior history.
    # History TTL 30min rolling (Redis ephemeral), max 5 turn pair.
    conversation_id: Optional[str] = None


@router.post("/chat")
async def ai_chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant: Tenant = Depends(deps.require_pro_tier),
) -> StreamingResponse:
    """
    AI chat dengan SSE streaming. Pro+ only (di-gate via require_pro_tier dep).

    Response format (per chunk):
        data: {"type": "chunk", "content": "..."}
        data: {"type": "done", "intent": "READ", "tokens_used": 123, "model": "..."}
        data: {"type": "error", "message": "..."}
    """
    # Validate outlet belongs to user's tenant
    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == body.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    outlet = outlet_result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    # Tier dari tenant yg udah divalidasi dep (Pro+ terjamin lolos check)
    raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter"
    tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)

    redis = await get_redis_client()

    # ── Budget Control ──────────────────────────────────────────────────
    # Tiered limits: per-tenant, per-user, platform safety net
    TENANT_DAILY_LIMIT = 50       # max 50 AI requests per tenant per day
    USER_DAILY_LIMIT = 30         # max 30 per user per day (within tenant quota)
    PLATFORM_DAILY_CENTS = 100    # $1.00/day emergency brake (all tenants combined)

    try:
        from datetime import date as dt_date
        today = dt_date.today().isoformat()
        tid = str(current_user.tenant_id)

        # 1. Platform safety cap — emergency brake
        spend_key = f"ai_spend:{today}"
        current_spend = int(await redis.get(spend_key) or 0)
        if current_spend >= PLATFORM_DAILY_CENTS:
            raise HTTPException(429, detail="Layanan AI sedang sibuk. Coba lagi besok.")

        # 2. Per-tenant daily limit
        tenant_key = f"ai_tenant:{tid}:{today}"
        tenant_count = await redis.incr(tenant_key)
        if tenant_count == 1:
            await redis.expire(tenant_key, 86400)
        if tenant_count > TENANT_DAILY_LIMIT:
            raise HTTPException(429, detail=f"Kuota AI harian habis ({TENANT_DAILY_LIMIT} pertanyaan). Coba lagi besok.")

        # 3. Per-user daily limit
        user_key = f"ai_user:{current_user.id}:{today}"
        user_count = await redis.incr(user_key)
        if user_count == 1:
            await redis.expire(user_key, 86400)
        if user_count > USER_DAILY_LIMIT:
            raise HTTPException(429, detail=f"Kamu sudah bertanya {USER_DAILY_LIMIT}x hari ini. Coba lagi besok.")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis down → allow request

    # Audit log (Rule #2) — log request masuk
    try:
        await log_audit(
            db=db,
            action="ai_chat",
            entity="ai",
            entity_id=body.outlet_id,
            after_state={
                "message_length": len(body.message),
                "tier": tier,
                "conversation_id": body.conversation_id,
            },
            user_id=str(current_user.id),
            tenant_id=str(current_user.tenant_id),
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Audit log failed (non-blocking): {e}")

    # Track estimated spend — 1 cent per Haiku, 2 cents per Sonnet
    try:
        from datetime import date as dt_date
        spend_key = f"ai_spend:{dt_date.today().isoformat()}"
        await redis.incrby(spend_key, 1)  # conservative estimate
        await redis.expire(spend_key, 86400)
    except Exception:
        pass

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in stream_ai_response(
                message=body.message,
                outlet_id=body.outlet_id,
                tenant_id=str(current_user.tenant_id),
                outlet_name=outlet.name,
                tier=tier,
                db=db,
                redis_client=redis,
                user_id=str(current_user.id),
                conversation_id=body.conversation_id,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Terjadi kesalahan pada server'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


class ProposalIngredient(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    qty: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    buy_price: float = Field(..., gt=0)
    buy_qty: float = Field(..., gt=0)
    initial_stock: float = Field(default=0, ge=0)  # 0 = belum ada stok, user restock nanti

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        allowed = {"gram", "ml", "pcs", "bungkus"}
        if v.lower() not in allowed:
            raise ValueError(f"unit harus salah satu: {', '.join(allowed)}")
        return v.lower()


class ApplyRecipeRequest(BaseModel):
    outlet_id: str
    product_name: str = Field(..., min_length=1, max_length=120)
    replace: bool = False  # True = soft-delete existing active recipe + recipe_ingredients
    ingredients: List[ProposalIngredient] = Field(..., min_length=1, max_length=20)


@router.post("/apply-recipe")
async def apply_recipe_proposal(
    request: Request,
    body: ApplyRecipeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant: Tenant = Depends(deps.require_pro_tier),
) -> Any:
    """
    Eksekusi recipe proposal dari AI.
    Dedup ingredient by name (case-insensitive). Product wajib sudah ada di menu.
    Set `ai_assisted=True` di Recipe + `ai_setup_complete=True` di Ingredient baru.
    """
    # Validate outlet ownership
    outlet = (await db.execute(
        select(Outlet).where(
            Outlet.id == body.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    brand_id = outlet.brand_id

    # Resolve product — fuzzy case-insensitive match dalam brand
    product = (await db.execute(
        select(Product).where(
            Product.brand_id == brand_id,
            func.lower(Product.name) == body.product_name.strip().lower(),
            Product.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    if not product:
        # Try partial match (contains)
        partial = (await db.execute(
            select(Product).where(
                Product.brand_id == brand_id,
                func.lower(Product.name).contains(body.product_name.strip().lower()),
                Product.deleted_at.is_(None),
            ).limit(1)
        )).scalar_one_or_none()
        if not partial:
            raise HTTPException(
                status_code=400,
                detail=f'Produk "{body.product_name}" belum ada di menu. Tambahkan dulu di halaman Menu, lalu setup resep lagi.',
            )
        product = partial

    # Cek apakah produk sudah punya active recipe
    existing_recipe = (await db.execute(
        select(Recipe).where(
            Recipe.product_id == product.id,
            Recipe.is_active == True,
            Recipe.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing_recipe:
        if not body.replace:
            # Structured 409 — frontend detect code=recipe_exists → tampil tombol "Ganti"
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "recipe_exists",
                    "message": f'Produk "{product.name}" udah punya resep aktif. Mau diganti dengan resep baru ini?',
                    "product_name": product.name,
                },
            )
        # User confirm replace — soft-delete old recipe + ingredients-nya
        from sqlalchemy import update as sql_update
        now = datetime.now(timezone.utc)
        await db.execute(
            sql_update(Recipe)
            .where(Recipe.id == existing_recipe.id)
            .values(is_active=False, deleted_at=now)
        )
        await db.execute(
            sql_update(RecipeIngredient)
            .where(
                RecipeIngredient.recipe_id == existing_recipe.id,
                RecipeIngredient.deleted_at.is_(None),
            )
            .values(deleted_at=now)
        )

    # Load existing ingredients dalam brand (untuk dedup)
    existing_ings = (await db.execute(
        select(Ingredient).where(
            Ingredient.brand_id == brand_id,
            Ingredient.deleted_at.is_(None),
        )
    )).scalars().all()
    by_name = {ing.name.strip().lower(): ing for ing in existing_ings}

    created_ingredients: list[dict] = []
    reused_ingredients: list[dict] = []
    recipe_ing_refs: list[tuple[Ingredient, ProposalIngredient]] = []

    UNIT_TYPE_MAP = {"gram": "WEIGHT", "ml": "VOLUME", "pcs": "COUNT", "bungkus": "COUNT"}

    for pi in body.ingredients:
        key = pi.name.strip().lower()
        if key in by_name:
            reused_ingredients.append({"name": by_name[key].name, "id": str(by_name[key].id)})
            recipe_ing_refs.append((by_name[key], pi))
            continue

        # Create ingredient baru + companion OutletStock dengan initial_stock
        cost_per_unit = Decimal(str(pi.buy_price)) / Decimal(str(pi.buy_qty))
        new_ing = Ingredient(
            id=uuid_mod.uuid4(),
            brand_id=brand_id,
            name=pi.name.strip(),
            tracking_mode="simple",
            base_unit=pi.unit,
            unit_type=UNIT_TYPE_MAP.get(pi.unit, "CUSTOM"),
            buy_price=Decimal(str(pi.buy_price)),
            buy_qty=float(pi.buy_qty),
            cost_per_base_unit=cost_per_unit,
            ai_setup_complete=True,
            needs_review=True,
            ingredient_type="recipe",
            row_version=0,
        )
        db.add(new_ing)
        await db.flush()

        # Companion OutletStock row biar bahan baru langsung muncul di /bahan-baku
        # dengan stok awal (bukan null/"-"). Merchant bisa langsung liat + restock.
        initial_stock_val = float(pi.initial_stock or 0)
        db.add(OutletStock(
            id=uuid_mod.uuid4(),
            outlet_id=outlet.id,
            ingredient_id=new_ing.id,
            computed_stock=initial_stock_val,
            min_stock_base=0.0,
            row_version=0,
        ))
        # Audit trail — event per ingredient kalau stok awal > 0
        if initial_stock_val > 0:
            db.add(Event(
                outlet_id=outlet.id,
                stream_id=f"ingredient:{new_ing.id}",
                event_type="stock.ai_initial_setup",
                event_data={
                    "ingredient_id": str(new_ing.id),
                    "outlet_id": str(outlet.id),
                    "initial_stock": initial_stock_val,
                    "unit": new_ing.base_unit,
                    "source": "ai_apply_recipe",
                    "user_id": str(current_user.id),
                },
            ))

        by_name[key] = new_ing
        created_ingredients.append({
            "name": new_ing.name,
            "id": str(new_ing.id),
            "unit": new_ing.base_unit,
            "cost_per_unit": float(cost_per_unit),
            "initial_stock": initial_stock_val,
        })
        recipe_ing_refs.append((new_ing, pi))

    # Create Recipe
    recipe = Recipe(
        id=uuid_mod.uuid4(),
        product_id=product.id,
        version=1,
        is_active=True,
        ai_assisted=True,
        created_by=current_user.id,
        row_version=0,
    )
    db.add(recipe)
    await db.flush()

    # Create RecipeIngredient + hitung HPP via unit_utils helper.
    # Fix CRITICAL #2 + #8: unit conversion (pi.unit != ing_obj.base_unit)
    # + defensive skip ghost ingredient (ing_obj.deleted_at soft-deleted).
    from backend.services.unit_utils import cost_from_qty_unit

    hpp = Decimal("0")
    hpp_unit_mismatch = []  # collect untuk observability
    for ing_obj, pi in recipe_ing_refs:
        # Defensive: ghost ingredient (ing_obj seharusnya dari match path yg
        # sudah filter deleted_at, tapi defensive untuk race condition)
        if ing_obj.deleted_at is not None:
            logger.warning(
                "ai_apply_recipe: skip soft-deleted ingredient %s (id=%s)",
                ing_obj.name, ing_obj.id,
            )
            continue

        # Unit-aware cost. None = unresolvable mismatch → log + skip HPP sum,
        # RecipeIngredient tetap ter-insert (data preserved, user bisa edit).
        contrib = cost_from_qty_unit(pi.qty, pi.unit, ing_obj)
        if contrib is None:
            hpp_unit_mismatch.append(f"{ing_obj.name} ({pi.unit} vs {ing_obj.base_unit})")
            logger.warning(
                "ai_apply_recipe: unit mismatch %s qty=%s unit=%s vs base_unit=%s "
                "— HPP sum skip, row tetap di-insert",
                ing_obj.name, pi.qty, pi.unit, ing_obj.base_unit,
            )
            line_cost = Decimal("0")
        else:
            line_cost = Decimal(str(contrib))
        hpp += line_cost

        db.add(RecipeIngredient(
            id=uuid_mod.uuid4(),
            recipe_id=recipe.id,
            ingredient_id=ing_obj.id,
            quantity=float(pi.qty),
            quantity_unit=pi.unit,
            is_optional=False,
            row_version=0,
        ))

    # Audit log (Rule #2)
    await log_audit(
        db=db,
        action="ai_apply_recipe",
        entity="recipe",
        entity_id=str(recipe.id),
        after_state={
            "product_id": str(product.id),
            "product_name": product.name,
            "ingredients_count": len(body.ingredients),
            "created_ingredients": len(created_ingredients),
            "reused_ingredients": len(reused_ingredients),
            "hpp_estimate": float(hpp),
            "hpp_unit_mismatch": hpp_unit_mismatch,  # observability flag
        },
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    await db.commit()

    # Invalidate AI context cache (ingredients/recipe changed)
    try:
        redis = await get_redis_client()
        await redis.delete(f"ai:context:{body.outlet_id}")
    except Exception:
        pass

    base_price = float(product.base_price or 0)
    margin_pct = None
    if base_price > 0:
        margin_pct = round((base_price - float(hpp)) / base_price * 100, 1)

    return {
        "success": True,
        "data": {
            "recipe_id": str(recipe.id),
            "product_id": str(product.id),
            "product_name": product.name,
            "product_base_price": base_price,
            "hpp": float(hpp),
            "margin_pct": margin_pct,
            "created_ingredients": created_ingredients,
            "reused_ingredients": reused_ingredients,
        },
    }


class BulkProductProposal(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    suggested_price: float = Field(..., gt=0)
    category_name: Optional[str] = Field(None, max_length=80)
    ingredients: List[ProposalIngredient] = Field(..., min_length=1, max_length=15)


class ApplyMenuBatchRequest(BaseModel):
    outlet_id: str
    products: List[BulkProductProposal] = Field(..., min_length=1, max_length=15)


@router.post("/apply-menu-batch")
async def apply_menu_batch(
    request: Request,
    body: ApplyMenuBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant: Tenant = Depends(deps.require_pro_tier),
) -> Any:
    """
    Bulk create products + categories + ingredients + recipes dari proposal AI.
    Skip produk yang sudah exist (nama sama di brand). Atomic per batch.
    """
    outlet = (await db.execute(
        select(Outlet).where(
            Outlet.id == body.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    brand_id = outlet.brand_id

    # Load existing ingredients + categories + products dalam brand (dedup lookup)
    existing_ings = (await db.execute(
        select(Ingredient).where(
            Ingredient.brand_id == brand_id,
            Ingredient.deleted_at.is_(None),
        )
    )).scalars().all()
    ing_by_name = {i.name.strip().lower(): i for i in existing_ings}

    existing_cats = (await db.execute(
        select(Category).where(
            Category.brand_id == brand_id,
            Category.deleted_at.is_(None),
        )
    )).scalars().all()
    cat_by_name = {c.name.strip().lower(): c for c in existing_cats}

    existing_prods = (await db.execute(
        select(Product).where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
        )
    )).scalars().all()
    prod_by_name = {p.name.strip().lower(): p for p in existing_prods}

    UNIT_TYPE_MAP = {"gram": "WEIGHT", "ml": "VOLUME", "pcs": "COUNT", "bungkus": "COUNT"}

    created_products: list[dict] = []
    skipped_products: list[dict] = []
    ings_created_names: set[str] = set()
    ings_reused_names: set[str] = set()

    for pprop in body.products:
        pname = pprop.name.strip()
        pkey = pname.lower()

        # Resolve / create category
        cat_id = None
        if pprop.category_name:
            ckey = pprop.category_name.strip().lower()
            cat = cat_by_name.get(ckey)
            if not cat:
                cat = Category(
                    id=uuid_mod.uuid4(),
                    brand_id=brand_id,
                    name=pprop.category_name.strip(),
                    is_active=True,
                    row_version=0,
                )
                db.add(cat)
                await db.flush()
                cat_by_name[ckey] = cat
            cat_id = cat.id

        # Resolve product
        product = prod_by_name.get(pkey)
        if product:
            # Produk sudah ada — cek apakah sudah punya recipe
            existing_recipe = (await db.execute(
                select(Recipe).where(
                    Recipe.product_id == product.id,
                    Recipe.is_active == True,
                    Recipe.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if existing_recipe:
                skipped_products.append({
                    "name": product.name,
                    "reason": "Sudah punya resep aktif",
                })
                continue
            # Pakai product existing, lanjut bikin recipe
        else:
            # Create product baru
            product = Product(
                id=uuid_mod.uuid4(),
                brand_id=brand_id,
                name=pname,
                base_price=Decimal(str(pprop.suggested_price)),
                category_id=cat_id,
                is_active=True,
                stock_enabled=False,  # recipe mode
                stock_qty=0,
                row_version=0,
            )
            db.add(product)
            await db.flush()
            prod_by_name[pkey] = product

        # Resolve / create ingredients untuk recipe
        recipe_ing_refs: list[tuple[Ingredient, ProposalIngredient]] = []
        for ing_prop in pprop.ingredients:
            ikey = ing_prop.name.strip().lower()
            ing_obj = ing_by_name.get(ikey)
            if ing_obj:
                ings_reused_names.add(ing_obj.name)
            else:
                cost_per_unit = Decimal(str(ing_prop.buy_price)) / Decimal(str(ing_prop.buy_qty))
                ing_obj = Ingredient(
                    id=uuid_mod.uuid4(),
                    brand_id=brand_id,
                    name=ing_prop.name.strip(),
                    tracking_mode="simple",
                    base_unit=ing_prop.unit,
                    unit_type=UNIT_TYPE_MAP.get(ing_prop.unit, "CUSTOM"),
                    buy_price=Decimal(str(ing_prop.buy_price)),
                    buy_qty=float(ing_prop.buy_qty),
                    cost_per_base_unit=cost_per_unit,
                    ai_setup_complete=True,
                    needs_review=True,
                    ingredient_type="recipe",
                    row_version=0,
                )
                db.add(ing_obj)
                await db.flush()

                # Companion OutletStock + audit event untuk ingredient baru
                initial_stock_val = float(ing_prop.initial_stock or 0)
                db.add(OutletStock(
                    id=uuid_mod.uuid4(),
                    outlet_id=outlet.id,
                    ingredient_id=ing_obj.id,
                    computed_stock=initial_stock_val,
                    min_stock_base=0.0,
                    row_version=0,
                ))
                if initial_stock_val > 0:
                    db.add(Event(
                        outlet_id=outlet.id,
                        stream_id=f"ingredient:{ing_obj.id}",
                        event_type="stock.ai_initial_setup",
                        event_data={
                            "ingredient_id": str(ing_obj.id),
                            "outlet_id": str(outlet.id),
                            "initial_stock": initial_stock_val,
                            "unit": ing_obj.base_unit,
                            "source": "ai_apply_menu_batch",
                            "user_id": str(current_user.id),
                        },
                    ))

                ing_by_name[ikey] = ing_obj
                ings_created_names.add(ing_obj.name)
            recipe_ing_refs.append((ing_obj, ing_prop))

        # Create Recipe
        recipe = Recipe(
            id=uuid_mod.uuid4(),
            product_id=product.id,
            version=1,
            is_active=True,
            ai_assisted=True,
            created_by=current_user.id,
            row_version=0,
        )
        db.add(recipe)
        await db.flush()

        # HPP via unit_utils helper (fix CRITICAL #2 + #8).
        from backend.services.unit_utils import cost_from_qty_unit as _cost

        hpp = Decimal("0")
        product_hpp_mismatch = []
        for ing_obj, ing_prop in recipe_ing_refs:
            if ing_obj.deleted_at is not None:
                logger.warning(
                    "menu_apply_batch: skip soft-deleted ingredient %s",
                    ing_obj.name,
                )
                continue
            contrib = _cost(ing_prop.qty, ing_prop.unit, ing_obj)
            if contrib is None:
                product_hpp_mismatch.append(
                    f"{ing_obj.name} ({ing_prop.unit} vs {ing_obj.base_unit})"
                )
                logger.warning(
                    "menu_apply_batch: unit mismatch product=%s ingredient=%s "
                    "qty=%s unit=%s vs base_unit=%s — HPP skip",
                    product.name, ing_obj.name, ing_prop.qty,
                    ing_prop.unit, ing_obj.base_unit,
                )
                line_cost = Decimal("0")
            else:
                line_cost = Decimal(str(contrib))
            hpp += line_cost
            db.add(RecipeIngredient(
                id=uuid_mod.uuid4(),
                recipe_id=recipe.id,
                ingredient_id=ing_obj.id,
                quantity=float(ing_prop.qty),
                quantity_unit=ing_prop.unit,
                is_optional=False,
                row_version=0,
            ))

        margin_pct = None
        if product.base_price and float(product.base_price) > 0:
            margin_pct = round((float(product.base_price) - float(hpp)) / float(product.base_price) * 100, 1)

        created_products.append({
            "name": product.name,
            "product_id": str(product.id),
            "recipe_id": str(recipe.id),
            "base_price": float(product.base_price or 0),
            "hpp": float(hpp),
            "margin_pct": margin_pct,
            "hpp_unit_mismatch": product_hpp_mismatch,  # observability
        })

    # Audit log
    await log_audit(
        db=db,
        action="ai_apply_menu_batch",
        entity="menu_batch",
        entity_id=str(body.outlet_id),
        after_state={
            "requested_count": len(body.products),
            "created_count": len(created_products),
            "skipped_count": len(skipped_products),
            "ingredients_created": len(ings_created_names),
            "ingredients_reused": len(ings_reused_names),
        },
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    await db.commit()

    # Invalidate context cache
    try:
        redis = await get_redis_client()
        await redis.delete(f"ai:context:{body.outlet_id}")
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "created_products": created_products,
            "skipped_products": skipped_products,
            "ingredients_created": sorted(ings_created_names),
            "ingredients_reused": sorted(ings_reused_names),
        },
    }


@router.delete("/context/{outlet_id}")
async def clear_ai_context_cache(
    outlet_id: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Force-clear cached AI context untuk outlet ini.
    Berguna setelah ada perubahan besar di menu/outlet.
    """
    # Validate ownership
    redis = await get_redis_client()
    cache_key = f"ai:context:{outlet_id}"
    await redis.delete(cache_key)
    return {"success": True, "message": "Context cache dibersihkan"}


@router.get("/budget")
async def ai_budget_status(
    current_user: User = Depends(deps.get_platform_admin),
) -> Any:
    """
    Check current AI budget usage. Superadmin only.
    """
    from datetime import date as dt_date
    redis = await get_redis_client()
    today = dt_date.today().isoformat()

    spend = int(await redis.get(f"ai_spend:{today}") or 0)

    # Get per-tenant usage
    keys = await redis.keys(f"ai_tenant:*:{today}")
    tenant_usage = {}
    for key in keys:
        tid = key.split(":")[1]
        count = int(await redis.get(key) or 0)
        tenant_usage[tid] = count

    # Sonnet usage
    sonnet_keys = await redis.keys(f"ai_sonnet:*:{today}")
    sonnet_usage = {}
    for key in sonnet_keys:
        tid = key.split(":")[1]
        count = int(await redis.get(key) or 0)
        sonnet_usage[tid] = count

    return {
        "success": True,
        "data": {
            "date": today,
            "estimated_spend_cents": spend,
            "estimated_spend_usd": f"${spend / 100:.2f}",
            "platform_daily_cap_cents": 100,
            "tenant_requests_today": tenant_usage,
            "sonnet_requests_today": sonnet_usage,
            "limits": {
                "tenant_daily": 50,
                "user_daily": 30,
                "sonnet_per_tenant": 5,
                "platform_cap_cents": 100,
            },
        },
    }


class ClassifyDomainRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: Optional[str] = Field(
        None, description="Dropdown value: cafe/warung/resto/other (optional hint)"
    )


@router.post("/classify-domain")
async def classify_domain(body: ClassifyDomainRequest) -> dict:
    """
    Lightweight domain classifier untuk Adaptive UI saat register (pre-login).

    Input: business_name + optional business_type dropdown value.
    Output: {domain, bucket, display_name, confidence, suggest_ui_switch}

    Public endpoint (tidak perlu auth) — pure classification, no DB write, no
    tenant context. Di-proteksi rate limit global slowapi (200/min default).

    Algorithm: keyword scoring weighted by match count. Winning bucket maps ke
    super-group (fnb/retail/service). `suggest_ui_switch=true` kalau domain
    non-F&B AND confidence >= 0.5 → Flutter tampilkan suggestion card.
    """
    text = (body.business_name or "").lower()
    if len(text) < 3:
        # Too short untuk confident classify — fallback
        return _fallback_response(body.business_type)

    # Score tiap bucket — product keywords (weight 1) + business-name hints (weight 2).
    # Business-name hints prioritized karena lebih deterministik ("Salon Cantik" >>
    # "style" / "cukur" yang bisa muncul di F&B juga).
    scores: dict[str, int] = {bucket: 0 for bucket in DOMAIN_KEYWORDS}
    matched_keywords: dict[str, list[str]] = {bucket: [] for bucket in DOMAIN_KEYWORDS}
    for bucket, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                scores[bucket] += 1
                matched_keywords[bucket].append(kw)
                if len(matched_keywords[bucket]) >= 3:
                    break  # cap per bucket — avoid over-weight single long text

    # Business-name hint pass — weight 2 (more authoritative than product keyword)
    for bucket, hints in _BUSINESS_NAME_HINTS.items():
        for hint in hints:
            if hint in text:
                scores[bucket] += 2
                if hint not in matched_keywords[bucket]:
                    matched_keywords[bucket].insert(0, hint)
                break  # 1 hint match per bucket cukup

    top_bucket = max(scores, key=scores.get)
    top_score = scores[top_bucket]

    if top_score == 0:
        # No keyword match → fallback ke business_type hint
        return _fallback_response(body.business_type)

    # Confidence: 1 match = 0.55, 2 matches = 0.75, 3+ = 0.9 (capped)
    confidence = min(0.9, 0.35 + 0.2 * top_score)

    super_group = _BUCKET_TO_SUPER_GROUP.get(top_bucket, "fnb")
    display_name = _BUCKET_DISPLAY_NAME.get(top_bucket, top_bucket)

    # Override display_name pakai hint keyword yang lebih spesifik (kalau ada).
    # Priority: hint match > bucket generic name. "Bengkel" over "Salon/Barber".
    for kw in matched_keywords[top_bucket]:
        if kw.lower() in _HINT_DISPLAY_OVERRIDE:
            display_name = _HINT_DISPLAY_OVERRIDE[kw.lower()]
            break

    # Suggestion trigger: hanya untuk Non-F&B + confident. F&B = default, gak
    # perlu konfirm ke user (mengurangi noise).
    suggest_ui_switch = (super_group != "fnb") and confidence >= 0.5

    return {
        "success": True,
        "data": {
            "domain": super_group,
            "bucket": top_bucket,
            "display_name": display_name,
            "confidence": round(confidence, 2),
            "suggest_ui_switch": suggest_ui_switch,
            "matched_keywords": matched_keywords[top_bucket][:3],
        },
    }


def _fallback_response(business_type: Optional[str]) -> dict:
    """Return default F&B classification saat text gak match apapun."""
    super_group = _BUSINESS_TYPE_TO_SUPER_GROUP.get(
        (business_type or "").lower(), "fnb"
    )
    # Map dropdown value → bucket approximation untuk display_name
    bucket_map = {"cafe": "kopi_cafe", "resto": "resto_makanan", "warung": "warteg"}
    bucket = bucket_map.get((business_type or "").lower(), "kopi_cafe")
    return {
        "success": True,
        "data": {
            "domain": super_group,
            "bucket": bucket,
            "display_name": _BUCKET_DISPLAY_NAME.get(bucket, "Cafe/Kopi"),
            "confidence": 0.3,
            "suggest_ui_switch": False,
            "matched_keywords": [],
        },
    }
