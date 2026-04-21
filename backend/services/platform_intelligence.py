"""
Kasira Platform Intelligence — Cross-Tenant Aggregation Engine

Reads events + data from ALL merchants, aggregates into anonymized benchmarks.
Feeds back into per-tenant AI context so each merchant can "mawas diri".

Jobs:
1. aggregate_daily_stats()  — nightly, per-outlet daily rollup from events
2. aggregate_hpp_benchmarks() — weekly, HPP comparison across merchants
3. aggregate_ingredient_prices() — daily, ingredient price index
4. generate_platform_insights() — daily, AI-ready insight summaries
"""

import logging
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, text, delete, and_, case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.event import Event
from backend.models.order import Order
from backend.models.payment import Payment
from backend.models.outlet import Outlet
from backend.models.tenant import Tenant
from backend.models.product import Product
from backend.models.category import Category
from backend.models.ingredient import Ingredient
from backend.models.brand import Brand
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.knowledge_graph import KnowledgeGraphEdge
from backend.models.platform import (
    PlatformDailyStats,
    PlatformHppBenchmark,
    PlatformIngredientPrice,
    PlatformInsight,
)

logger = logging.getLogger(__name__)


# ─── Job 1: Daily Stats Aggregation ──────────────────────────────────────────

async def aggregate_daily_stats(db: AsyncSession, target_date: Optional[date] = None) -> Dict:
    """
    Aggregate daily stats per outlet from events table.
    Runs nightly for yesterday. Can be re-run for any date (idempotent via UPSERT).
    """
    # Bypass RLS for cross-tenant access
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    logger.info(f"Aggregating daily stats for {target_date}")

    # Get all active outlets with their tenant info + location
    outlets = (await db.execute(
        select(Outlet.id, Outlet.tenant_id, Tenant.subscription_tier,
               Outlet.city, Outlet.district, Outlet.province)
        .join(Tenant, Outlet.tenant_id == Tenant.id)
        .where(Outlet.deleted_at.is_(None), Tenant.is_active == True, Tenant.is_demo == False)
    )).all()

    stats_created = 0

    for outlet_id, tenant_id, tier, outlet_city, outlet_district, outlet_province in outlets:
        # Revenue + order count from completed orders
        revenue_q = await db.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
                func.count(Order.id).label("cnt"),
            ).where(
                Order.outlet_id == outlet_id,
                Order.created_at >= start,
                Order.created_at < end,
                Order.status == "completed",
                Order.deleted_at.is_(None),
            )
        )
        rev_row = revenue_q.first()
        revenue = float(rev_row.revenue) if rev_row else 0
        order_count = int(rev_row.cnt) if rev_row else 0

        if order_count == 0:
            continue  # Skip outlets with no orders

        avg_order = revenue / order_count if order_count > 0 else 0

        # Cancel count from events
        cancel_q = await db.execute(
            select(func.count(Event.id)).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.cancelled",
                Event.created_at >= start,
                Event.created_at < end,
            )
        )
        cancel_count = cancel_q.scalar() or 0

        # Channel breakdown from order.created events
        source_col = Event.event_data["source"].astext
        source_q = await db.execute(
            select(source_col.label("src"), func.count(Event.id).label("cnt"))
            .where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.created",
                Event.created_at >= start,
                Event.created_at < end,
            ).group_by(source_col)
        )
        orders_pos = 0
        orders_storefront = 0
        for r in source_q.all():
            if r.src == "pos":
                orders_pos = r.cnt
            elif r.src == "storefront":
                orders_storefront = r.cnt

        # Payment method breakdown
        method_col = Event.event_data["method"].astext
        pay_q = await db.execute(
            select(method_col.label("method"), func.count(Event.id).label("cnt"))
            .where(
                Event.outlet_id == outlet_id,
                Event.event_type == "payment.completed",
                Event.created_at >= start,
                Event.created_at < end,
            ).group_by(method_col)
        )
        payments_cash = 0
        payments_qris = 0
        for r in pay_q.all():
            if r.method == "cash":
                payments_cash = r.cnt
            elif r.method == "qris":
                payments_qris = r.cnt

        # Peak hour + hourly distribution
        hour_q = await db.execute(
            select(
                func.extract("hour", Event.created_at).label("h"),
                func.count(Event.id).label("cnt"),
            ).where(
                Event.outlet_id == outlet_id,
                Event.event_type == "order.created",
                Event.created_at >= start,
                Event.created_at < end,
            ).group_by(func.extract("hour", Event.created_at))
            .order_by(func.count(Event.id).desc())
        )
        hour_rows = hour_q.all()
        peak_hour = None
        peak_hour_orders = 0
        hourly_dist = {}
        for hr in hour_rows:
            h_wib = int(hr.h) + 7  # UTC → WIB
            if h_wib >= 24:
                h_wib -= 24
            hourly_dist[str(h_wib)] = hr.cnt
        if hour_rows and hour_rows[0].cnt > 0:
            h = int(hour_rows[0].h) + 7
            if h >= 24:
                h -= 24
            peak_hour = h
            peak_hour_orders = hour_rows[0].cnt

        # Unique products sold
        from backend.models.order import OrderItem
        unique_q = await db.execute(
            select(func.count(func.distinct(OrderItem.product_id)))
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.outlet_id == outlet_id,
                Order.created_at >= start,
                Order.created_at < end,
                Order.status == "completed",
            )
        )
        unique_products = unique_q.scalar() or 0

        # UPSERT
        tier_val = tier.value if hasattr(tier, "value") else str(tier) if tier else "starter"
        stmt = pg_insert(PlatformDailyStats).values(
            tenant_id=tenant_id,
            outlet_id=outlet_id,
            stat_date=target_date,
            revenue=revenue,
            order_count=order_count,
            avg_order_value=avg_order,
            cancel_count=cancel_count,
            orders_pos=orders_pos,
            orders_storefront=orders_storefront,
            payments_cash=payments_cash,
            payments_qris=payments_qris,
            peak_hour=peak_hour,
            peak_hour_orders=peak_hour_orders,
            unique_products_sold=unique_products,
            tier=tier_val,
            city=outlet_city,
            district=outlet_district,
            province=outlet_province,
            hourly_distribution=hourly_dist or None,
        ).on_conflict_do_update(
            constraint="uq_platform_daily_outlet_date",
            set_={
                "revenue": revenue,
                "order_count": order_count,
                "avg_order_value": avg_order,
                "cancel_count": cancel_count,
                "orders_pos": orders_pos,
                "orders_storefront": orders_storefront,
                "payments_cash": payments_cash,
                "payments_qris": payments_qris,
                "peak_hour": peak_hour,
                "peak_hour_orders": peak_hour_orders,
                "unique_products_sold": unique_products,
                "tier": tier_val,
                "city": outlet_city,
                "district": outlet_district,
                "province": outlet_province,
                "hourly_distribution": hourly_dist or None,
            },
        )
        await db.execute(stmt)
        stats_created += 1

    await db.commit()
    logger.info(f"Daily stats: {stats_created} outlets aggregated for {target_date}")
    return {"date": str(target_date), "outlets_processed": stats_created}


