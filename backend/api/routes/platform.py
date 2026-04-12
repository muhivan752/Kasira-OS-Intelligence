"""
Platform Intelligence API — Superadmin only.
Trigger aggregation jobs and view cross-tenant benchmarks.
"""

from typing import Any, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.response import StandardResponse
from backend.services.platform_intelligence import (
    aggregate_daily_stats,
    aggregate_hpp_benchmarks,
    aggregate_ingredient_prices,
    generate_platform_insights,
)

router = APIRouter()


def _require_superadmin(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin only")


@router.post("/aggregate/daily", response_model=StandardResponse)
async def run_daily_aggregation(
    target_date: Optional[date] = Query(None, description="Date to aggregate (default: yesterday)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superadmin(current_user)
    result = await aggregate_daily_stats(db, target_date)
    return StandardResponse(success=True, data=result, message="Daily stats aggregated")


@router.post("/aggregate/hpp", response_model=StandardResponse)
async def run_hpp_aggregation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superadmin(current_user)
    result = await aggregate_hpp_benchmarks(db)
    return StandardResponse(success=True, data=result, message="HPP benchmarks aggregated")


@router.post("/aggregate/ingredients", response_model=StandardResponse)
async def run_ingredient_aggregation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superadmin(current_user)
    result = await aggregate_ingredient_prices(db)
    return StandardResponse(success=True, data=result, message="Ingredient prices indexed")


@router.post("/aggregate/insights", response_model=StandardResponse)
async def run_insight_generation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_superadmin(current_user)
    result = await generate_platform_insights(db)
    return StandardResponse(success=True, data=result, message="Platform insights generated")


@router.post("/aggregate/all", response_model=StandardResponse)
async def run_all_aggregations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Run all aggregation jobs in sequence. For cron / manual trigger."""
    _require_superadmin(current_user)
    results = {}
    results["daily"] = await aggregate_daily_stats(db)
    results["hpp"] = await aggregate_hpp_benchmarks(db)
    results["ingredients"] = await aggregate_ingredient_prices(db)
    results["insights"] = await generate_platform_insights(db)
    return StandardResponse(success=True, data=results, message="All aggregations complete")
