import asyncio
import uuid
import json
import logging
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

from backend.api.api import api_router
from backend.core.config import settings
from backend.core.database import tenant_context
from backend.services.xendit import xendit_service


def _rate_limit_key(request: Request) -> str:
    """
    Rate limit key:
      1. Authorization Bearer JWT → decode `sub` (user_id) — per-user limit
      2. Fallback ke IP (untuk public endpoint atau request tanpa JWT)

    Parsing JWT disini tanpa validate expiry/signature — fine untuk key-func doang,
    karena endpoint dep `get_current_user` nanti tetep validate. Tujuan: user di
    belakang NAT/CGN gak kena limit gabungan.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
        try:
            # JWT = header.payload.signature — decode payload only
            import base64, json as _json
            parts = token.split(".")
            if len(parts) == 3:
                payload_raw = parts[1]
                # b64url padding
                payload_raw += "=" * (-len(payload_raw) % 4)
                payload = _json.loads(base64.urlsafe_b64decode(payload_raw))
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
        except Exception:
            pass
    return get_remote_address(request)


# Skip rate limit untuk health check dan webhook eksternal (Xendit retry webhook bisa spike)
_RATE_LIMIT_EXEMPT_PATHS = {"/health", "/health/background", "/", "/favicon.ico"}
_RATE_LIMIT_EXEMPT_PREFIXES = ("/api/v1/webhooks/",)


def _is_exempt(request: Request) -> bool:
    path = request.url.path
    if path in _RATE_LIMIT_EXEMPT_PATHS:
        return True
    return any(path.startswith(p) for p in _RATE_LIMIT_EXEMPT_PREFIXES)


# Limiter: 200 req/min per key sebagai default — cukup generous untuk POS flow
# (create order + payment + sync tiap beberapa detik), tapi auto-block bot flood.
limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=["200/minute"],
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
    headers_enabled=True,
)

# ── Sentry (Rule #45 pre-pilot: monitoring wajib) ─────────────────────────────
if settings.SENTRY_DSN and settings.SENTRY_DSN.strip().startswith('http'):
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else "production",
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,       # 10% performance tracing — cukup untuk pre-pilot
        profiles_sample_rate=0.0,
        send_default_pii=False,       # JANGAN kirim PII (GDPR + privacy)
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup & shutdown lifecycle.

    CRITICAL #11 fix: dulu pake raw `asyncio.create_task` — kalau loop crash
    = silent gone (payment reconciliation loop mati = pending payments lolos
    reconcile). Sekarang pake TaskSupervisor — auto-restart + traceback
    logging + graceful cancel + health tracking.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    from backend.tasks.payment_reconciliation import payment_reconciliation_loop
    from backend.tasks.subscription_billing import generate_invoices_loop, grace_period_loop
    from backend.tasks.platform_aggregation import (
        daily_stats_loop, hpp_benchmark_loop, ingredient_price_loop, insights_loop,
    )
    from backend.core.task_supervisor import task_supervisor

    # Register semua background loop via factory (bukan panggil langsung).
    # Factory dipanggil ulang tiap restart — koroutine baru setiap kali.
    task_supervisor.register("payment_reconciliation", lambda: payment_reconciliation_loop())
    task_supervisor.register("subscription_billing", lambda: generate_invoices_loop())
    task_supervisor.register("grace_period", lambda: grace_period_loop())
    task_supervisor.register("daily_stats", lambda: daily_stats_loop())
    task_supervisor.register("hpp_benchmark", lambda: hpp_benchmark_loop())
    task_supervisor.register("ingredient_price", lambda: ingredient_price_loop())
    task_supervisor.register("insights", lambda: insights_loop())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    # Graceful: supervisor cancel semua task + await 10s max. Task yang
    # responsive ke CancelledError (pattern `await asyncio.sleep(...)`) akan
    # stop clean. Kalau ada yang stuck, force-cancel via process exit.
    await task_supervisor.stop(timeout=10.0)
    await xendit_service.close()

_is_prod = settings.ENVIRONMENT == "production"

# Defense-in-depth: SafeJSONResponse handles numpy.ndarray + numpy scalars
# yang bisa leak dari pgvector/embedding column. Route dgn response_model=...
# tetap via Pydantic (ini cuma affect route yang return dict/list langsung).
from backend.core.json_safe import SafeJSONResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    # Disable OpenAPI/docs di production — cegah endpoint enumeration + schema leak
    openapi_url=None if _is_prod else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    lifespan=lifespan,
    default_response_class=SafeJSONResponse,
)

# Global rate limiter (200/min per key). Health + webhook paths di-exempt via
# subclass supaya gak kena flood dari uptime check / Xendit webhook retry.
app.state.limiter = limiter


class ConditionalSlowAPIMiddleware(SlowAPIMiddleware):
    """
    Middleware wrapper dgn FAIL-OPEN semantic untuk Redis backend.

    Pre-existing bug: saat Redis down, slowapi internal propagate
    redis.ConnectionError ke `_rate_limit_exceeded_handler` yg expect
    `RateLimitExceeded` (punya .detail) → AttributeError → 500.
    Seluruh request chain break gara-gara rate limiter backend.

    Fix: catch Exception di dispatch, kalau NOT RateLimitExceeded = Redis
    issue → log + bypass rate limit (fail-open). Request user TETAP jalan.
    """
    async def dispatch(self, request: Request, call_next):
        if _is_exempt(request):
            return await call_next(request)
        try:
            return await super().dispatch(request, call_next)
        except RateLimitExceeded:
            # Legit rate limit hit — biarin slowapi handler handle (429)
            raise
        except Exception as e:
            # Redis down atau internal slowapi error → fail OPEN
            # Log sbg warning (bukan error) karena auto-recover saat Redis balik
            logger.warning(
                "slowapi backend error (rate limit bypassed for %s %s): %s: %s",
                request.method, request.url.path, type(e).__name__, e,
            )
            return await call_next(request)


app.add_middleware(ConditionalSlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set CORS enabled origins from env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID", "public")
        token = tenant_context.set(tenant_id)
        try:
            response = await call_next(request)
            return response
        finally:
            tenant_context.reset(token)

from backend.core.request_context import request_id_context

class ResponseFormatMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            # Add request_id to headers
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "data": None,
                    "meta": None,
                    "request_id": request_id
                }
            )
        finally:
            request_id_context.reset(token)

app.add_middleware(ResponseFormatMiddleware)
app.add_middleware(TenantMiddleware)

from backend.schemas.response import StandardResponse

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve uploaded images as static files
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/", response_model=StandardResponse[dict])
async def root():
    return StandardResponse(data={"message": "Welcome to Kasira POS API"}, message="Welcome")

@app.get("/health")
async def health():
    """Health check endpoint for uptime monitoring."""
    from backend.core.database import engine
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception:
        from fastapi import Response
        return Response(status_code=503, content='{"status":"error","db":"unreachable"}')


@app.get("/health/background")
async def health_background_tasks():
    """
    Background task supervisor health snapshot (CRITICAL #11).
    Include state per-task + restart count + last crash reason. Return 503
    kalau ada task yang udah DEAD (supervisor give up restart).

    Usage: internal monitoring / Sentry check / cron alert script.
    """
    from backend.core.task_supervisor import task_supervisor
    from fastapi import Response
    import json as _json
    snapshot = task_supervisor.health_snapshot()
    status_code = 200 if task_supervisor.is_healthy() else 503
    return Response(
        status_code=status_code,
        content=_json.dumps(snapshot, default=str),
        media_type="application/json",
    )