# ─── Job 2: HPP Benchmarks ──────────────────────────────────────────────────

async def aggregate_hpp_benchmarks(db: AsyncSession, target_week: Optional[date] = None) -> Dict:
    """
    Aggregate HPP benchmarks per product type across all merchants.
    Groups by normalized product name (lowered, trimmed) for fuzzy matching.
    Runs weekly on Monday for previous week.
    """
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    if target_week is None:
        today = datetime.now(timezone.utc).date()
        target_week = today - timedelta(days=today.weekday())  # Monday of current week

    logger.info(f"Aggregating HPP benchmarks for week of {target_week}")

    # Get all products with recipes + ingredients via KG edges
    edges = (await db.execute(
        select(
            KnowledgeGraphEdge.source_node_id.label("product_id"),
            KnowledgeGraphEdge.target_node_id.label("ingredient_id"),
            KnowledgeGraphEdge.metadata_payload,
        ).where(
            KnowledgeGraphEdge.relation_type == "contains",
            KnowledgeGraphEdge.deleted_at.is_(None),
        )
    )).all()

    if not edges:
        return {"week": str(target_week), "benchmarks_created": 0}

    # Load products + ingredients
    product_ids = set(e.product_id for e in edges)
    ingredient_ids = set(e.ingredient_id for e in edges)

    from backend.models.brand import Brand
    # Exclude demo tenant products
    demo_tenant_ids = [t for t in (await db.execute(
        select(Tenant.id).where(Tenant.is_demo == True)
    )).scalars().all()]

    products = {p.id: p for p in (await db.execute(
        select(Product)
        .join(Brand, Product.brand_id == Brand.id)
        .where(
            Product.id.in_(list(product_ids)),
            Product.deleted_at.is_(None),
            Brand.tenant_id.notin_(demo_tenant_ids) if demo_tenant_ids else True,
        )
    )).scalars().all()}

    ingredients = {i.id: i for i in (await db.execute(
        select(Ingredient).where(Ingredient.id.in_(list(ingredient_ids)), Ingredient.deleted_at.is_(None))
    )).scalars().all()}

    # Get categories
    cat_ids = set(p.category_id for p in products.values() if p.category_id)
    categories = {}
    if cat_ids:
        categories = {c.id: c for c in (await db.execute(
            select(Category).where(Category.id.in_(list(cat_ids)))
        )).scalars().all()}

    # Compute HPP per product
    product_hpp: Dict[UUID, Dict] = {}
    for e in edges:
        prod = products.get(e.product_id)
        ing = ingredients.get(e.ingredient_id)
        if not prod or not ing:
            continue

        meta = e.metadata_payload or {}
        qty = Decimal(str(meta.get("quantity", 0)))
        cost = qty * (ing.cost_per_base_unit or Decimal("0"))

        if e.product_id not in product_hpp:
            cat = categories.get(prod.category_id)
            product_hpp[e.product_id] = {
                "name": prod.name.lower().strip(),
                "category": cat.name if cat else "Uncategorized",
                "price": float(prod.base_price or 0),
                "hpp": Decimal("0"),
                "ingredients": [],
            }
        product_hpp[e.product_id]["hpp"] += cost
        product_hpp[e.product_id]["ingredients"].append({
            "name": ing.name,
            "cost": float(cost),
        })

    # Group by normalized product name and aggregate
    name_groups: Dict[str, List] = {}
    for pid, data in product_hpp.items():
        key = data["name"]
        if key not in name_groups:
            name_groups[key] = []
        name_groups[key].append(data)

    benchmarks_created = 0
    for name, items in name_groups.items():
        hpps = [float(i["hpp"]) for i in items]
        prices = [i["price"] for i in items]
        category = items[0]["category"]

        avg_hpp = sum(hpps) / len(hpps)
        avg_price = sum(prices) / len(prices) if prices else 0
        margin = ((avg_price - avg_hpp) / avg_price * 100) if avg_price > 0 else 0

        # Top ingredients (most common across samples)
        all_ings = {}
        for item in items:
            for ing in item["ingredients"]:
                iname = ing["name"]
                if iname not in all_ings:
                    all_ings[iname] = {"name": iname, "total_cost": 0, "count": 0}
                all_ings[iname]["total_cost"] += ing["cost"]
                all_ings[iname]["count"] += 1
        top_ings = sorted(all_ings.values(), key=lambda x: x["count"], reverse=True)[:5]
        for ti in top_ings:
            ti["avg_cost"] = round(ti["total_cost"] / ti["count"], 2)
            del ti["total_cost"]

        stmt = pg_insert(PlatformHppBenchmark).values(
            category_name=category,
            product_name_normalized=name,
            stat_week=target_week,
            sample_count=len(items),
            avg_hpp=round(avg_hpp, 2),
            min_hpp=min(hpps),
            max_hpp=max(hpps),
            avg_price=round(avg_price, 2),
            avg_margin_pct=round(margin, 2),
            top_ingredients=top_ings,
        ).on_conflict_do_update(
            constraint="uq_hpp_bench_product_week",
            set_={
                "category_name": category,
                "sample_count": len(items),
                "avg_hpp": round(avg_hpp, 2),
                "min_hpp": min(hpps),
                "max_hpp": max(hpps),
                "avg_price": round(avg_price, 2),
                "avg_margin_pct": round(margin, 2),
                "top_ingredients": top_ings,
            },
        )
        await db.execute(stmt)
        benchmarks_created += 1

    await db.commit()
    logger.info(f"HPP benchmarks: {benchmarks_created} products aggregated for week {target_week}")
    return {"week": str(target_week), "benchmarks_created": benchmarks_created}


