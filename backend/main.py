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

logger = logging.getLogger(__name__)

from backend.api.api import api_router
from backend.core.config import settings
from backend.core.database import tenant_context
from backend.services.xendit import xendit_service

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
    """Startup & shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────────────
    from backend.tasks.payment_reconciliation import payment_reconciliation_loop
    from backend.tasks.subscription_billing import generate_invoices_loop, grace_period_loop
    from backend.tasks.platform_aggregation import (
        daily_stats_loop, hpp_benchmark_loop, ingredient_price_loop, insights_loop,
    )
    reconciliation_task = asyncio.create_task(payment_reconciliation_loop())
    billing_task = asyncio.create_task(generate_invoices_loop())
    grace_task = asyncio.create_task(grace_period_loop())
    # Platform intelligence (silent aggregation)
    daily_stats_task = asyncio.create_task(daily_stats_loop())
    hpp_task = asyncio.create_task(hpp_benchmark_loop())
    ingredient_task = asyncio.create_task(ingredient_price_loop())
    insights_task = asyncio.create_task(insights_loop())
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    reconciliation_task.cancel()
    billing_task.cancel()
    grace_task.cancel()
    daily_stats_task.cancel()
    hpp_task.cancel()
    ingredient_task.cancel()
    insights_task.cancel()
    await xendit_service.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

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
