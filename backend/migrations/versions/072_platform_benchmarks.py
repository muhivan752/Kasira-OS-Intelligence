"""Platform-wide benchmark tables for cross-tenant intelligence.

Revision ID: 072
Revises: 071
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "072"
down_revision = "071"


def upgrade() -> None:
    # 1. Daily aggregates per outlet (materialized nightly)
    op.create_table(
        "platform_daily_stats",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("outlet_id", UUID(as_uuid=True), nullable=False),
        sa.Column("stat_date", sa.Date, nullable=False),
        # Revenue
        sa.Column("revenue", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("order_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("avg_order_value", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("cancel_count", sa.Integer, server_default="0", nullable=False),
        # Channel mix
        sa.Column("orders_pos", sa.Integer, server_default="0", nullable=False),
        sa.Column("orders_storefront", sa.Integer, server_default="0", nullable=False),
        sa.Column("payments_cash", sa.Integer, server_default="0", nullable=False),
        sa.Column("payments_qris", sa.Integer, server_default="0", nullable=False),
        # Peak info
        sa.Column("peak_hour", sa.SmallInteger, nullable=True),  # WIB hour
        sa.Column("peak_hour_orders", sa.Integer, server_default="0", nullable=False),
        # Product count
        sa.Column("unique_products_sold", sa.Integer, server_default="0", nullable=False),
        # Metadata
        sa.Column("tier", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("outlet_id", "stat_date", name="uq_platform_daily_outlet_date"),
    )
    op.create_index("ix_platform_daily_tenant_date", "platform_daily_stats", ["tenant_id", "stat_date"])
    op.create_index("ix_platform_daily_date", "platform_daily_stats", ["stat_date"])

    # 2. HPP benchmarks per product category (weekly rollup)
    op.create_table(
        "platform_hpp_benchmarks",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("category_name", sa.String, nullable=False),
        sa.Column("product_name_normalized", sa.String, nullable=False),  # lowered, trimmed
        sa.Column("stat_week", sa.Date, nullable=False),  # Monday of week
        # Aggregated HPP stats
        sa.Column("sample_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("avg_hpp", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("min_hpp", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("max_hpp", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("avg_price", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("avg_margin_pct", sa.Numeric(5, 2), server_default="0", nullable=False),
        # Ingredient price trends
        sa.Column("top_ingredients", JSONB, nullable=True),  # [{name, avg_cost, trend_pct}]
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("product_name_normalized", "stat_week", name="uq_hpp_bench_product_week"),
    )
    op.create_index("ix_hpp_bench_week", "platform_hpp_benchmarks", ["stat_week"])
    op.create_index("ix_hpp_bench_category", "platform_hpp_benchmarks", ["category_name"])

    # 3. Ingredient price index (cross-tenant price tracking)
    op.create_table(
        "platform_ingredient_prices",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("ingredient_name_normalized", sa.String, nullable=False),
        sa.Column("base_unit", sa.String, nullable=False),
        sa.Column("stat_date", sa.Date, nullable=False),
        # Price stats from all merchants
        sa.Column("sample_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("avg_cost_per_unit", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("min_cost", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("max_cost", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("median_cost", sa.Numeric(12, 2), server_default="0", nullable=False),
        # Week-over-week change
        sa.Column("wow_change_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("ingredient_name_normalized", "base_unit", "stat_date", name="uq_ing_price_name_unit_date"),
    )
    op.create_index("ix_ing_price_date", "platform_ingredient_prices", ["stat_date"])
    op.create_index("ix_ing_price_name", "platform_ingredient_prices", ["ingredient_name_normalized"])

    # 4. Platform-wide insights cache (for AI injection)
    op.create_table(
        "platform_insights",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("insight_type", sa.String, nullable=False),  # hpp_benchmark, price_trend, channel_trend, peak_pattern
        sa.Column("scope", sa.String, server_default="'all'", nullable=False),  # all, category:Minuman, geo:medan
        sa.Column("insight_data", JSONB, nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_insights_type_valid", "platform_insights", ["insight_type", "valid_until"])


def downgrade() -> None:
    op.drop_table("platform_insights")
    op.drop_table("platform_ingredient_prices")
    op.drop_table("platform_hpp_benchmarks")
    op.drop_table("platform_daily_stats")