# ─── Job 3: Ingredient Price Index ──────────────────────────────────────────

async def aggregate_ingredient_prices(db: AsyncSession, target_date: Optional[date] = None) -> Dict:
    """
    Build ingredient price index from all merchants' ingredient data.
    Shows what everyone is paying for the same ingredients.
    """
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    logger.info(f"Aggregating ingredient prices for {target_date}")

    # Get all active ingredients with cost data (exclude demo tenants)
    ingredients = (await db.execute(
        select(
            func.lower(func.trim(Ingredient.name)).label("name"),
            Ingredient.base_unit,
            Ingredient.cost_per_base_unit,
        )
        .join(Brand, Ingredient.brand_id == Brand.id)
        .join(Tenant, Brand.tenant_id == Tenant.id)
        .where(
            Ingredient.deleted_at.is_(None),
            Ingredient.cost_per_base_unit > 0,
            Tenant.is_demo == False,
        )
    )).all()

    if not ingredients:
        return {"date": str(target_date), "ingredients_processed": 0}

    # Group by normalized name + unit
    groups: Dict[str, List[float]] = {}
    units: Dict[str, str] = {}
    for name, unit, cost in ingredients:
        key = f"{name}||{unit}"
        if key not in groups:
            groups[key] = []
            units[key] = unit
        groups[key].append(float(cost))

    # Get last week's prices for WoW comparison
    last_week = target_date - timedelta(days=7)
    prev_prices = {}
    prev_q = await db.execute(
        select(
            PlatformIngredientPrice.ingredient_name_normalized,
            PlatformIngredientPrice.base_unit,
            PlatformIngredientPrice.avg_cost_per_unit,
        ).where(PlatformIngredientPrice.stat_date == last_week)
    )
    for r in prev_q.all():
        prev_prices[f"{r.ingredient_name_normalized}||{r.base_unit}"] = float(r.avg_cost_per_unit)

    prices_created = 0
    for key, costs in groups.items():
        name = key.split("||")[0]
        unit = units[key]

        costs_sorted = sorted(costs)
        avg_cost = sum(costs) / len(costs)
        median_idx = len(costs_sorted) // 2
        median_cost = costs_sorted[median_idx] if costs_sorted else 0

        # WoW change
        prev = prev_prices.get(key)
        wow = None
        if prev and prev > 0:
            wow = round((avg_cost - prev) / prev * 100, 2)

        stmt = pg_insert(PlatformIngredientPrice).values(
            ingredient_name_normalized=name,
            base_unit=unit,
            stat_date=target_date,
            sample_count=len(costs),
            avg_cost_per_unit=round(avg_cost, 2),
            min_cost=min(costs),
            max_cost=max(costs),
            median_cost=round(median_cost, 2),
            wow_change_pct=wow,
        ).on_conflict_do_update(
            constraint="uq_ing_price_name_unit_date",
            set_={
                "sample_count": len(costs),
                "avg_cost_per_unit": round(avg_cost, 2),
                "min_cost": min(costs),
                "max_cost": max(costs),
                "median_cost": round(median_cost, 2),
                "wow_change_pct": wow,
            },
        )
        await db.execute(stmt)
        prices_created += 1

    await db.commit()
    logger.info(f"Ingredient prices: {prices_created} ingredients indexed for {target_date}")
    return {"date": str(target_date), "ingredients_processed": prices_created}


