"""
Kasira Analytics API — Menu Engineering & Combo Detection
"""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.response import StandardResponse
from backend.services.menu_engineering_service import classify_menu, detect_combos

router = APIRouter()


@router.get("/menu-engineering", response_model=StandardResponse)
async def get_menu_engineering(
    request: Request,
    outlet_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Menu Engineering BCG Matrix — classify products into Star/Plowhorse/Puzzle/Dog.
    Default period: last 30 days.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    result = await classify_menu(
        db=db,
        brand_id=current_user.tenant_id,
        outlet_id=outlet_id,
        start_date=start_date,
        end_date=end_date,
    )

    return StandardResponse(
        data=result,
        request_id=request.state.request_id,
        message="Menu engineering analysis",
    )


@router.get("/combos", response_model=StandardResponse)
async def get_combo_detection(
    request: Request,
    outlet_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    min_support: int = 3,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Combo Detection — find products frequently ordered together.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    combos = await detect_combos(
        db=db,
        outlet_id=outlet_id,
        start_date=start_date,
        end_date=end_date,
        min_support=min_support,
        limit=limit,
    )

    return StandardResponse(
        data=combos,
        request_id=request.state.request_id,
        message=f"Found {len(combos)} combo pairs",
    )
