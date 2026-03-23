"""outlet_tax_config

Revision ID: 010
Revises: 009
Create Date: 2026-03-20 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'outlet_tax_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('pb1_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('ppn_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('pkp_registered', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('service_charge_pct', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('tax_inclusive', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('outlet_tax_config')
