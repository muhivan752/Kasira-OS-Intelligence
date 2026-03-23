import httpx
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

async def send_whatsapp_message(phone: str, message: str) -> bool:
    if not settings.FONNTE_TOKEN:
        logger.warning(f"FONNTE_TOKEN not set. Simulating sending WA to {phone}: {message}")
        return True
        
    url = "https://api.fonnte.com/send"
    headers = {
        "Authorization": settings.FONNTE_TOKEN
    }
    data = {
        "target": phone,
        "message": message
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()
            result = response.json()
            if result.get("status"):
                return True
            else:
                logger.error(f"Fonnte API error: {result}")
                return False
    except Exception as e:
        logger.error(f"Failed to send WA message via Fonnte: {e}")
        return False
