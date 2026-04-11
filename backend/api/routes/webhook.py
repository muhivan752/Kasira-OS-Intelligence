"""
Kasira Webhook Routes — Fonnte incoming WhatsApp messages

POST /webhook/fonnte — receives incoming WA messages from Fonnte webhook
"""

import logging
from typing import Any

from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.models.outlet import Outlet
from backend.services.wa_bot import handle_incoming_wa
from backend.services.fonnte import send_whatsapp_message
from backend.services.redis import get_redis_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/fonnte")
async def fonnte_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Receive incoming WhatsApp messages from Fonnte webhook.

    Fonnte sends form data or JSON with fields:
    - device: device/phone number that received the message
    - sender: customer phone number
    - message: message text
    - url: media URL (if any)
    - filename: media filename
    - extension: media extension
    """
    # Temporarily disabled — remove this line when ready with dedicated number
    return {"status": "ok", "message": "webhook disabled"}

    try:
        # Fonnte can send as form data or JSON
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)

        sender = body.get("sender", "")
        message = body.get("message", "")
        device = body.get("device", "")

        if not sender or not message:
            return {"status": "ok", "message": "ignored — no sender or message"}

        # Clean sender phone
        sender = sender.strip().replace("+", "").replace("-", "").replace(" ", "")
        if sender.startswith("0"):
            sender = "62" + sender[1:]

        # Skip messages from groups (Fonnte prefixes group messages)
        if sender.endswith("@g.us") or "@" in sender:
            return {"status": "ok", "message": "ignored — group message"}

        # Skip own messages (echo)
        if sender == device:
            return {"status": "ok", "message": "ignored — own message"}

        logger.info(f"WA incoming: {sender} → {message[:50]}...")

        # Find which outlet this phone belongs to
        # For now: match by outlet phone number or use first active outlet
        # TODO: when multi-outlet support is added, match by device number
        outlet = None

        # Try to find outlet by phone matching the device
        if device:
            clean_device = device.strip().replace("+", "").replace("-", "").replace(" ", "")
            outlet_result = await db.execute(
                select(Outlet).where(
                    Outlet.phone == clean_device,
                    Outlet.deleted_at.is_(None),
                    Outlet.is_active == True,
                )
            )
            outlet = outlet_result.scalar_one_or_none()

        # Fallback: use any active outlet with reservation enabled
        if not outlet:
            from backend.models.reservation import ReservationSettings
            outlet_result = await db.execute(
                select(Outlet).join(
                    ReservationSettings, ReservationSettings.outlet_id == Outlet.id
                ).where(
                    Outlet.deleted_at.is_(None),
                    Outlet.is_active == True,
                    ReservationSettings.is_enabled == True,
                ).limit(1)
            )
            outlet = outlet_result.scalar_one_or_none()

        # Last fallback: first active outlet
        if not outlet:
            outlet_result = await db.execute(
                select(Outlet).where(
                    Outlet.deleted_at.is_(None),
                    Outlet.is_active == True,
                ).limit(1)
            )
            outlet = outlet_result.scalar_one_or_none()

        if not outlet:
            logger.warning("No active outlet found for webhook")
            return {"status": "ok", "message": "no outlet"}

        # Process message
        redis_client = await get_redis_client()
        response = await handle_incoming_wa(
            phone=sender,
            message=message.strip(),
            outlet_id=str(outlet.id),
            outlet_name=outlet.name,
            redis_client=redis_client,
            db=db,
        )

        # Send reply via Fonnte
        if response:
            await send_whatsapp_message(sender, response)

        return {"status": "ok", "message": "processed"}

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
