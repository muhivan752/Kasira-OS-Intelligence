"""add tax_pct and service_charge_enabled to outlet_tax_config

Revision ID: 067
Revises: 066
Create Date: 2026-04-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '067'
down_revision = '066'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('outlet_tax_config', sa.Column('tax_pct', sa.Float(), server_default='10.0', nullable=False))
    op.add_column('outlet_tax_config', sa.Column('service_charge_enabled', sa.Boolean(), server_default='false', nullable=False))

def downgrade():
    op.drop_column('outlet_tax_config', 'tax_pct')
    op.drop_column('outlet_tax_config', 'service_charge_enabled')
