"""
KG Price Event Loop — margin drift alert.

Tails `ingredient.price_updated` events (emitted from PUT /ingredients/{id}
when cost_per_base_unit changes), computes per-product margin drift via KG
edges, and WA-notifies tenant owner when threshold crossed.

Trigger source:
- `ingredients.py:245-257` emits Event(event_type='ingredient.price_updated',
  event_data={before:{cost_per_base_unit}, after:{cost_per_base_unit}, ...})

Flow per event:
1. Gate on cost delta >= 20% (cheap prefilter — ignore rounding / tiny bumps).
2. Resolve tenant via outlet_id. Skip demo / suspended / cancelled.
3. Dedup: skip if `margin_alert.sent` emitted today for same (tenant, ingredient).
4. Compute margin drift per affected product using KG `contains` edges:
   - HPP_before = sum(cost_contribution) with old cost swapped in for THIS ingredient
   - HPP_after  = sum(cost_contribution) with all current ingredient costs
5. Flag products with margin_drop >= 5pp OR new margin < 20%.
6. Fetch owner phone (tenant superuser). Send WA via existing Fonnte service.
7. Emit `margin_alert.sent` event (dedup + audit trail).

No schema change — reuses Event table (append-only), KG edges, Fonnte WA.
Idempotent — safe to re-run; dedup prevents dup WA within same calendar day.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, date
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.models.event import Event
from backend.models.outlet import Outlet
from backend.models.tenant import Tenant
from backend.models.ingredient import Ingredient
from backend.models.product import Product
from backend.models.knowledge_graph import KnowledgeGraphEdge
from backend.models.user import User
from backend.services.unit_utils import cost_from_qty_unit
from backend.services.fonnte import send_whatsapp_message

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 300          # 5 min
STAGGER_SECONDS = 150           # after startup
LOOKBACK_HOURS = 6              # re-scan window; dedup handles overlap

# Thresholds
COST_DELTA_MIN = 0.20           # ≥20% price bump to consider
MARGIN_DROP_PP = 5.0            # ≥5 percentage-point absolute margin drop
MARGIN_CRITICAL = 20.0          # new margin below this = alert regardless of drop
MAX_PRODUCTS_IN_MSG = 5         # truncate WA message


async def _get_owner_phone(db: AsyncSession, tenant_id: UUID) -> str | None:
    """Tenant superuser = owner. Mirrors subscription_billing._get_owner_phone."""
    stmt = select(User.phone).where(
        User.tenant_id == tenant_id,
        User.is_superuser == True,
        User.deleted_at.is_(None),
    ).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def _already_alerted_today(
    db: AsyncSession, tenant_id: UUID, ingredient_id: UUID
) -> bool:
    """Dedup: has margin_alert.sent been emitted for this (tenant, ingredient) today?"""
    today_start = datetime.combine(
        date.today(), datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    stream = f"tenant:{tenant_id}:ingredient:{ingredient_id}"
    res = await db.execute(
        select(Event.id).where(
            Event.event_type == "margin_alert.sent",
            Event.stream_id == stream,
            Event.created_at >= today_start,
        ).limit(1)
    )
    return res.first() is not None


class _GhostIngredient:
    """Tiny shim so cost_from_qty_unit can receive a swapped cost."""
    __slots__ = ("cost_per_base_unit", "base_unit")

    def __init__(self, cost: float, base_unit: str):
        self.cost_per_base_unit = cost
        self.base_unit = base_unit


async def _compute_margin_drift(
    db: AsyncSession,
    tenant_id: UUID,
    ingredient_id: UUID,
    old_cost: float,
    new_cost: float,
) -> list[dict]:
    """
    For each product that uses `ingredient_id`, compute HPP before & after the
    cost change and derive margin. Returns per-product records with margins.
    """
    # Affected products via KG `used_by` edges
    used_by = (await db.execute(
        select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.source_node_type == "ingredient",
            KnowledgeGraphEdge.source_node_id == ingredient_id,
            KnowledgeGraphEdge.relation_type == "used_by",
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).scalars().all()
    if not used_by:
        return []

    product_ids = list({e.target_node_id for e in used_by})

    products = {p.id: p for p in (await db.execute(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.deleted_at.is_(None),
        )
    )).scalars().all()}
    if not products:
        return []

    # Pull ALL `contains` edges for these products — need every ingredient per
    # product to compute total HPP (swap only the target ingredient's cost).
    contain_edges = (await db.execute(
        select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == tenant_id,
            KnowledgeGraphEdge.source_node_type == "product",
            KnowledgeGraphEdge.source_node_id.in_(product_ids),
            KnowledgeGraphEdge.relation_type == "contains",
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).scalars().all()

    ing_ids = {e.target_node_id for e in contain_edges}
    ingredients = {i.id: i for i in (await db.execute(
        select(Ingredient).where(
            Ingredient.id.in_(list(ing_ids)),
            Ingredient.deleted_at.is_(None),
        )
    )).scalars().all()}

    edges_by_product: dict[UUID, list] = {}
    for e in contain_edges:
        edges_by_product.setdefault(e.source_node_id, []).append(e)

    results: list[dict] = []
    for pid, prod in products.items():
        price = float(prod.base_price or 0)
        if price <= 0:
            continue

        hpp_before = 0.0
        hpp_after = 0.0
        missing_target = True  # sanity: did we actually hit the changed ingredient?
        for e in edges_by_product.get(pid, []):
            ing = ingredients.get(e.target_node_id)
            if ing is None:
                continue
            meta = e.metadata_payload or {}
            qty_raw = meta.get("quantity", 0)
            unit_raw = str(meta.get("unit") or ing.base_unit or "")

            if e.target_node_id == ingredient_id:
                missing_target = False
                cb = cost_from_qty_unit(
                    qty_raw, unit_raw, _GhostIngredient(old_cost, ing.base_unit)
                )
                ca = cost_from_qty_unit(
                    qty_raw, unit_raw, _GhostIngredient(new_cost, ing.base_unit)
                )
            else:
                cb = cost_from_qty_unit(qty_raw, unit_raw, ing)
                ca = cb

            if cb is None or ca is None:
                # unit mismatch — skip this line from sum (conservative)
                continue
            hpp_before += cb
            hpp_after += ca

        if missing_target:
            continue  # KG stale — `used_by` claimed but no `contains` edge

        margin_before = (price - hpp_before) / price * 100
        margin_after = (price - hpp_after) / price * 100
        results.append({
            "product_id": str(pid),
            "product_name": prod.name,
            "price": price,
            "hpp_before": round(hpp_before, 2),
            "hpp_after": round(hpp_after, 2),
            "margin_before": round(margin_before, 1),
            "margin_after": round(margin_after, 1),
            "margin_drop_pp": round(margin_before - margin_after, 1),
        })

    return results


def _format_alert(
    ingredient_name: str,
    old_cost: float,
    new_cost: float,
    flagged: list[dict],
    total_affected: int,
) -> str:
    delta_pct = ((new_cost - old_cost) / old_cost * 100) if old_cost > 0 else 0
    lines = [
        "⚠️ *Kasira — Peringatan Margin*",
        "",
        f"Harga *{ingredient_name}* naik:",
        f"Rp{old_cost:,.0f} → Rp{new_cost:,.0f} ({delta_pct:+.1f}%)",
        "",
        f"Produk terdampak ({len(flagged)} dari {total_affected}):",
    ]
    for item in sorted(flagged, key=lambda x: x["margin_drop_pp"], reverse=True)[:MAX_PRODUCTS_IN_MSG]:
        lines.append(
            f"• {item['product_name']}: margin {item['margin_before']}% → "
            f"*{item['margin_after']}%* (turun {item['margin_drop_pp']}pp)"
        )
    remaining = len(flagged) - MAX_PRODUCTS_IN_MSG
    if remaining > 0:
        lines.append(f"…+{remaining} produk lain")
    lines.append("")
    lines.append("Cek *Dashboard → Laporan → HPP* untuk detail & revisi harga.")
    return "\n".join(lines)


async def process_price_events_once() -> dict:
    """Single pass: tail recent price events, alert on margin drift."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    stats = {
        "events_seen": 0,
        "skipped_delta": 0,
        "skipped_tenant_state": 0,
        "skipped_dedup": 0,
        "skipped_no_flagged": 0,
        "skipped_no_owner": 0,
        "alerts_sent": 0,
        "alerts_wa_failed": 0,
    }

    async with AsyncSessionLocal() as db:
        # Janitor-style cross-tenant scan
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

        events = (await db.execute(
            select(Event).where(
                Event.event_type == "ingredient.price_updated",
                Event.created_at > cutoff,
            ).order_by(Event.created_at.asc())
        )).scalars().all()

        for event in events:
            stats["events_seen"] += 1

            data = event.event_data or {}
            before = data.get("before") or {}
            after = data.get("after") or {}
            try:
                old_cost = float(before.get("cost_per_base_unit", 0) or 0)
                new_cost = float(after.get("cost_per_base_unit", 0) or 0)
            except (TypeError, ValueError):
                continue
            if old_cost <= 0 or new_cost <= 0:
                continue

            delta_pct = (new_cost - old_cost) / old_cost
            if delta_pct < COST_DELTA_MIN:
                stats["skipped_delta"] += 1
                continue

            ing_id_raw = data.get("ingredient_id")
            if not ing_id_raw:
                continue
            try:
                ingredient_id = UUID(ing_id_raw)
            except (TypeError, ValueError):
                continue

            outlet = await db.get(Outlet, event.outlet_id)
            if outlet is None or outlet.tenant_id is None:
                continue

            tenant = await db.get(Tenant, outlet.tenant_id)
            if tenant is None:
                continue
            if getattr(tenant, "is_demo", False):
                stats["skipped_tenant_state"] += 1
                continue
            status_val = (
                tenant.subscription_status.value
                if hasattr(tenant.subscription_status, "value")
                else str(tenant.subscription_status or "")
            )
            if status_val not in ("active", "trial"):
                stats["skipped_tenant_state"] += 1
                continue

            if await _already_alerted_today(db, tenant.id, ingredient_id):
                stats["skipped_dedup"] += 1
                continue

            drift = await _compute_margin_drift(
                db=db,
                tenant_id=tenant.id,
                ingredient_id=ingredient_id,
                old_cost=old_cost,
                new_cost=new_cost,
            )
            flagged = [
                d for d in drift
                if d["margin_drop_pp"] >= MARGIN_DROP_PP
                or d["margin_after"] < MARGIN_CRITICAL
            ]
            if not flagged:
                stats["skipped_no_flagged"] += 1
                continue

            owner_phone = await _get_owner_phone(db, tenant.id)
            if not owner_phone:
                stats["skipped_no_owner"] += 1
                logger.info(
                    "kg_price_events: tenant %s no owner phone (%d flagged)",
                    tenant.id, len(flagged),
                )
                # still emit dedup event so we don't re-evaluate every loop
                ok = False
            else:
                ingredient_name = data.get("name") or "bahan"
                msg = _format_alert(
                    ingredient_name, old_cost, new_cost, flagged, len(drift)
                )
                try:
                    ok = await send_whatsapp_message(owner_phone, msg)
                except Exception as e:
                    logger.error(
                        "kg_price_events: WA error tenant %s: %s", tenant.id, e
                    )
                    ok = False
                if ok:
                    stats["alerts_sent"] += 1
                else:
                    stats["alerts_wa_failed"] += 1

            # Emit dedup event regardless of WA outcome — prevents retry storm
            db.add(Event(
                outlet_id=event.outlet_id,
                stream_id=f"tenant:{tenant.id}:ingredient:{ingredient_id}",
                event_type="margin_alert.sent",
                event_data={
                    "tenant_id": str(tenant.id),
                    "ingredient_id": str(ingredient_id),
                    "ingredient_name": data.get("name"),
                    "old_cost": old_cost,
                    "new_cost": new_cost,
                    "delta_pct": round(delta_pct * 100, 2),
                    "affected_count": len(drift),
                    "flagged_count": len(flagged),
                    "sample_products": [
                        {
                            "name": f["product_name"],
                            "margin_before": f["margin_before"],
                            "margin_after": f["margin_after"],
                            "drop_pp": f["margin_drop_pp"],
                        }
                        for f in sorted(
                            flagged, key=lambda x: x["margin_drop_pp"], reverse=True
                        )[:MAX_PRODUCTS_IN_MSG]
                    ],
                    "wa_sent": ok,
                },
                event_metadata={
                    "actor": "kg_price_event_loop",
                    "trigger_event_id": str(event.id),
                    "ts": datetime.now(timezone.utc).isoformat(),
                },
            ))

        try:
            await db.commit()
        except Exception as e:
            logger.error("kg_price_events: commit failed: %s", e)
            await db.rollback()

    if any(v for k, v in stats.items() if k != "events_seen") or stats["events_seen"]:
        logger.info("kg_price_events: %s", stats)
    return stats


async def kg_price_event_loop():
    """Run margin drift check every 5 min, forever."""
    logger.info(
        "KG price event loop started (interval: %ds, stagger: %ds, lookback: %dh)",
        INTERVAL_SECONDS, STAGGER_SECONDS, LOOKBACK_HOURS,
    )
    await asyncio.sleep(STAGGER_SECONDS)
    while True:
        try:
            await process_price_events_once()
        except Exception as e:
            logger.error("kg_price_event_loop error: %s", e)
        await asyncio.sleep(INTERVAL_SECONDS)
