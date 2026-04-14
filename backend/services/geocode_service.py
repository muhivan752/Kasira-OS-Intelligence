"""
Reverse geocoding via Nominatim (OpenStreetMap).
Free, no API key needed. Rate limit: 1 req/sec.
Used for silent location enrichment — never blocks user flow.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.outlet import Outlet

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "KasiraPOS/1.0 (kasira.id)"


async def reverse_geocode(lat: float, lng: float) -> dict | None:
    """Call Nominatim reverse geocode. Returns address dict or None."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "jsonv2",
                    "addressdetails": 1,
                },
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})
            return {
                "city": addr.get("city") or addr.get("town") or addr.get("municipality"),
                "district": addr.get("suburb") or addr.get("village") or addr.get("neighbourhood"),
                "province": addr.get("state"),
                "postal_code": addr.get("postcode"),
            }
    except Exception as e:
        logger.warning(f"Nominatim reverse geocode failed: {e}")
        return None


async def enrich_outlet_location_silent(outlet_id, lat: float, lng: float):
    """Background task: reverse geocode and update outlet with city/district/province."""
    from backend.core.database import AsyncSessionLocal

    try:
        geo = await reverse_geocode(lat, lng)
        if not geo or not geo.get("city"):
            logger.info(f"No city resolved for outlet {outlet_id} ({lat},{lng})")
            return

        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text('SET search_path TO public'))
            await session.execute(
                update(Outlet)
                .where(Outlet.id == outlet_id)
                .values(
                    city=geo["city"],
                    district=geo.get("district"),
                    province=geo.get("province"),
                    postal_code=geo.get("postal_code"),
                    geocoded_at=datetime.now(timezone.utc),
                    geocode_source="gps",
                )
            )
            await session.commit()
            logger.info(f"Outlet {outlet_id} geocoded → {geo['city']}, {geo.get('province')}")
    except Exception as e:
        logger.error(f"enrich_outlet_location_silent failed: {e}")
