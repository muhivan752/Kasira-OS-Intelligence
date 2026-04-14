"""
Platform Aggregation — Silent background tasks for cross-tenant intelligence.

Loops:
1. daily_stats_loop       — every 6 hours, aggregate daily stats per outlet
2. hpp_benchmark_loop     — every Monday, HPP comparison across merchants
3. ingredient_price_loop  — every 12 hours, ingredient price index
4. insights_loop          — every 24 hours, generate AI-ready insights

All idempotent (UPSERT), all try/except, all have staggered startup delays.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from backend.core.database import AsyncSessionLocal
from backend.services.platform_intelligence import (
    aggregate_daily_stats,
    aggregate_hpp_benchmarks,
    aggregate_ingredient_prices,
    generate_platform_insights,
)

logger = logging.getLogger(__name__)

DAILY_STATS_INTERVAL = 6 * 3600        # 6 jam
HPP_BENCHMARK_INTERVAL = 24 * 3600     # 24 jam (cek apakah hari Senin)
INGREDIENT_PRICE_INTERVAL = 12 * 3600  # 12 jam
INSIGHTS_INTERVAL = 24 * 3600          # 24 jam


async def daily_stats_loop():
    """Aggregate daily stats every 6 hours."""
    logger.info("Platform daily_stats_loop started (interval: 6h)")
    await asyncio.sleep(30)  # stagger: 30s after startup
    while True:
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                await db.execute(text('SET search_path TO public'))
                result = await aggregate_daily_stats(db)
                logger.info(f"daily_stats: {result}")
        except Exception as e:
            logger.error(f"daily_stats_loop error: {e}")
        await asyncio.sleep(DAILY_STATS_INTERVAL)


async def hpp_benchmark_loop():
    """Aggregate HPP benchmarks — runs daily but only processes on Mondays."""
    logger.info("Platform hpp_benchmark_loop started (interval: 24h, Mondays only)")
    await asyncio.sleep(60)  # stagger: 60s
    while True:
        try:
            today = datetime.now(timezone.utc).date()
            if today.weekday() == 0:  # Monday
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import text
                    await db.execute(text('SET search_path TO public'))
                    result = await aggregate_hpp_benchmarks(db)
                    logger.info(f"hpp_benchmark: {result}")
            else:
                logger.debug(f"hpp_benchmark: skipped (not Monday, today={today.strftime('%A')})")
        except Exception as e:
            logger.error(f"hpp_benchmark_loop error: {e}")
        await asyncio.sleep(HPP_BENCHMARK_INTERVAL)


async def ingredient_price_loop():
    """Aggregate ingredient prices every 12 hours."""
    logger.info("Platform ingredient_price_loop started (interval: 12h)")
    await asyncio.sleep(90)  # stagger: 90s
    while True:
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                await db.execute(text('SET search_path TO public'))
                result = await aggregate_ingredient_prices(db)
                logger.info(f"ingredient_price: {result}")
        except Exception as e:
            logger.error(f"ingredient_price_loop error: {e}")
        await asyncio.sleep(INGREDIENT_PRICE_INTERVAL)


async def insights_loop():
    """Generate platform insights every 24 hours."""
    logger.info("Platform insights_loop started (interval: 24h)")
    await asyncio.sleep(120)  # stagger: 120s
    while True:
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                await db.execute(text('SET search_path TO public'))
                result = await generate_platform_insights(db)
                logger.info(f"insights: {result}")
        except Exception as e:
            logger.error(f"insights_loop error: {e}")
        await asyncio.sleep(INSIGHTS_INTERVAL)
