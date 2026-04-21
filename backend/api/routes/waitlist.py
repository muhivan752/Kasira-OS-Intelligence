"""
Waitlist Interest Tracker — Batch #27.

Non-F&B user (Retail/Service) yang coba akses Pro feature → diarahkan ke
waitlist (bukan bayar). Endpoint ini capture interest untuk early access
saat Pro-Retail / Pro-Service ship nanti (~3-6 bulan).

Storage: Event table (append-only audit log). Zero schema change. Query via
`event_type='waitlist.interest'` filter saat nanti kirim early-access WA.
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.event import Event

logger = logging.getLogger(__name__)

router = APIRouter()


class WaitlistJoinRequest(BaseModel):
    domain: str = Field(..., description="'retail' | 'service'")
    display_name: Optional[str] = Field(None, max_length=80, description="e.g. 'Bengkel', 'Salon'")
    source: str = Field("upgrade_sheet", max_length=40, description="UI location yang trigger CTA")


@router.post("/join")
async def join_waitlist(
    body: WaitlistJoinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """
    Record user interest untuk Pro-Retail / Pro-Service waitlist.

    Logged ke Event table — searchable via `event_type='waitlist.interest'`.
    Idempotent di sisi client (Flutter pake SharedPrefs flag supaya gak
    double-submit per user/domain), server sini tetep accept semua (append-only).
    """
    if body.domain not in ("retail", "service", "fnb"):
        raise HTTPException(status_code=400, detail=f"Domain '{body.domain}' tidak valid")

    # Fetch outlet_id dari user (first active outlet) — optional, buat grouping.
    # Pakai raw tenant_id untuk tenant-scoped tracking.
    from sqlalchemy import select
    from backend.models.outlet import Outlet
    outlet_id = None
    try:
        result = await db.execute(
            select(Outlet.id)
            .where(Outlet.tenant_id == current_user.tenant_id, Outlet.deleted_at.is_(None))
            .limit(1)
        )
        outlet_id = result.scalar_one_or_none()
    except Exception:
        pass  # best-effort

    event = Event(
        outlet_id=outlet_id,
        stream_id=f"waitlist:{current_user.tenant_id}:{body.domain}",
        event_type="waitlist.interest",
        event_data={
            "domain": body.domain,
            "display_name": body.display_name,
            "source": body.source,
            "tenant_id": str(current_user.tenant_id),
            "user_id": str(current_user.id),
            "phone": current_user.phone,
        },
        event_metadata={
            "actor": f"user:{current_user.id}",
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(event)
    try:
        await db.commit()
    except Exception as e:
        logger.error(f"waitlist join commit failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Gagal simpan waitlist")

    logger.info(
        "waitlist.interest: tenant=%s user=%s domain=%s display=%s",
        current_user.tenant_id, current_user.id, body.domain, body.display_name,
    )

    return {
        "success": True,
        "data": {
            "domain": body.domain,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        },
    }
