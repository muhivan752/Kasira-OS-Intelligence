import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api import deps
from backend.core.security import get_pin_hash
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.schemas.user import User as UserSchema, UserCreateWithPIN, UserUpdate
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from sqlalchemy import func
import json

# Batas kasir per tier (tidak termasuk owner)
CASHIER_LIMITS = {
    "starter": 1,
    "pro": 5,
    "business": 999,
    "enterprise": 999,
}

router = APIRouter()


class CashierCreate(BaseModel):
    name: str
    phone: str
    pin: str
    outlet_id: Optional[str] = None


class StatusUpdate(BaseModel):
    is_active: bool


class PinUpdate(BaseModel):
    pin: str


@router.get("/", response_model=StandardResponse[List[UserSchema]])
async def list_cashiers(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List all cashiers (non-superuser) for current tenant."""
    stmt = (
        select(User)
        .where(
            User.tenant_id == current_user.tenant_id,
            User.is_superuser == False,
            User.deleted_at == None,
        )
        .order_by(User.full_name)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return StandardResponse(data=users)


@router.post("/cashier", response_model=StandardResponse[UserSchema])
async def create_cashier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    cashier_in: CashierCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a new cashier for the current tenant. Owner only."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Hanya owner yang bisa menambah kasir")

    # Cek limit kasir per tier
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id, Tenant.deleted_at == None)
    )
    tenant = tenant_result.scalar_one_or_none()
    tier = tenant.subscription_tier.value if hasattr(tenant.subscription_tier, 'value') else str(tenant.subscription_tier or 'starter')
    max_cashiers = CASHIER_LIMITS.get(tier, 1)

    active_cashier_count = (await db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == current_user.tenant_id,
            User.is_superuser == False,
            User.is_active == True,
            User.deleted_at == None,
        )
    )).scalar() or 0

    if active_cashier_count >= max_cashiers:
        raise HTTPException(
            status_code=403,
            detail=f"Batas kasir untuk paket {tier.capitalize()} adalah {max_cashiers}. Upgrade untuk menambah kasir.",
        )

    # Validate phone format
    if not cashier_in.phone.startswith("628"):
        raise HTTPException(status_code=422, detail="Nomor HP harus diawali dengan 628")

    if len(cashier_in.pin) != 6 or not cashier_in.pin.isdigit():
        raise HTTPException(status_code=422, detail="PIN harus 6 digit angka")

    # Check duplicate phone
    stmt = select(User).where(User.phone == cashier_in.phone, User.deleted_at == None)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Nomor HP sudah terdaftar")

    db_user = User(
        full_name=cashier_in.name,
        phone=cashier_in.phone,
        pin_hash=get_pin_hash(cashier_in.pin),
        tenant_id=current_user.tenant_id,
        is_active=True,
        is_superuser=False,
    )
    db.add(db_user)
    await db.flush()

    await log_audit(
        db=db,
        action="CREATE",
        entity="users",
        entity_id=db_user.id,
        after_state={"full_name": cashier_in.name, "phone": cashier_in.phone, "role": "cashier"},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    await db.commit()
    await db.refresh(db_user)
    return StandardResponse(data=db_user, message="Kasir berhasil ditambahkan")


@router.put("/{user_id}/status", response_model=StandardResponse[UserSchema])
async def update_cashier_status(
    user_id: uuid.UUID,
    status_in: StatusUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Toggle active status of a cashier."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Hanya owner yang bisa mengubah status kasir")

    stmt = select(User).where(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id,
        User.deleted_at == None,
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kasir tidak ditemukan")

    before = {"is_active": user.is_active}
    user.is_active = status_in.is_active

    await log_audit(
        db=db,
        action="UPDATE",
        entity="users",
        entity_id=user.id,
        before_state=before,
        after_state={"is_active": status_in.is_active},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    await db.commit()
    await db.refresh(user)
    return StandardResponse(data=user, message="Status kasir diperbarui")


@router.put("/{user_id}/pin", response_model=StandardResponse[UserSchema])
async def reset_cashier_pin(
    user_id: uuid.UUID,
    pin_in: PinUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Reset PIN for a cashier."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Hanya owner yang bisa reset PIN kasir")

    if len(pin_in.pin) != 6 or not pin_in.pin.isdigit():
        raise HTTPException(status_code=422, detail="PIN harus 6 digit angka")

    stmt = select(User).where(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id,
        User.deleted_at == None,
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kasir tidak ditemukan")

    user.pin_hash = get_pin_hash(pin_in.pin)

    await log_audit(
        db=db,
        action="UPDATE",
        entity="users",
        entity_id=user.id,
        before_state={"pin_hash": "redacted"},
        after_state={"pin_hash": "reset"},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    await db.commit()
    await db.refresh(user)
    return StandardResponse(data=user, message="PIN kasir berhasil direset")


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

@router.get("/me", response_model=StandardResponse)
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Get current user with tenant tier.
    """
    from backend.models.tenant import Tenant
    tier = "starter"
    if current_user.tenant_id:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )).scalar_one_or_none()
        if tenant:
            raw_tier = getattr(tenant, "subscription_tier", "starter")
            tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier or "starter")

    sub_status = "active"
    if current_user.tenant_id:
        if tenant:
            raw_status = getattr(tenant, "subscription_status", "active")
            sub_status = raw_status.value if hasattr(raw_status, 'value') else str(raw_status or "active")

    user_data = UserSchema.model_validate(current_user).model_dump()
    user_data["subscription_tier"] = tier
    user_data["subscription_status"] = sub_status
    return StandardResponse(data=user_data)

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
