"""
Kasira Invoice OCR Routes — Scan purchase invoices to extract ingredient data.

POST /invoice-ocr/scan        — upload invoice photo, get extracted items
POST /invoice-ocr/apply       — apply matched prices to ingredients
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.brand import Brand
from backend.models.outlet import Outlet
from backend.schemas.response import StandardResponse
from backend.services import invoice_ocr_service

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_SIZE_MB = 10
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_brand_id(tenant_id: UUID, db: AsyncSession, outlet_id: Optional[UUID] = None) -> UUID:
    if outlet_id:
        outlet = await db.scalar(select(Outlet).where(Outlet.id == outlet_id, Outlet.tenant_id == tenant_id,
                                                      Outlet.deleted_at.is_(None)))
        if not outlet or not outlet.brand_id:
            raise HTTPException(404, detail='Brand outlet tidak ditemukan')
        return outlet.brand_id
    brand = (await db.execute(
        select(Brand).where(Brand.tenant_id == tenant_id, Brand.deleted_at.is_(None))
    )).scalars().all()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if len(brand) > 1:
        raise HTTPException(400, detail='Pilih outlet untuk membaca nota')
    return brand[0].id


# ─── Scan ───────────────────────────────────────────────────────────────────

@router.post("/scan")
async def scan_invoice(
    request: Request,
    outlet_id: Optional[UUID] = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Upload invoice/receipt photo. Returns extracted items with ingredient matching.
    """
    # Validate file
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, detail=f"Format tidak didukung. Gunakan: JPG, PNG, atau WebP")

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, detail=f"Ukuran file maksimal {MAX_SIZE_MB}MB")

    brand_id = await _get_brand_id(current_user.tenant_id, db, outlet_id)
    from backend.services.ai_access import fresh
    access = request.state.access
    user_id, tenant_id = current_user.id, current_user.tenant_id
    async def guard():
        from sqlalchemy import text
        await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), {"tenant": str(tenant_id)})
        if outlet_id:
            await fresh(db, user_id, tenant_id, outlet_id,
                grants=("ai.chat", "purchasing.manage", "supplier.price.view"), expected=access.version,
                claims=request.state.auth_claims, token=request.state.auth_token)
    await guard()

    # Budget check — OCR costs ~3 cents per scan (image + extraction)
    try:
        from backend.services.redis import get_redis_client
        from datetime import date as dt_date
        redis = await get_redis_client()
        today = dt_date.today().isoformat()
        spend_key = f"ai_spend:{today}"
        current_spend = int(await redis.get(spend_key) or 0)
        if current_spend >= 50:  # $0.50/day cap
            raise HTTPException(429, detail="Budget AI harian sudah tercapai. Coba lagi besok.")
        await redis.incrby(spend_key, 3)  # OCR ~3 cents
        await redis.expire(spend_key, 86400)
    except HTTPException:
        raise
    except Exception:
        pass

    # Step 1: Extract data via Claude Vision
    await db.commit()
    try:
        extracted = await invoice_ocr_service.extract_invoice_data(content, file.content_type)
    except RuntimeError as e:
        raise HTTPException(503, detail=str(e))
    await guard()

    if "error" in extracted:
        return StandardResponse(
            success=False,
            data=extracted,
            message=extracted.get("error", "OCR gagal"),
        )

    # Step 2: Match items to existing ingredients
    items = extracted.get("items", [])
    matched = await invoice_ocr_service.match_ingredients(items, brand_id, db)

    return StandardResponse(
        data={
            "supplier_name": extracted.get("supplier_name"),
            "invoice_date": extracted.get("invoice_date"),
            "invoice_number": extracted.get("invoice_number"),
            "grand_total": extracted.get("grand_total"),
            "notes": extracted.get("notes"),
            "items": matched,
            "summary": {
                "total_items": len(matched),
                "exact_match": sum(1 for i in matched if i["match_type"] == "exact"),
                "partial_match": sum(1 for i in matched if i["match_type"] == "partial"),
                "new_items": sum(1 for i in matched if i["match_type"] == "new"),
            },
        },
        message=f"Berhasil scan {len(matched)} item dari nota",
    )


# ─── Apply Prices ──────────────────────────────────────────────────────────

class ApplyItem(BaseModel):
    name: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    matched_ingredient_id: Optional[str] = None

class ApplyRequest(BaseModel):
    outlet_id: UUID | None = None
    items: List[ApplyItem]


@router.post("/apply")
async def apply_prices(
    body: ApplyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Apply scanned invoice prices to matched ingredients.
    Only updates ingredients that have a matched_ingredient_id.
    """
    brand_id = await _get_brand_id(current_user.tenant_id, db, body.outlet_id)
    if body.outlet_id:
        from backend.services.ai_access import fresh
        await fresh(db, current_user.id, current_user.tenant_id, body.outlet_id,
            grants=("ai.chat", "hpp.view", "supplier.price.view", "hpp.manage", "hpp.approve"),
            expected=request.state.access.version, claims=request.state.auth_claims, token=request.state.auth_token, lock=True)
    from backend.models.ingredient import Ingredient
    for item in body.items:
        if item.matched_ingredient_id:
            from backend.services.pos_access import as_id
            if not await db.scalar(select(Ingredient.id).where(Ingredient.id == as_id(item.matched_ingredient_id),
                Ingredient.brand_id == brand_id, Ingredient.deleted_at.is_(None))):
                raise HTTPException(404, "Bahan tidak tersedia dalam brand outlet ini")

    result = await invoice_ocr_service.apply_invoice_prices(
        [item.model_dump() for item in body.items],
        brand_id,
        db,
    )

    return StandardResponse(
        data=result,
        message=f"Updated {result['updated']} ingredient prices",
    )
