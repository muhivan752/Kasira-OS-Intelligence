"""Add stock_mode to outlets and row_version to ingredients

Revision ID: 065
Revises: 064
Create Date: 2026-04-11 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '065'
down_revision = '064'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE stock_mode_type AS ENUM ('simple', 'recipe')")
    op.add_column('outlets', sa.Column('stock_mode', sa.Enum('simple', 'recipe', name='stock_mode_type', create_type=False), server_default='simple', nullable=False))

def downgrade():
    op.drop_column('outlets', 'stock_mode')
    op.execute("DROP TYPE stock_mode_type")
