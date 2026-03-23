"""pricing_rules

Revision ID: 023
Revises: 022
Create Date: 2026-03-20 10:23:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE rule_type AS ENUM ('discount', 'happy_hour', 'buy_x_get_y')")

    op.create_table(
        'pricing_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('rule_type', postgresql.ENUM('discount', 'happy_hour', 'buy_x_get_y', name='rule_type', create_type=False), nullable=False),
        sa.Column('value', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('pricing_rules')
    op.execute("DROP TYPE rule_type")
