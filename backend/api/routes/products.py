from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.product import Product
from backend.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from backend.schemas.stock import ProductRestock
from backend.schemas.response import StandardResponse
from backend.models.audit_log import log_audit

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
    Restock a product manually (Tier Starter).
    """
    from datetime import datetime, timezone
    
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if not product.stock_enabled:
        raise HTTPException(status_code=400, detail="Stock tracking is not enabled for this product")
        
    before_state = {
        "stock_qty": product.stock_qty,
        "is_active": product.is_active
    }
    
    # Increment stock
    new_stock = product.stock_qty + restock_in.quantity
    
    # If it was auto-hidden because of 0 stock, we make it active again
    is_active = product.is_active
    if product.stock_auto_hide and product.stock_qty <= 0 and new_stock > 0:
        is_active = True
        
    stmt = (
        update(Product)
        .where(Product.id == product_id, Product.row_version == product.row_version)
        .values(
            stock_qty=new_stock,
            is_active=is_active,
            last_restock_at=datetime.now(timezone.utc),
            row_version=Product.row_version + 1,
            updated_at=datetime.now(timezone.utc)
        )
        .returning(Product)
    )
    
    result = await db.execute(stmt)
    updated_product = result.scalar_one_or_none()
    
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrent update detected. Please try again."
        )
        
    await db.commit()
    
    # Audit log
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
            "notes": restock_in.notes
        },
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data=ProductResponse.model_validate(updated_product),
        request_id=request.state.request_id,
        message=f"Successfully restocked {restock_in.quantity} items"
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
    await db.commit()
    await db.refresh(product)
    
    # Audit log
    await log_audit(
        db=db,
        action="CREATE",
        entity="product",
        entity_id=product.id,
        after_state={"name": product.name, "base_price": float(product.base_price), "sku": product.sku},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data=ProductResponse.model_validate(product),
        request_id=request.state.request_id,
        message="Product created successfully"
    )

@router.get("/", response_model=StandardResponse[List[ProductResponse]])
async def read_products(
    request: Request,
    brand_id: UUID,
    category_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve products.
    """
    query = select(Product).where(
        Product.brand_id == brand_id,
        Product.deleted_at.is_(None)
    )
    
    if category_id:
        query = query.where(Product.category_id == category_id)
        
    query = query.offset(skip).limit(limit)
    
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
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
        
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
    # 1. Fetch current product
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
        
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
        
    await db.commit()
    
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
        request_id=request.state.request_id
    )
    
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
    from datetime import datetime, timezone
    
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
        
    product.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    
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
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data={"id": str(product_id)},
        request_id=request.state.request_id,
        message="Product deleted successfully"
    )
