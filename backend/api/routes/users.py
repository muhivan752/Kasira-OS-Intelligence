import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api import deps
from backend.core.security import get_pin_hash
from backend.models.user import User
from backend.schemas.user import User as UserSchema, UserCreateWithPIN, UserUpdate
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
import json

router = APIRouter()

@router.post("/", response_model=StandardResponse[UserSchema])
async def create_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreateWithPIN,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new user.
    """
    stmt = select(User).where(User.phone == user_in.phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this phone number already exists in the system.",
        )
    
    user_data = user_in.model_dump(exclude={"pin"})
    
    if hasattr(user_in, "pin") and user_in.pin:
        user_data["pin_hash"] = get_pin_hash(user_in.pin)
        
    db_user = User(**user_data)
    db.add(db_user)
    await db.flush() # Flush to get db_user.id
    
    # Audit log
    # Convert UUIDs to strings for JSON serialization
    after_state = json.loads(user_in.model_dump_json(exclude={"pin"}))
    await log_audit(
        db=db,
        action="CREATE",
        entity="users",
        entity_id=db_user.id,
        after_state=after_state,
        user_id=current_user.id,
        tenant_id=db_user.tenant_id
    )
    
    await db.commit()
    await db.refresh(db_user)
    return StandardResponse(data=db_user, message="User created successfully")

@router.get("/me", response_model=StandardResponse[UserSchema])
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user.
    """
    return StandardResponse(data=current_user)

@router.get("/{user_id}", response_model=StandardResponse[UserSchema])
async def read_user_by_id(
    user_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user == current_user:
        return StandardResponse(data=user)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return StandardResponse(data=user)
