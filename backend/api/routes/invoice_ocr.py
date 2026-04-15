"""
Kasira Invoice OCR Routes — Scan purchase invoices to extract ingredient data.

POST /invoice-ocr/scan        — upload invoice photo, get extracted items
POST /invoice-ocr/apply       — apply matched prices to ingredients
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.brand import Brand
from backend.schemas.response import StandardResponse
from backend.services import invoice_ocr_service

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_SIZE_MB = 10
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _get_brand_id(tenant_id: UUID, db: AsyncSession) -> UUID:
    brand = (await db.execute(
        select(Brand).where(Brand.tenant_id == tenant_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand.id


# ─── Scan ───────────────────────────────────────────────────────────────────

@router.post("/scan")
async def scan_invoice(
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

    brand_id = await _get_brand_id(current_user.tenant_id, db)

    # Step 1: Extract data via Claude Vision
    try:
        extracted = await invoice_ocr_service.extract_invoice_data(content, file.content_type)
    except RuntimeError as e:
        raise HTTPException(503, detail=str(e))

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
    items: List[ApplyItem]


@router.post("/apply")
async def apply_prices(
    request: ApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Apply scanned invoice prices to matched ingredients.
    Only updates ingredients that have a matched_ingredient_id.
    """
    brand_id = await _get_brand_id(current_user.tenant_id, db)

    result = await invoice_ocr_service.apply_invoice_prices(
        [item.model_dump() for item in request.items],
        brand_id,
        db,
    )

    return StandardResponse(
        data=result,
        message=f"Updated {result['updated']} ingredient prices",
    )
