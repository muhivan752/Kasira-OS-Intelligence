from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.product import Product
from backend.models.tenant import Tenant
from backend.models.brand import Brand
from backend.models.outlet import Outlet
from backend.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from backend.schemas.stock import ProductRestock
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.stock_service import restock_product as svc_restock
from backend.api.deps import validate_brand_ownership, validate_product_ownership

router = APIRouter()

@router.post("/{product_id}/restock", response_model=StandardResponse[ProductResponse])
async def restock_product(
    request: Request,
    product_id: UUID,
    restock_in: ProductRestock,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Restock produk saat terima barang (Starter: transaction-first, Rule #19).
    Menulis stock.restock event ke event store sebelum update cache.
    """
    product = await validate_product_ownership(db, product_id, current_user.tenant_id)
    if not product.stock_enabled:
        raise HTTPException(status_code=400, detail="Tracking stok tidak aktif untuk produk ini")

    tenant_stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()
    tier = getattr(getattr(tenant, "subscription_tier", None), "value", "starter")

    before_state = {"stock_qty": product.stock_qty, "is_active": product.is_active}

    updated_product = await svc_restock(
        db,
        product=product,
        quantity=restock_in.quantity,
        outlet_id=restock_in.outlet_id,
        user_id=current_user.id,
        notes=restock_in.notes,
        tier=tier,
    )

    await log_audit(
        db=db,
        action="RESTOCK",
        entity="product",
        entity_id=updated_product.id,
        before_state=before_state,
        after_state={
            "stock_qty": updated_product.stock_qty,
            "is_active": updated_product.is_active,
            "restock_amount": restock_in.quantity,
            "notes": restock_in.notes,
        },
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()

    # Re-fetch with category eagerly loaded
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    )
    updated_product = result.scalar_one()

    return StandardResponse(
        success=True,
        data=ProductResponse.model_validate(updated_product),
        request_id=request.state.request_id,
        message=f"Berhasil restock {restock_in.quantity} item",
    )

@router.post("/", response_model=StandardResponse[ProductResponse])
async def create_product(
    request: Request,
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create new product.
    """
    await validate_brand_ownership(db, product_in.brand_id, current_user.tenant_id)
    product = Product(
        brand_id=product_in.brand_id,
        category_id=product_in.category_id,
        name=product_in.name,
        description=product_in.description,
        base_price=product_in.base_price,
        image_url=product_in.image_url,
        is_active=product_in.is_active,
        stock_enabled=product_in.stock_enabled,
        stock_qty=product_in.stock_qty,
        stock_low_threshold=product_in.stock_low_threshold,
        stock_auto_hide=product_in.stock_auto_hide,
        sku=product_in.sku,
        barcode=product_in.barcode,
        is_subscription=product_in.is_subscription
    )
    db.add(product)
    await db.flush()

    # Audit log
    await log_audit(
        db=db,
        action="CREATE",
        entity="product",
        entity_id=product.id,
        after_state={"name": product.name, "base_price": float(product.base_price), "sku": product.sku},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    # Re-fetch with category eagerly loaded (avoid MissingGreenlet on ProductResponse.category_name)
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).where(Product.id == product.id)
    )
    product = result.scalar_one()

    return StandardResponse(
        success=True,
        data=ProductResponse.model_validate(product),
        request_id=request.state.request_id,
        message="Product created successfully"
    )

@router.get("/low-stock", response_model=StandardResponse[List[ProductResponse]])
async def read_low_stock_products(
    request: Request,
    brand_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Produk dengan stock_enabled=true dan stock_qty <= stock_low_threshold.
    """
    if brand_id is None:
        brand_row = (await db.execute(
            select(Brand).where(Brand.tenant_id == current_user.tenant_id, Brand.deleted_at.is_(None))
        )).scalars().first()
        if not brand_row:
            return StandardResponse(success=True, data=[], request_id=request.state.request_id)
        brand_id = brand_row.id

    from sqlalchemy import column as col
    query = (
        select(Product)
        .options(selectinload(Product.category))
        .where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
            Product.stock_enabled == True,
            Product.stock_qty <= Product.stock_low_threshold,
        )
        .order_by(Product.stock_qty.asc())
    )
    result = await db.execute(query)
    products = result.scalars().all()

    return StandardResponse(
        success=True,
        data=[ProductResponse.model_validate(p) for p in products],
        request_id=request.state.request_id
    )


@router.get("/", response_model=StandardResponse[List[ProductResponse]])
async def read_products(
    request: Request,
    brand_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve products. brand_id opsional — jika tidak dikirim, infer dari tenant user (Flutter POS).
    """
    # Jika brand_id tidak dikirim (Flutter POS), cari brand pertama milik tenant
    if brand_id is None:
        brand_row = (await db.execute(
            select(Brand).where(Brand.tenant_id == current_user.tenant_id, Brand.deleted_at.is_(None))
        )).scalars().first()
        if not brand_row:
            return StandardResponse(success=True, data=[], request_id=request.state.request_id)
        brand_id = brand_row.id
    else:
        await validate_brand_ownership(db, brand_id, current_user.tenant_id)

    query = select(Product).where(
        Product.brand_id == brand_id,
        Product.deleted_at.is_(None)
    )
    
    if category_id:
        query = query.where(Product.category_id == category_id)

    query = query.options(selectinload(Product.category)).offset(skip).limit(limit)

    result = await db.execute(query)
    products = result.scalars().all()
    
    return StandardResponse(
        success=True,
        data=[ProductResponse.model_validate(p) for p in products],
        request_id=request.state.request_id
    )

@router.get("/best-sellers", response_model=StandardResponse[List[ProductResponse]])
async def read_best_sellers(
    request: Request,
    brand_id: Optional[UUID] = None,
    outlet_id: Optional[UUID] = None,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Top products by sold_total."""
    if brand_id is None:
        brand_row = (await db.execute(
            select(Brand).where(Brand.tenant_id == current_user.tenant_id, Brand.deleted_at.is_(None))
        )).scalars().first()
        if not brand_row:
            return StandardResponse(success=True, data=[], request_id=request.state.request_id)
        brand_id = brand_row.id

    query = (
        select(Product)
        .options(selectinload(Product.category))
        .where(
            Product.brand_id == brand_id,
            Product.deleted_at.is_(None),
            Product.sold_total > 0,
        )
        .order_by(Product.sold_total.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    return StandardResponse(
        success=True,
        data=[ProductResponse.model_validate(p) for p in products],
        request_id=request.state.request_id
    )

@router.get("/{product_id}", response_model=StandardResponse[ProductResponse])
async def read_product(
    request: Request,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get product by ID.
    """
    product = await validate_product_ownership(db, product_id, current_user.tenant_id)

    return StandardResponse(
        success=True,
        data=ProductResponse.model_validate(product),
        request_id=request.state.request_id
    )

@router.put("/{product_id}", response_model=StandardResponse[ProductResponse])
async def update_product(
    request: Request,
    product_id: UUID,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a product with optimistic locking.
    """
    # 1. Fetch current product with tenant validation
    product = await validate_product_ownership(db, product_id, current_user.tenant_id)
        
    # 2. Check row_version for optimistic locking
    if product.row_version != product_in.row_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product has been modified by another user. Please refresh and try again."
        )
        
    before_state = {
        "name": product.name, 
        "base_price": float(product.base_price),
        "stock_qty": product.stock_qty,
        "is_active": product.is_active
    }
    
    # 3. Perform update with row_version increment
    update_data = product_in.model_dump(exclude_unset=True, exclude={"row_version"})
    
    # If stock hits 0 and auto_hide is enabled, set is_active to False
    if "stock_qty" in update_data:
        new_stock = update_data["stock_qty"]
        auto_hide = update_data.get("stock_auto_hide", product.stock_auto_hide)
        if new_stock <= 0 and auto_hide:
            update_data["is_active"] = False
            
    # Execute update query with WHERE clause for row_version
    stmt = (
        update(Product)
        .where(Product.id == product_id, Product.row_version == product_in.row_version)
        .values(**update_data, row_version=Product.row_version + 1, updated_at=datetime.now(timezone.utc))
        .returning(Product)
    )
    
    result = await db.execute(stmt)
    updated_product = result.scalar_one_or_none()
    
    if not updated_product:
        # This means the row_version changed between our GET and UPDATE
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrent update detected. Please try again."
        )
        
    # Audit log
    await log_audit(
        db=db,
        action="UPDATE",
        entity="product",
        entity_id=updated_product.id,
        before_state=before_state,
        after_state={
            "name": updated_product.name,
            "base_price": float(updated_product.base_price),
            "stock_qty": updated_product.stock_qty,
            "is_active": updated_product.is_active
        },
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()

    # Re-fetch with category eagerly loaded
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    )
    updated_product = result.scalar_one()

    return StandardResponse(
        success=True,
        data=ProductResponse.model_validate(updated_product),
        request_id=request.state.request_id,
        message="Product updated successfully"
    )

@router.delete("/{product_id}", response_model=StandardResponse[dict])
async def delete_product(
    request: Request,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete a product (soft delete).
    """
    product = await validate_product_ownership(db, product_id, current_user.tenant_id)
        
    product.deleted_at = datetime.now(timezone.utc)

    # Audit log
    await log_audit(
        db=db,
        action="DELETE",
        entity="product",
        entity_id=product.id,
        before_state={"name": product.name, "sku": product.sku},
        after_state={"deleted": True},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()

    return StandardResponse(
        success=True,
        data={"id": str(product_id)},
        request_id=request.state.request_id,
        message="Product deleted successfully"
    )
