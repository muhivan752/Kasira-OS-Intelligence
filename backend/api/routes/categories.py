from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.category import Category
from backend.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter()

@router.post("/", response_model=StandardResponse[CategoryResponse])
async def create_category(
    request: Request,
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create new category.
    """
    category = Category(
        brand_id=category_in.brand_id,
        name=category_in.name,
        is_active=category_in.is_active
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    # Audit log
    await log_audit(
        db=db,
        action="CREATE",
        entity="category",
        entity_id=category.id,
        after_state={"name": category.name, "brand_id": str(category.brand_id)},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data=CategoryResponse.model_validate(category),
        request_id=request.state.request_id,
        message="Category created successfully"
    )

@router.get("/", response_model=StandardResponse[List[CategoryResponse]])
async def read_categories(
    request: Request,
    brand_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve categories.
    """
    query = select(Category).where(
        Category.brand_id == brand_id,
        Category.deleted_at.is_(None)
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return StandardResponse(
        success=True,
        data=[CategoryResponse.model_validate(c) for c in categories],
        request_id=request.state.request_id
    )

@router.get("/{category_id}", response_model=StandardResponse[CategoryResponse])
async def read_category(
    request: Request,
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get category by ID.
    """
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Category not found")
        
    return StandardResponse(
        success=True,
        data=CategoryResponse.model_validate(category),
        request_id=request.state.request_id
    )

@router.put("/{category_id}", response_model=StandardResponse[CategoryResponse])
async def update_category(
    request: Request,
    category_id: UUID,
    category_in: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a category.
    """
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Category not found")
        
    before_state = {"name": category.name, "is_active": category.is_active}
    
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
        
    await db.commit()
    await db.refresh(category)
    
    # Audit log
    await log_audit(
        db=db,
        action="UPDATE",
        entity="category",
        entity_id=category.id,
        before_state=before_state,
        after_state={"name": category.name, "is_active": category.is_active},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data=CategoryResponse.model_validate(category),
        request_id=request.state.request_id,
        message="Category updated successfully"
    )

@router.delete("/{category_id}", response_model=StandardResponse[dict])
async def delete_category(
    request: Request,
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete a category (soft delete).
    """
    from datetime import datetime, timezone
    
    category = await db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Category not found")
        
    category.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    
    # Audit log
    await log_audit(
        db=db,
        action="DELETE",
        entity="category",
        entity_id=category.id,
        before_state={"name": category.name},
        after_state={"deleted": True},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data={"id": str(category_id)},
        request_id=request.state.request_id,
        message="Category deleted successfully"
    )
