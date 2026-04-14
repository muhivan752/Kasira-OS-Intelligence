"""platform_geo_columns

Revision ID: 074
Revises: 073
Create Date: 2026-04-14 08:00:00.000000

Add geo columns to platform_daily_stats for city-level aggregation.
Add hourly_distribution JSONB for 24h breakdown.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '074'
down_revision = '073'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('platform_daily_stats', sa.Column('city', sa.String(), nullable=True))
    op.add_column('platform_daily_stats', sa.Column('district', sa.String(), nullable=True))
    op.add_column('platform_daily_stats', sa.Column('province', sa.String(), nullable=True))
    op.add_column('platform_daily_stats', sa.Column('business_type', sa.String(), nullable=True))
    op.add_column('platform_daily_stats', sa.Column('hourly_distribution', postgresql.JSONB(), nullable=True))

    op.create_index('idx_platform_daily_city_date', 'platform_daily_stats', ['city', 'stat_date'],
                     postgresql_where=sa.text("city IS NOT NULL"))
    op.create_index('idx_platform_daily_province', 'platform_daily_stats', ['province'],
                     postgresql_where=sa.text("province IS NOT NULL"))


def downgrade():
    op.drop_index('idx_platform_daily_province', table_name='platform_daily_stats')
    op.drop_index('idx_platform_daily_city_date', table_name='platform_daily_stats')
    op.drop_column('platform_daily_stats', 'hourly_distribution')
    op.drop_column('platform_daily_stats', 'business_type')
    op.drop_column('platform_daily_stats', 'province')
    op.drop_column('platform_daily_stats', 'district')
    op.drop_column('platform_daily_stats', 'city')
