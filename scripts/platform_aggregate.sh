#!/bin/bash
# Platform Intelligence — nightly cross-tenant aggregation
# Run via cron: 30 17 * * * /var/www/kasira/scripts/platform_aggregate.sh
# (17:30 UTC = 00:30 WIB — runs after reset_sold_today at 00:00)

LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')] platform_aggregate:"

echo "$LOG_PREFIX Starting aggregation..."

# Run inside the backend container — uses async Python
docker exec kasira-backend-1 python -c "
import asyncio
import sys
sys.path.insert(0, '/app')

async def run():
    from backend.core.database import engine, AsyncSessionLocal
    from backend.services.platform_intelligence import (
        aggregate_daily_stats,
        aggregate_hpp_benchmarks,
        aggregate_ingredient_prices,
        generate_platform_insights,
    )

    async with AsyncSessionLocal() as db:
        # 1. Daily stats (yesterday)
        r1 = await aggregate_daily_stats(db)
        print(f'Daily stats: {r1}')

        # 2. HPP benchmarks (weekly, runs daily but only changes on new data)
        r2 = await aggregate_hpp_benchmarks(db)
        print(f'HPP benchmarks: {r2}')

        # 3. Ingredient prices
        r3 = await aggregate_ingredient_prices(db)
        print(f'Ingredient prices: {r3}')

        # 4. Platform insights
        r4 = await generate_platform_insights(db)
        print(f'Insights: {r4}')

    await engine.dispose()
    print('All aggregations complete.')

asyncio.run(run())
" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "$LOG_PREFIX Done (success)"
else
    echo "$LOG_PREFIX FAILED (exit code $EXIT_CODE)"
fi
