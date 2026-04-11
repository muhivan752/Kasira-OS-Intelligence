import uuid
from typing import Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.api import deps
from backend.models.outlet import Outlet
from backend.schemas.outlet import Outlet as OutletSchema, OutletCreate, OutletUpdate, OutletPaymentSetup, OutletPaymentSetupOwn, OutletPaymentStatus, OutletStockModeUpdate
from backend.schemas.response import StandardResponse, ResponseMeta
from backend.services.audit import log_audit
import json

router = APIRouter()

@router.get("/", response_model=StandardResponse[List[OutletSchema]])
async def read_outlets(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve outlets.
    """
    stmt = select(Outlet).where(
        Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit)
        
    result = await db.execute(stmt)
    outlets = result.scalars().all()
    
    meta = ResponseMeta(page=(skip // limit) + 1, per_page=limit, total=len(outlets))
    return StandardResponse(data=outlets, meta=meta)

@router.post("/", response_model=StandardResponse[OutletSchema])
async def create_outlet(
    *,
    db: AsyncSession = Depends(deps.get_db),
    outlet_in: OutletCreate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new outlet.
    """
    db_outlet = Outlet(**outlet_in.model_dump())
    db.add(db_outlet)
    await db.flush()
    
    after_state = json.loads(outlet_in.model_dump_json())
    await log_audit(
        db=db,
        action="CREATE",
        entity="outlets",
        entity_id=db_outlet.id,
        after_state=after_state,
        user_id=current_user.id,
        tenant_id=db_outlet.tenant_id
    )
    
    await db.commit()
    await db.refresh(db_outlet)
    return StandardResponse(data=db_outlet, message="Outlet created successfully")

@router.get("/{outlet_id}", response_model=StandardResponse[OutletSchema])
async def read_outlet(
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Get outlet by ID.
    """
    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    return StandardResponse(data=outlet)

@router.put("/{outlet_id}", response_model=StandardResponse[OutletSchema])
async def update_outlet(
    request: Request,
    outlet_id: uuid.UUID,
    outlet_in: OutletUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Update outlet info (name, phone, address, is_open, opening_hours).
    """
    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    before_state = {
        "name": outlet.name, "phone": outlet.phone,
        "address": outlet.address, "is_open": outlet.is_open,
    }

    update_data = outlet_in.model_dump(exclude_unset=True)
    update_stmt = (
        update(Outlet)
        .where(Outlet.id == outlet_id)
        .values(**update_data, row_version=Outlet.row_version + 1,
                updated_at=datetime.now(timezone.utc))
    )
    await db.execute(update_stmt)

    await log_audit(
        db=db,
        action="UPDATE",
        entity="outlets",
        entity_id=outlet_id,
        before_state=before_state,
        after_state=update_data,
        user_id=current_user.id,
        tenant_id=outlet.tenant_id,
    )
    await db.commit()

    # Invalidate storefront cache
    from backend.api.routes.connect import invalidate_storefront_cache
    await invalidate_storefront_cache(outlet_id, db)

    await db.refresh(outlet)
    return StandardResponse(
        success=True,
        data=outlet,
        request_id=request.state.request_id,
        message="Outlet berhasil diperbarui"
    )

@router.post("/{outlet_id}/payment-setup", response_model=StandardResponse[OutletPaymentStatus])
async def setup_payment(
    request: Request,
    outlet_id: uuid.UUID,
    setup_in: OutletPaymentSetup,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Setup payment gateway for an outlet.
    """
    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()

    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    now = datetime.now(timezone.utc)
    
    update_stmt = (
        update(Outlet)
        .where(Outlet.id == outlet_id)
        .values(
            xendit_business_id=setup_in.xendit_business_id,
            xendit_connected_at=now,
            row_version=Outlet.row_version + 1
        )
    )
    await db.execute(update_stmt)

    # Golden Rule #2: Setiap WRITE endpoint WAJIB tulis audit log
    await log_audit(
        db=db,
        action="UPDATE",
        entity="outlets",
        entity_id=outlet_id,
        after_state={"xendit_business_id": setup_in.xendit_business_id, "xendit_connected_at": now.isoformat()},
        user_id=current_user.id,
        tenant_id=outlet.tenant_id,
    )

    await db.commit()
    
    status_data = OutletPaymentStatus(
        is_connected=True,
        xendit_business_id=setup_in.xendit_business_id,
        connected_at=now
    )
    
    return StandardResponse(
        success=True,
        data=status_data,
        request_id=request.state.request_id,
        message="Payment gateway berhasil dikonfigurasi"
    )

@router.post("/{outlet_id}/payment-setup/own-key", response_model=StandardResponse[OutletPaymentStatus])
async def setup_payment_own_key(
    request: Request,
    outlet_id: uuid.UUID,
    setup_in: OutletPaymentSetupOwn,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """Simpan Xendit secret key milik merchant sendiri (Phase 1 pilot)."""
    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    )
    outlet = (await db.execute(stmt)).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    now = datetime.now(timezone.utc)
    await db.execute(
        update(Outlet)
        .where(Outlet.id == outlet_id)
        .values(xendit_api_key=setup_in.xendit_api_key, xendit_connected_at=now, row_version=Outlet.row_version + 1)
    )
    await log_audit(db=db, action="UPDATE", entity="outlets", entity_id=outlet_id,
                    after_state={"xendit_mode": "own_key", "xendit_connected_at": now.isoformat()},
                    user_id=current_user.id, tenant_id=outlet.tenant_id)
    await db.commit()

    return StandardResponse(
        success=True,
        data=OutletPaymentStatus(is_connected=True, mode="own_key", connected_at=now),
        request_id=request.state.request_id,
        message="Xendit API key berhasil disimpan"
    )

@router.delete("/{outlet_id}/payment-setup/own-key", response_model=StandardResponse[dict])
async def remove_payment_own_key(
    request: Request,
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """Hapus Xendit secret key merchant."""
    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    )
    outlet = (await db.execute(stmt)).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    await db.execute(
        update(Outlet).where(Outlet.id == outlet_id)
        .values(xendit_api_key=None, row_version=Outlet.row_version + 1)
    )
    await log_audit(db=db, action="UPDATE", entity="outlets", entity_id=outlet_id,
                    after_state={"xendit_mode": "removed_own_key"},
                    user_id=current_user.id, tenant_id=outlet.tenant_id)
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Xendit API key dihapus")

@router.get("/{outlet_id}/payment-status", response_model=StandardResponse[OutletPaymentStatus])
async def get_payment_status(
    request: Request,
    outlet_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    Get payment gateway status for an outlet.
    """
    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()

    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    has_own_key = outlet.xendit_api_key is not None
    has_platform = outlet.xendit_business_id is not None
    is_connected = has_own_key or has_platform
    mode = "xenplatform" if has_platform else ("own_key" if has_own_key else "none")

    status_data = OutletPaymentStatus(
        is_connected=is_connected,
        mode=mode,
        xendit_business_id=outlet.xendit_business_id,
        connected_at=outlet.xendit_connected_at
    )
    
    return StandardResponse(
        success=True,
        data=status_data,
        request_id=request.state.request_id
    )


@router.put("/{outlet_id}/stock-mode", response_model=StandardResponse[OutletSchema])
async def update_stock_mode(
    request: Request,
    outlet_id: uuid.UUID,
    mode_in: OutletStockModeUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """Switch stock mode between 'simple' and 'recipe' (Pro only)."""
    from backend.models.tenant import Tenant
    from backend.api.deps import PRO_TIERS
    tenant = (await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))).scalar_one_or_none()
    raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter"
    tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)
    if tier.lower() not in PRO_TIERS:
        raise HTTPException(status_code=403, detail="Fitur ini hanya tersedia untuk paket Pro")

    stmt = select(Outlet).where(
        Outlet.id == outlet_id, Outlet.deleted_at == None,
        Outlet.tenant_id == current_user.tenant_id,
    )
    outlet = (await db.execute(stmt)).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    if mode_in.stock_mode not in ("simple", "recipe"):
        raise HTTPException(status_code=400, detail="Stock mode harus 'simple' atau 'recipe'")

    # If switching to recipe, validate all stock-enabled products have active recipes
    if mode_in.stock_mode == "recipe":
        from backend.models.product import Product
        from backend.models.recipe import Recipe

        products = (await db.execute(
            select(Product).where(
                Product.brand_id == outlet.brand_id,
                Product.stock_enabled == True,
                Product.deleted_at.is_(None),
            )
        )).scalars().all()

        product_ids = [p.id for p in products]
        if product_ids:
            recipes = (await db.execute(
                select(Recipe.product_id).where(
                    Recipe.product_id.in_(product_ids),
                    Recipe.is_active == True,
                    Recipe.deleted_at.is_(None),
                )
            )).scalars().all()
            recipe_product_ids = set(recipes)
            missing = [p.name for p in products if p.id not in recipe_product_ids]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produk berikut belum punya resep: {', '.join(missing[:5])}. Tambahkan resep dulu sebelum beralih ke mode Resep."
                )

    before = outlet.stock_mode
    await db.execute(
        update(Outlet).where(Outlet.id == outlet_id)
        .values(stock_mode=mode_in.stock_mode, row_version=Outlet.row_version + 1, updated_at=datetime.now(timezone.utc))
    )
    await log_audit(
        db=db, action="UPDATE", entity="outlets", entity_id=outlet_id,
        before_state={"stock_mode": before}, after_state={"stock_mode": mode_in.stock_mode},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(outlet)

    return StandardResponse(
        success=True, data=outlet,
        message=f"Mode stok diubah ke '{mode_in.stock_mode}'",
        request_id=request.state.request_id,
    )
