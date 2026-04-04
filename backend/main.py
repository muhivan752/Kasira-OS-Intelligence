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
    """Startup & shutdown lifecycle — pastikan connection pool Xendit ditutup dengan bersih."""
    # ── Startup ──────────────────────────────────────────────────────────────
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
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
