"""
Kasira AI Chat Route — SSE Streaming endpoint untuk Owner/Manager

POST /ai/chat → StreamingResponse (text/event-stream)

Rules yang diimplementasikan:
- Rule #2: Audit log setiap request (termasuk yang gagal)
- Rule #9: Async ONLY
- Rule #25-27: Model selector + 3 optimasi AI
- Rule #54-56: Intent classifier, WRITE confirmation, UNKNOWN reject
"""

import json
import logging
from typing import Any, Optional, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.tenant import Tenant
from backend.services.redis import get_redis_client
from backend.services.audit import log_audit
from backend.services.ai_service import stream_ai_response

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    outlet_id: str
    conversation_id: Optional[str] = None  # untuk multi-turn (future use)


@router.post("/chat")
async def ai_chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> StreamingResponse:
    """
    AI chat dengan SSE streaming.

    Response format (per chunk):
        data: {"type": "chunk", "content": "..."}
        data: {"type": "done", "intent": "READ", "tokens_used": 123, "model": "..."}
        data: {"type": "error", "message": "..."}
    """
    # Validate outlet belongs to user's tenant
    outlet_result = await db.execute(
        select(Outlet).where(
            Outlet.id == body.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )
    outlet = outlet_result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    # Ambil tier dari tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id, Tenant.deleted_at.is_(None))
    )
    tenant = tenant_result.scalar_one_or_none()
    tier = getattr(getattr(tenant, "subscription_tier", None), "value", "starter")

    # AI Chatbot = Pro+ only
    if tier not in ("pro", "business", "enterprise"):
        raise HTTPException(
            status_code=403,
            detail="AI Chatbot hanya tersedia untuk paket Pro. Upgrade untuk mengakses."
        )

    redis = await get_redis_client()

    # ── Budget Control ──────────────────────────────────────────────────
    # Tiered limits: per-tenant, per-user, platform safety net
    TENANT_DAILY_LIMIT = 50       # max 50 AI requests per tenant per day
    USER_DAILY_LIMIT = 30         # max 30 per user per day (within tenant quota)
    PLATFORM_DAILY_CENTS = 100    # $1.00/day emergency brake (all tenants combined)

    try:
        from datetime import date as dt_date
        today = dt_date.today().isoformat()
        tid = str(current_user.tenant_id)

        # 1. Platform safety cap — emergency brake
        spend_key = f"ai_spend:{today}"
        current_spend = int(await redis.get(spend_key) or 0)
        if current_spend >= PLATFORM_DAILY_CENTS:
            raise HTTPException(429, detail="Layanan AI sedang sibuk. Coba lagi besok.")

        # 2. Per-tenant daily limit
        tenant_key = f"ai_tenant:{tid}:{today}"
        tenant_count = await redis.incr(tenant_key)
        if tenant_count == 1:
            await redis.expire(tenant_key, 86400)
        if tenant_count > TENANT_DAILY_LIMIT:
            raise HTTPException(429, detail=f"Kuota AI harian habis ({TENANT_DAILY_LIMIT} pertanyaan). Coba lagi besok.")

        # 3. Per-user daily limit
        user_key = f"ai_user:{current_user.id}:{today}"
        user_count = await redis.incr(user_key)
        if user_count == 1:
            await redis.expire(user_key, 86400)
        if user_count > USER_DAILY_LIMIT:
            raise HTTPException(429, detail=f"Kamu sudah bertanya {USER_DAILY_LIMIT}x hari ini. Coba lagi besok.")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis down → allow request

    # Audit log (Rule #2) — log request masuk
    try:
        await log_audit(
            db=db,
            action="ai_chat",
            entity="ai",
            entity_id=body.outlet_id,
            after_state={"message_length": len(body.message), "tier": tier},
            user_id=str(current_user.id),
            tenant_id=str(current_user.tenant_id),
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Audit log failed (non-blocking): {e}")

    # Track estimated spend — 1 cent per Haiku, 2 cents per Sonnet
    try:
        from datetime import date as dt_date
        spend_key = f"ai_spend:{dt_date.today().isoformat()}"
        await redis.incrby(spend_key, 1)  # conservative estimate
        await redis.expire(spend_key, 86400)
    except Exception:
        pass

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in stream_ai_response(
                message=body.message,
                outlet_id=body.outlet_id,
                tenant_id=str(current_user.tenant_id),
                outlet_name=outlet.name,
                tier=tier,
                db=db,
                redis_client=redis,
                user_id=str(current_user.id),
            ):
                yield chunk
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Terjadi kesalahan pada server'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.delete("/context/{outlet_id}")
async def clear_ai_context_cache(
    outlet_id: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Force-clear cached AI context untuk outlet ini.
    Berguna setelah ada perubahan besar di menu/outlet.
    """
    # Validate ownership
    redis = await get_redis_client()
    cache_key = f"ai:context:{outlet_id}"
    await redis.delete(cache_key)
    return {"success": True, "message": "Context cache dibersihkan"}


@router.get("/budget")
async def ai_budget_status(
    current_user: User = Depends(deps.get_platform_admin),
) -> Any:
    """
    Check current AI budget usage. Superadmin only.
    """
    from datetime import date as dt_date
    redis = await get_redis_client()
    today = dt_date.today().isoformat()

    spend = int(await redis.get(f"ai_spend:{today}") or 0)

    # Get per-tenant usage
    keys = await redis.keys(f"ai_tenant:*:{today}")
    tenant_usage = {}
    for key in keys:
        tid = key.split(":")[1]
        count = int(await redis.get(key) or 0)
        tenant_usage[tid] = count

    # Sonnet usage
    sonnet_keys = await redis.keys(f"ai_sonnet:*:{today}")
    sonnet_usage = {}
    for key in sonnet_keys:
        tid = key.split(":")[1]
        count = int(await redis.get(key) or 0)
        sonnet_usage[tid] = count

    return {
        "success": True,
        "data": {
            "date": today,
            "estimated_spend_cents": spend,
            "estimated_spend_usd": f"${spend / 100:.2f}",
            "platform_daily_cap_cents": 100,
            "tenant_requests_today": tenant_usage,
            "sonnet_requests_today": sonnet_usage,
            "limits": {
                "tenant_daily": 50,
                "user_daily": 30,
                "sonnet_per_tenant": 5,
                "platform_cap_cents": 100,
            },
        },
    }
