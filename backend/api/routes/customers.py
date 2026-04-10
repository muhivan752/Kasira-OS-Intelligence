from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.customer import Customer
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter()


class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=StandardResponse[List[CustomerResponse]])
async def list_customers(
    request: Request,
    outlet_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = select(Customer).where(
        Customer.tenant_id == current_user.tenant_id,
        Customer.deleted_at.is_(None),
    )
    if search:
        from sqlalchemy import or_
        query = query.where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(Customer.name).offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    return StandardResponse(
        success=True,
        data=[CustomerResponse.model_validate(c) for c in customers],
        request_id=request.state.request_id,
    )


@router.post("/", response_model=StandardResponse[CustomerResponse])
async def create_customer(
    request: Request,
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # Cek duplikat phone
    if customer_in.phone:
        dup_stmt = select(Customer).where(
            Customer.tenant_id == current_user.tenant_id,
            Customer.phone == customer_in.phone,
            Customer.deleted_at.is_(None),
        )
        if (await db.execute(dup_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Pelanggan dengan nomor HP ini sudah terdaftar")

    customer = Customer(
        tenant_id=current_user.tenant_id,
        name=customer_in.name,
        phone=customer_in.phone,
        email=customer_in.email,
        phone_hmac='',
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    await log_audit(
        db=db,
        action="CREATE",
        entity="customer",
        entity_id=customer.id,
        after_state={"name": customer.name, "phone": customer.phone},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        success=True,
        data=CustomerResponse.model_validate(customer),
        request_id=request.state.request_id,
        message="Pelanggan berhasil ditambahkan",
    )
