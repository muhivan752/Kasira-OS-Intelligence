"""ingredient_units

Revision ID: 018
Revises: 017
Create Date: 2026-03-20 10:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'ingredient_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('unit_name', sa.String(), nullable=False),
        sa.Column('conversion_to_base', sa.Float(), nullable=False),
        sa.Column('is_purchase_unit', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_display_unit', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('unit_type', postgresql.ENUM('WEIGHT', 'VOLUME', 'COUNT', 'CUSTOM', name='unit_type', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('ingredient_units')
