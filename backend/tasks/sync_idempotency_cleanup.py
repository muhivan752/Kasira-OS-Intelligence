"""
Sync Idempotency Keys Cleanup — Weekly janitor for `sync_idempotency_keys`.

Background:
- Migration 081 (2026-04-19) adds `sync_idempotency_keys` table for offline
  sync retry dedup (Flutter sends `idempotency_key` per batch, server claims
  atomically via `INSERT ON CONFLICT DO NOTHING RETURNING`).
- Retention: 7 days. Flutter retry window is far shorter (minutes-hours),
  so keys older than 7d are guaranteed unused.
- Table only grows — zero cleanup = unbounded growth. On a busy tenant,
  hundreds of sync batches per day × N tenants = fast index bloat.

Loop:
- Stagger: 300s after startup (avoid nabrak other janitors at boot).
- Interval: 7 days (604800s). Weekly cadence.
- Query: `DELETE FROM sync_idempotency_keys WHERE processed_at < :cutoff`
  — uses existing `ix_sync_idempotency_processed` index (migration 081).
- RLS bypass via `SET LOCAL app.current_tenant_id = ''` (cross-tenant).
- Idempotent: re-runs within same window delete nothing (cheap no-op).
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

from backend.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

RETENTION_DAYS = 7
CHECK_INTERVAL_SECONDS = 7 * 24 * 3600  # 1 week
STARTUP_DELAY_SECONDS = 300  # stagger: 5min after boot


async def cleanup_idempotency_keys_once() -> int:
    """
    Single pass: delete keys older than retention window across all tenants.

    RLS note: migration 081 RLS policy uses hard UUID cast without empty-string
    bypass (unlike `orders`/`tabs` policies). Setting `app.current_tenant_id = ''`
    breaks with `invalid input syntax for type uuid`. Fix: iterate tenants + set
    context per-tenant. Tenants table has no RLS → enumeration is free.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    total_deleted = 0
    tenant_count = 0
    async with AsyncSessionLocal() as db:
        try:
            tenants = (await db.execute(
                text("SELECT id FROM tenants WHERE deleted_at IS NULL")
            )).scalars().all()
            tenant_count = len(tenants)

            for tid in tenants:
                # Scope RLS to this tenant — satisfies `tenant_id = ...::uuid` policy
                await db.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                    {"tid": str(tid)},
                )
                result = await db.execute(
                    text(
                        "DELETE FROM sync_idempotency_keys "
                        "WHERE processed_at < :cutoff"
                    ),
                    {"cutoff": cutoff},
                )
                total_deleted += result.rowcount or 0
            await db.commit()
        except Exception as e:
            logger.error(f"sync_idempotency_cleanup: delete failed: {e}")
            await db.rollback()
            return 0

    if total_deleted:
        logger.info(
            f"sync_idempotency_cleanup: deleted {total_deleted} key(s) "
            f"older than {RETENTION_DAYS}d across {tenant_count} tenants "
            f"(cutoff={cutoff.isoformat()})"
        )
    return total_deleted


async def sync_idempotency_cleanup_loop():
    """Run cleanup once per week, forever."""
    logger.info(
        f"Sync idempotency cleanup loop started "
        f"(interval: {CHECK_INTERVAL_SECONDS}s, retention: {RETENTION_DAYS}d)"
    )
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        try:
            await cleanup_idempotency_keys_once()
        except Exception as e:
            logger.error(f"sync_idempotency_cleanup_loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