# ─── Job 4: Generate Platform Insights ───────────────────────────────────────

async def generate_platform_insights(db: AsyncSession) -> Dict:
    """
    Generate AI-ready insight summaries from aggregated data.
    These get injected into per-tenant AI context.
    """
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    now = datetime.now(timezone.utc)
    today = now.date()
    valid_from = now
    valid_until = now + timedelta(hours=24)
    insights_created = 0

    # 1. Platform-wide averages (last 7 days)
    week_ago = today - timedelta(days=7)
    platform_q = await db.execute(
        select(
            func.avg(PlatformDailyStats.revenue).label("avg_revenue"),
            func.avg(PlatformDailyStats.order_count).label("avg_orders"),
            func.avg(PlatformDailyStats.avg_order_value).label("avg_aov"),
            func.avg(PlatformDailyStats.cancel_count).label("avg_cancels"),
            func.sum(PlatformDailyStats.orders_storefront).label("total_sf"),
            func.sum(PlatformDailyStats.orders_pos).label("total_pos"),
            func.count(func.distinct(PlatformDailyStats.outlet_id)).label("active_outlets"),
        ).where(PlatformDailyStats.stat_date >= week_ago)
    )
    p = platform_q.first()
    if p and p.active_outlets and p.active_outlets > 0:
        total_orders = (float(p.total_sf or 0) + float(p.total_pos or 0))
        sf_pct = float(p.total_sf or 0) / total_orders * 100 if total_orders > 0 else 0

        stmt = pg_insert(PlatformInsight).values(
            insight_type="platform_averages",
            scope="all",
            insight_data={
                "period": f"{week_ago} to {today}",
                "active_outlets": int(p.active_outlets),
                "avg_daily_revenue": round(float(p.avg_revenue or 0)),
                "avg_daily_orders": round(float(p.avg_orders or 0), 1),
                "avg_order_value": round(float(p.avg_aov or 0)),
                "avg_daily_cancels": round(float(p.avg_cancels or 0), 1),
                "storefront_pct": round(sf_pct, 1),
            },
            valid_from=valid_from,
            valid_until=valid_until,
        )
        await db.execute(stmt)
        insights_created += 1

    # 2. Ingredient price alerts (WoW > 10%)
    price_alerts = (await db.execute(
        select(PlatformIngredientPrice).where(
            PlatformIngredientPrice.stat_date == today,
            func.abs(PlatformIngredientPrice.wow_change_pct) > 10,
        ).order_by(func.abs(PlatformIngredientPrice.wow_change_pct).desc())
        .limit(5)
    )).scalars().all()

    if price_alerts:
        alerts = [{
            "ingredient": a.ingredient_name_normalized,
            "unit": a.base_unit,
            "change_pct": float(a.wow_change_pct),
            "avg_cost": float(a.avg_cost_per_unit),
            "sample_count": a.sample_count,
        } for a in price_alerts]

        stmt = pg_insert(PlatformInsight).values(
            insight_type="price_alerts",
            scope="all",
            insight_data={"alerts": alerts},
            valid_from=valid_from,
            valid_until=valid_until,
        )
        await db.execute(stmt)
        insights_created += 1

    # 3. HPP benchmarks summary (latest week)
    hpp_q = await db.execute(
        select(PlatformHppBenchmark)
        .order_by(PlatformHppBenchmark.stat_week.desc(), PlatformHppBenchmark.sample_count.desc())
        .limit(20)
    )
    hpp_rows = hpp_q.scalars().all()
    if hpp_rows:
        benchmarks = [{
            "product": h.product_name_normalized,
            "category": h.category_name,
            "avg_hpp": float(h.avg_hpp),
            "avg_price": float(h.avg_price),
            "avg_margin_pct": float(h.avg_margin_pct),
            "sample_count": h.sample_count,
        } for h in hpp_rows]

        stmt = pg_insert(PlatformInsight).values(
            insight_type="hpp_benchmarks",
            scope="all",
            insight_data={"benchmarks": benchmarks},
            valid_from=valid_from,
            valid_until=valid_until,
        )
        await db.execute(stmt)
        insights_created += 1

    await db.commit()
    logger.info(f"Platform insights: {insights_created} insights generated")
    return {"insights_created": insights_created}


