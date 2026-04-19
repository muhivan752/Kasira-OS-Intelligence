"""
Prometheus metrics + middleware — observability stack Kasira (#10).

Design:
  - Lightweight middleware: cuma `time.perf_counter()` diff + metric emit
    per request (<1µs overhead). Zero impact pada hot path POS checkout.
  - Metrics stored in-memory via prometheus_client, exposed via /metrics
    endpoint (Prometheus scraper format).
  - Custom business metrics untuk Kasira: sync volume per table, Xendit
    payment outcomes, background task health aggregation.

Registered metrics:

  HTTP:
    kasira_http_requests_total           (counter) method, path, status
    kasira_http_request_duration_seconds (histogram) method, path, status
    kasira_http_requests_in_progress     (gauge) method, path

  Business:
    kasira_sync_records_total  (counter) table, direction (push/pull)
    kasira_xendit_calls_total  (counter) method, outcome (ok/transient_fail/permanent_fail)
    kasira_fonnte_calls_total  (counter) outcome (ok/fail/circuit_open)

  Infra:
    kasira_bg_tasks_alive           (gauge) task
    kasira_bg_tasks_restarts_total  (counter) task
"""

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# Dedicated registry untuk hindari duplicate registration saat reload.
METRICS_REGISTRY = CollectorRegistry(auto_describe=False)


# ─── HTTP metrics ─────────────────────────────────────────────────────────────
http_requests_total = Counter(
    "kasira_http_requests_total",
    "Total HTTP requests received.",
    labelnames=("method", "path_template", "status_code"),
    registry=METRICS_REGISTRY,
)

http_request_duration_seconds = Histogram(
    "kasira_http_request_duration_seconds",
    "HTTP request latency distribution.",
    labelnames=("method", "path_template", "status_code"),
    # Buckets tuned untuk POS/API latency — kalau median >500ms = slow
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=METRICS_REGISTRY,
)

http_requests_in_progress = Gauge(
    "kasira_http_requests_in_progress",
    "HTTP requests currently being processed (concurrent).",
    labelnames=("method", "path_template"),
    registry=METRICS_REGISTRY,
)


# ─── Business metrics ─────────────────────────────────────────────────────────
sync_records_total = Counter(
    "kasira_sync_records_total",
    "Total records transferred via /sync/ endpoint.",
    labelnames=("table", "direction"),  # direction = push | pull
    registry=METRICS_REGISTRY,
)

xendit_calls_total = Counter(
    "kasira_xendit_calls_total",
    "Xendit API outbound calls dgn outcome breakdown.",
    labelnames=("method", "outcome"),  # outcome = ok | transient_fail | permanent_fail
    registry=METRICS_REGISTRY,
)

fonnte_calls_total = Counter(
    "kasira_fonnte_calls_total",
    "Fonnte WA API outbound calls dgn outcome breakdown.",
    labelnames=("outcome",),  # ok | fail | circuit_open
    registry=METRICS_REGISTRY,
)


# ─── Infra metrics (bg task supervisor) ───────────────────────────────────────
bg_tasks_alive = Gauge(
    "kasira_bg_tasks_alive",
    "Background task alive state (1=running/crashed-recovering, 0=dead/stopped).",
    labelnames=("task",),
    registry=METRICS_REGISTRY,
)

bg_tasks_restarts_total = Counter(
    "kasira_bg_tasks_restarts_total",
    "Cumulative background task restart count.",
    labelnames=("task",),
    registry=METRICS_REGISTRY,
)


# ─── Path template extraction ─────────────────────────────────────────────────
def _get_path_template(request: Request) -> str:
    """
    Get route path template (e.g. `/orders/{order_id}`) daripada full URL
    dgn concrete ID — cegah label explosion di Prometheus (unique UUIDs
    bikin cardinality meledak).
    """
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    # Fallback: normalize path by replacing UUIDs / ints w/ placeholder
    path = request.url.path
    import re
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", path)
    path = re.sub(r"/\d+", "/{n}", path)
    return path


# ─── Middleware ───────────────────────────────────────────────────────────────
class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware yg emit HTTP metrics. Zero impact pada hot path (<1µs overhead).
    Install ke app AFTER routers defined supaya route template resolved benar.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Skip /metrics sendiri untuk avoid recursive logging
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path_template = _get_path_template(request)
        in_progress = http_requests_in_progress.labels(method=method, path_template=path_template)
        in_progress.inc()

        start = time.perf_counter()
        status_code = 500  # default kalau exception mid-request
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration = time.perf_counter() - start
            status_str = str(status_code)
            http_requests_total.labels(
                method=method, path_template=path_template, status_code=status_str,
            ).inc()
            http_request_duration_seconds.labels(
                method=method, path_template=path_template, status_code=status_str,
            ).observe(duration)
            in_progress.dec()


# ─── Business metric helpers ──────────────────────────────────────────────────
def observe_sync_volume(table: str, direction: str, count: int) -> None:
    """Call di sync handler untuk track record volume per table per direction."""
    if count <= 0:
        return
    try:
        sync_records_total.labels(table=table, direction=direction).inc(count)
    except Exception:
        # Metrics tidak critical — never break business logic
        pass


def track_xendit_outcome(method: str, outcome: str) -> None:
    """
    Dipanggil di xendit service wrapper.
    outcome: ok | transient_fail | permanent_fail
    """
    try:
        xendit_calls_total.labels(method=method, outcome=outcome).inc()
    except Exception:
        pass


def track_fonnte_outcome(outcome: str) -> None:
    """outcome: ok | fail | circuit_open"""
    try:
        fonnte_calls_total.labels(outcome=outcome).inc()
    except Exception:
        pass


# ─── Background task supervisor integration ──────────────────────────────────
def update_bg_task_metrics() -> None:
    """
    Refresh gauge + counter dari TaskSupervisor.health_snapshot().
    Dipanggil saat /metrics di-scrape (pull model) — jadi always fresh.
    """
    try:
        from backend.core.task_supervisor import task_supervisor
        snap = task_supervisor.health_snapshot()
        for name, state in snap.get("tasks", {}).items():
            alive_val = 1.0 if state.get("alive") and state.get("state") != "dead" else 0.0
            bg_tasks_alive.labels(task=name).set(alive_val)
            # Restart counter — pake internal total (counter MUST be monotonic,
            # so kalau restart_count turun, log warning tapi jangan panic)
            restart_count = state.get("restart_count", 0)
            # Gauge-like counter via direct labels access
            try:
                current = bg_tasks_restarts_total.labels(task=name)
                # prometheus_client Counter tidak expose set — inc() jalan forever
                # Strategy: increment delta sejak last observe. Simpan last-seen
                # count di module global.
                _last = _BG_RESTART_LAST.get(name, 0)
                delta = restart_count - _last
                if delta > 0:
                    current.inc(delta)
                    _BG_RESTART_LAST[name] = restart_count
            except Exception:
                pass
    except Exception as e:
        logger.debug("bg task metrics refresh failed: %s", e)


_BG_RESTART_LAST: dict = {}


# ─── /metrics endpoint handler ────────────────────────────────────────────────
def metrics_endpoint_response() -> Response:
    """Generate Prometheus exposition format response."""
    update_bg_task_metrics()  # refresh before scrape
    output = generate_latest(METRICS_REGISTRY)
    return Response(
        content=output,
        media_type=CONTENT_TYPE_LATEST,
    )
