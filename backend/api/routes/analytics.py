"""
Kasira Analytics API — Menu Engineering, Combo Detection, Hourly Trends
"""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.api import deps
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.platform import PlatformDailyStats
from backend.schemas.response import StandardResponse
from backend.services.menu_engineering_service import classify_menu, detect_combos

# Analytics = Pro+ only (menu engineering, combo detection, hourly trends)
# butuh data yg hanya tersedia di Pro (recipe cost, KG) atau analysis yg advanced.
router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])


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


@router.get("/hourly", response_model=StandardResponse)
async def get_hourly_distribution(
    request: Request,
    outlet_id: UUID,
    days: int = Query(7, ge=1, le=90, description="Berapa hari ke belakang"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Hourly distribution — jam-jam sibuk outlet berdasarkan data order.
    Aggregates hourly_distribution dari platform_daily_stats.
    Returns: per-hour totals + peak hour + average orders per hour.
    """
    end = date.today()
    start = end - timedelta(days=days)

    rows = (await db.execute(
        select(PlatformDailyStats.hourly_distribution, PlatformDailyStats.stat_date)
        .where(
            PlatformDailyStats.outlet_id == outlet_id,
            PlatformDailyStats.stat_date >= start,
            PlatformDailyStats.stat_date <= end,
            PlatformDailyStats.hourly_distribution.isnot(None),
        )
        .order_by(PlatformDailyStats.stat_date)
    )).all()

    # Aggregate across all days
    hourly_totals: dict[str, int] = {}
    days_with_data = 0
    for dist, _ in rows:
        if not dist:
            continue
        days_with_data += 1
        for hour, count in dist.items():
            hourly_totals[hour] = hourly_totals.get(hour, 0) + count

    # Sort by hour
    sorted_hours = sorted(hourly_totals.items(), key=lambda x: int(x[0]))

    # Find peak
    peak_hour = None
    peak_count = 0
    for h, c in sorted_hours:
        if c > peak_count:
            peak_hour = int(h)
            peak_count = c

    # Build response
    distribution = [
        {"hour": int(h), "label": f"{int(h):02d}:00", "orders": c}
        for h, c in sorted_hours
    ]

    return StandardResponse(
        data={
            "period": {"start": str(start), "end": str(end), "days": days, "days_with_data": days_with_data},
            "distribution": distribution,
            "peak_hour": peak_hour,
            "peak_hour_label": f"{peak_hour:02d}:00" if peak_hour is not None else None,
            "peak_orders": peak_count,
            "total_orders": sum(hourly_totals.values()),
        },
        request_id=request.state.request_id,
        message=f"Hourly distribution for {days_with_data} days",
    )
