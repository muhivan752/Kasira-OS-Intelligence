"""
Async Task Supervisor — auto-restart pattern untuk background loops.

Fix CRITICAL #11: dulu `asyncio.create_task(loop_fn())` di main.py lifespan
= kalau coroutine crash karena exception, silent gone. Payment reconciliation
loop mati = pending payments lolos reconcile sampai backend restart.

Scope: single-file supervisor. Caller register task via factory function,
supervisor handle lifecycle:
  1. Spawn task via factory
  2. Catch exception → log FULL traceback (exc_info=True, not silent)
  3. Auto-restart dengan exponential backoff (1s, 2s, 4s, 8s, cap 60s)
  4. Max restarts per hour — cegah runaway crash loop (mark DEAD kalau
     lewat threshold, log CRITICAL, jangan retry terus)
  5. Graceful shutdown via `await supervisor.stop(timeout)` di FastAPI
     lifespan — cancel all + await completion
  6. Health snapshot — /health/background endpoint expose state

Integration:
  - Zero touch ke task body code — supervisor wraps factory call
  - Task tetap own DB sessions (AsyncSessionLocal) — HLC/RLS tidak terganggu
  - CancelledError propagated (graceful shutdown), bukan counted as crash
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Coroutine, Dict, Optional

logger = logging.getLogger(__name__)


# ─── Config ───────────────────────────────────────────────────────────────────
DEFAULT_MAX_RESTARTS_PER_HOUR = 10
DEFAULT_BACKOFF_BASE = 1.0  # 1s * 2^n, capped 60s
DEFAULT_BACKOFF_CAP = 60.0
DEFAULT_SHUTDOWN_TIMEOUT = 10.0


@dataclass
class TaskHealth:
    """Per-task health state. Serializable untuk health endpoint."""
    name: str
    state: str = "running"  # running | crashed | dead | stopped
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    restart_count: int = 0
    last_crash_at: Optional[datetime] = None
    last_crash_reason: Optional[str] = None
    # Window tracking untuk rate-limit restart
    restart_window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    restarts_in_window: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "started_at": self.started_at.isoformat(),
            "restart_count": self.restart_count,
            "last_crash_at": self.last_crash_at.isoformat() if self.last_crash_at else None,
            "last_crash_reason": self.last_crash_reason,
        }


class TaskSupervisor:
    """
    Supervise long-running async tasks dgn auto-restart + health tracking.

    Usage:
      supervisor = TaskSupervisor()
      supervisor.register("payment_recon", lambda: payment_reconciliation_loop())
      # ... app runs ...
      await supervisor.stop(timeout=10)  # graceful shutdown
    """

    def __init__(
        self,
        max_restarts_per_hour: int = DEFAULT_MAX_RESTARTS_PER_HOUR,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        backoff_cap: float = DEFAULT_BACKOFF_CAP,
    ):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._health: Dict[str, TaskHealth] = {}
        self._factories: Dict[str, Callable[[], Coroutine]] = {}
        self._stopping = False
        self._max_restarts = max_restarts_per_hour
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap

    def register(self, name: str, coroutine_factory: Callable[[], Coroutine]) -> None:
        """
        Register dan start task.
        `coroutine_factory` = callable yg return FRESH coroutine tiap dipanggil.
        Example: `lambda: payment_reconciliation_loop()` (bukan panggil langsung).
        """
        if name in self._factories:
            logger.warning("TaskSupervisor: task '%s' already registered — skip", name)
            return
        self._factories[name] = coroutine_factory
        self._health[name] = TaskHealth(name=name)
        self._spawn(name)
        logger.info("TaskSupervisor: registered + started '%s'", name)

    def _spawn(self, name: str) -> None:
        """Create asyncio.Task wrapping the supervised coroutine."""
        if self._stopping:
            return
        task = asyncio.create_task(self._wrapped_run(name), name=f"supervised:{name}")
        self._tasks[name] = task

    def _check_restart_rate(self, name: str) -> bool:
        """
        Return True kalau masih boleh restart (under rate limit).
        Rate: max_restarts_per_hour dalam rolling 1-hour window.
        """
        h = self._health[name]
        now = datetime.now(timezone.utc)
        window_age_sec = (now - h.restart_window_start).total_seconds()
        if window_age_sec >= 3600:
            # Window expired — reset
            h.restart_window_start = now
            h.restarts_in_window = 0
        h.restarts_in_window += 1
        return h.restarts_in_window <= self._max_restarts

    async def _wrapped_run(self, name: str) -> None:
        """
        Run task body dgn crash detection + exponential-backoff restart.
        CancelledError propagated untuk graceful shutdown — tidak dihitung crash.
        """
        factory = self._factories[name]
        h = self._health[name]

        while not self._stopping:
            try:
                coro = factory()
                await coro
                # Normal exit — tidak umum untuk long-running loop
                logger.warning(
                    "TaskSupervisor: task '%s' exited normally (not restarting). "
                    "Background loops biasanya infinite — cek factory apakah break.",
                    name,
                )
                h.state = "stopped"
                return

            except asyncio.CancelledError:
                logger.info("TaskSupervisor: task '%s' cancelled (graceful shutdown)", name)
                h.state = "stopped"
                raise  # propagate cancel

            except BaseException as e:  # noqa: BLE001 — catch-all on purpose
                h.restart_count += 1
                h.last_crash_at = datetime.now(timezone.utc)
                h.last_crash_reason = f"{type(e).__name__}: {e}"

                # Log FULL traceback (exc_info=True) — zero silent failure
                logger.error(
                    "TaskSupervisor: task '%s' CRASHED (restart #%d) — traceback below",
                    name, h.restart_count,
                    exc_info=True,
                )

                # Rate-limit restart — cegah runaway crash loop jadi CPU spike
                if not self._check_restart_rate(name):
                    logger.critical(
                        "TaskSupervisor: task '%s' exceeded max restarts (%d/hour) — "
                        "marking DEAD. Manual intervention required. "
                        "Last reason: %s",
                        name, self._max_restarts, h.last_crash_reason,
                    )
                    h.state = "dead"
                    return

                # Exponential backoff sebelum restart (capped)
                # attempt 1: 1s, 2: 2s, 3: 4s, 4: 8s, 5: 16s, 6: 32s, 7+: 60s
                backoff = min(
                    self._backoff_cap,
                    self._backoff_base * (2 ** min(h.restart_count - 1, 6)),
                )
                h.state = "crashed"
                logger.info(
                    "TaskSupervisor: task '%s' restart in %.1fs (window: %d/%d)",
                    name, backoff, h.restarts_in_window, self._max_restarts,
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    logger.info("TaskSupervisor: shutdown during backoff '%s'", name)
                    h.state = "stopped"
                    raise
                h.state = "running"
                h.started_at = datetime.now(timezone.utc)  # fresh lifecycle

    async def stop(self, timeout: float = DEFAULT_SHUTDOWN_TIMEOUT) -> None:
        """
        Graceful shutdown — cancel all supervised tasks + await completion.
        Dipanggil di FastAPI lifespan shutdown block.
        """
        if self._stopping:
            return
        self._stopping = True
        logger.info("TaskSupervisor: shutdown initiated (%d task(s))", len(self._tasks))

        tasks = list(self._tasks.values())
        for t in tasks:
            t.cancel()

        if not tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout,
            )
            logger.info("TaskSupervisor: all tasks stopped gracefully")
        except asyncio.TimeoutError:
            logger.warning(
                "TaskSupervisor: shutdown timeout (%.1fs) — some task didn't respond. "
                "Tasks yang masih running di-force-cancel by process exit.",
                timeout,
            )

    def health_snapshot(self) -> dict:
        """
        Return aggregate health + per-task detail. Dipakai /health/background endpoint.
        """
        tasks_state = {}
        overall = "healthy"
        for name, h in self._health.items():
            task = self._tasks.get(name)
            alive = task is not None and not task.done()
            detail = h.to_dict()
            detail["alive"] = alive
            tasks_state[name] = detail
            if h.state == "dead":
                overall = "degraded"
            elif h.state == "crashed" and overall == "healthy":
                overall = "crashed_recent"
        return {
            "overall": overall,
            "task_count": len(self._tasks),
            "tasks": tasks_state,
        }

    def is_healthy(self) -> bool:
        """True kalau tidak ada task DEAD (crashed + recovering OK)."""
        return not any(h.state == "dead" for h in self._health.values())


# Singleton — di-share di lifespan + health endpoint
task_supervisor = TaskSupervisor()