# ─── AI Context Injection ────────────────────────────────────────────────────

async def build_cross_tenant_context(
    tenant_id: UUID, outlet_id: UUID, db: AsyncSession
) -> str:
    """
    Build cross-tenant benchmark context for a specific merchant's AI chat.
    Shows how they compare to the platform average (anonymized).
    """
    await db.execute(text("SET LOCAL app.current_tenant_id = ''"))

    lines = []
    today = datetime.now(timezone.utc).date()

    # 1. Get merchant's own stats (last 7 days)
    week_ago = today - timedelta(days=7)
    own_stats = await db.execute(
        select(
            func.avg(PlatformDailyStats.revenue).label("avg_rev"),
            func.avg(PlatformDailyStats.order_count).label("avg_orders"),
            func.avg(PlatformDailyStats.avg_order_value).label("avg_aov"),
        ).where(
            PlatformDailyStats.outlet_id == outlet_id,
            PlatformDailyStats.stat_date >= week_ago,
        )
    )
    own = own_stats.first()

    # 2. Get platform averages
    platform_insight = await db.execute(
        select(PlatformInsight).where(
            PlatformInsight.insight_type == "platform_averages",
            PlatformInsight.valid_until >= datetime.now(timezone.utc),
        ).order_by(PlatformInsight.created_at.desc()).limit(1)
    )
    pi = platform_insight.scalar_one_or_none()

    if own and pi and own.avg_rev:
        pd = pi.insight_data
        own_rev = float(own.avg_rev)
        platform_rev = pd.get("avg_daily_revenue", 0)

        if platform_rev > 0:
            rev_vs = ((own_rev - platform_rev) / platform_rev) * 100
            rev_label = "di atas" if rev_vs > 0 else "di bawah"

            lines.append("\nBENCHMARK vs PLATFORM KASIRA:")
            lines.append(f"- Omzet harian kamu: Rp{own_rev:,.0f} ({abs(rev_vs):.0f}% {rev_label} rata-rata)")
            lines.append(f"- Rata-rata platform: Rp{platform_rev:,.0f}/hari dari {pd.get('active_outlets', '?')} outlet")

            own_aov = float(own.avg_aov) if own.avg_aov else 0
            platform_aov = pd.get("avg_order_value", 0)
            if platform_aov > 0:
                aov_vs = ((own_aov - platform_aov) / platform_aov) * 100
                aov_label = "di atas" if aov_vs > 0 else "di bawah"
                lines.append(f"- AOV kamu: Rp{own_aov:,.0f} vs platform Rp{platform_aov:,.0f} ({abs(aov_vs):.0f}% {aov_label})")

    # 3. Ingredient price alerts
    price_insight = await db.execute(
        select(PlatformInsight).where(
            PlatformInsight.insight_type == "price_alerts",
            PlatformInsight.valid_until >= datetime.now(timezone.utc),
        ).order_by(PlatformInsight.created_at.desc()).limit(1)
    )
    pa = price_insight.scalar_one_or_none()
    if pa and pa.insight_data.get("alerts"):
        alerts = pa.insight_data["alerts"]
        lines.append("\nALERT HARGA BAHAN (cross-merchant):")
        for a in alerts[:3]:
            direction = "naik" if a["change_pct"] > 0 else "turun"
            lines.append(
                f"- {a['ingredient']} {direction} {abs(a['change_pct']):.0f}% minggu ini "
                f"(avg Rp{a['avg_cost']:,.0f}/{a['unit']}, {a['sample_count']} merchant)"
            )

    # 4. HPP benchmarks for merchant's products
    hpp_insight = await db.execute(
        select(PlatformInsight).where(
            PlatformInsight.insight_type == "hpp_benchmarks",
            PlatformInsight.valid_until >= datetime.now(timezone.utc),
        ).order_by(PlatformInsight.created_at.desc()).limit(1)
    )
    hb = hpp_insight.scalar_one_or_none()
    if hb and hb.insight_data.get("benchmarks"):
        # Get this merchant's product names
        own_products = (await db.execute(
            select(func.lower(func.trim(Product.name)).label("name"))
            .join(Outlet, Product.brand_id == Outlet.brand_id)
            .where(Outlet.id == outlet_id, Product.deleted_at.is_(None))
        )).scalars().all()
        own_names = set(own_products)

        matches = [b for b in hb.insight_data["benchmarks"] if b["product"] in own_names]
        if matches:
            lines.append("\nHPP BENCHMARK (vs merchant lain):")
            for m in matches[:5]:
                lines.append(
                    f"- {m['product']}: HPP rata-rata Rp{m['avg_hpp']:,.0f}, "
                    f"margin rata-rata {m['avg_margin_pct']:.0f}% ({m['sample_count']} merchant)"
                )

    return "\n".join(lines)
