"""ingredients

Revision ID: 017
Revises: 016
Create Date: 2026-03-20 10:17:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE tracking_mode AS ENUM ('simple', 'detail')")
    op.execute("CREATE TYPE unit_type AS ENUM ('WEIGHT', 'VOLUME', 'COUNT', 'CUSTOM')")
    op.execute("CREATE TYPE ingredient_type AS ENUM ('recipe', 'overhead')")

    op.create_table(
        'ingredients',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('tracking_mode', postgresql.ENUM('simple', 'detail', name='tracking_mode', create_type=False), nullable=False),
        sa.Column('base_unit', sa.String(), nullable=False),
        sa.Column('unit_type', postgresql.ENUM('WEIGHT', 'VOLUME', 'COUNT', 'CUSTOM', name='unit_type', create_type=False), nullable=False),
        sa.Column('cost_per_base_unit', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('ai_setup_complete', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('ingredient_type', postgresql.ENUM('recipe', 'overhead', name='ingredient_type', create_type=False), server_default='recipe', nullable=False),
        sa.Column('overhead_cost_per_day', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('ingredients')
    op.execute("DROP TYPE ingredient_type")
    op.execute("DROP TYPE unit_type")
    op.execute("DROP TYPE tracking_mode")
