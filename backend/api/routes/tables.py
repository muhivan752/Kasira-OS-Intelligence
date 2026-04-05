from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.api import deps
from backend.models.user import User
from backend.models.reservation import Table
from backend.schemas.response import StandardResponse
from pydantic import BaseModel

router = APIRouter()

class TableResponse(BaseModel):
    id: UUID
    name: str
    capacity: int
    status: str

    class Config:
        from_attributes = True

@router.get("/", response_model=StandardResponse[List[TableResponse]])
async def get_tables(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(
        select(Table).where(
            Table.outlet_id == outlet_id,
            Table.deleted_at.is_(None),
        ).order_by(Table.name)
    )
    tables = result.scalars().all()
    return StandardResponse(
        success=True,
        data=[TableResponse.model_validate(t) for t in tables],
        request_id=request.state.request_id,
    )
