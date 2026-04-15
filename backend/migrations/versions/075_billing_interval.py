"""billing_interval

Revision ID: 075
Revises: 074
Create Date: 2026-04-15 21:30:00.000000

Add billing_interval column to tenants (monthly/annual).
"""
from alembic import op
import sqlalchemy as sa


revision = '075'
down_revision = '074'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('billing_interval', sa.String(), server_default='monthly', nullable=False))


def downgrade() -> None:
    op.drop_column('tenants', 'billing_interval')
