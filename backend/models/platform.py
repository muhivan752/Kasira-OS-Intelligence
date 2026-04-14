"""
Platform-wide benchmark & intelligence models.

These tables are NOT tenant-scoped — they aggregate anonymized data
across ALL merchants to provide cross-tenant insights.

Used by:
- AI context injection (merchant sees benchmark vs industry)
- Superadmin dashboard
- Scheduled aggregation jobs
"""

from sqlalchemy import Column, String, Integer, SmallInteger, Date, Numeric, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.core.database import Base


class PlatformDailyStats(Base):
    """Daily aggregated stats per outlet. Materialized nightly by cron job."""
    __tablename__ = "platform_daily_stats"

    id = Column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), nullable=False)
    stat_date = Column(Date, nullable=False)
    revenue = Column(Numeric(14, 2), server_default="0", nullable=False)
    order_count = Column(Integer, server_default="0", nullable=False)
    avg_order_value = Column(Numeric(12, 2), server_default="0", nullable=False)
    cancel_count = Column(Integer, server_default="0", nullable=False)
    orders_pos = Column(Integer, server_default="0", nullable=False)
    orders_storefront = Column(Integer, server_default="0", nullable=False)
    payments_cash = Column(Integer, server_default="0", nullable=False)
    payments_qris = Column(Integer, server_default="0", nullable=False)
    peak_hour = Column(SmallInteger, nullable=True)
    peak_hour_orders = Column(Integer, server_default="0", nullable=False)
    unique_products_sold = Column(Integer, server_default="0", nullable=False)
    tier = Column(String, nullable=True)
    # Geo columns (migration 074)
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    province = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    hourly_distribution = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class PlatformHppBenchmark(Base):
    """Weekly HPP benchmarks per product type across all merchants."""
    __tablename__ = "platform_hpp_benchmarks"

    id = Column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"), primary_key=True)
    category_name = Column(String, nullable=False)
    product_name_normalized = Column(String, nullable=False)
    stat_week = Column(Date, nullable=False)
    sample_count = Column(Integer, server_default="0", nullable=False)
    avg_hpp = Column(Numeric(12, 2), server_default="0", nullable=False)
    min_hpp = Column(Numeric(12, 2), server_default="0", nullable=False)
    max_hpp = Column(Numeric(12, 2), server_default="0", nullable=False)
    avg_price = Column(Numeric(12, 2), server_default="0", nullable=False)
    avg_margin_pct = Column(Numeric(5, 2), server_default="0", nullable=False)
    top_ingredients = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class PlatformIngredientPrice(Base):
    """Daily ingredient price index across all merchants."""
    __tablename__ = "platform_ingredient_prices"

    id = Column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"), primary_key=True)
    ingredient_name_normalized = Column(String, nullable=False)
    base_unit = Column(String, nullable=False)
    stat_date = Column(Date, nullable=False)
    sample_count = Column(Integer, server_default="0", nullable=False)
    avg_cost_per_unit = Column(Numeric(12, 2), server_default="0", nullable=False)
    min_cost = Column(Numeric(12, 2), server_default="0", nullable=False)
    max_cost = Column(Numeric(12, 2), server_default="0", nullable=False)
    median_cost = Column(Numeric(12, 2), server_default="0", nullable=False)
    wow_change_pct = Column(Numeric(6, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class PlatformInsight(Base):
    """Cached cross-tenant insights for AI injection."""
    __tablename__ = "platform_insights"

    id = Column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"), primary_key=True)
    insight_type = Column(String, nullable=False)  # hpp_benchmark, price_trend, channel_trend
    scope = Column(String, server_default="'all'", nullable=False)
    insight_data = Column(JSONB, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
