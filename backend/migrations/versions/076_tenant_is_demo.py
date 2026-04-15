"""tenant_is_demo

Revision ID: 076
Revises: 075
Create Date: 2026-04-15 22:30:00.000000

Add is_demo flag to tenants — exclude test accounts from intelligence.
"""
from alembic import op
import sqlalchemy as sa


revision = '076'
down_revision = '075'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('is_demo', sa.Boolean(), server_default='false', nullable=False))
    # Mark existing test tenants
    op.execute("""
        UPDATE tenants SET is_demo = true
        WHERE name IN ('Kasira Coffee', 'B coffee', 'Dita Coffee', 'Warung Demo')
    """)


def downgrade() -> None:
    op.drop_column('tenants', 'is_demo')
