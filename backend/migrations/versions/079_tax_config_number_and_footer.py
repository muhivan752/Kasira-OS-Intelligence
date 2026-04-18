"""add tax_number and receipt_footer to outlet_tax_config

Revision ID: 079
Revises: 078
Create Date: 2026-04-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '079'
down_revision = '078'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'outlet_tax_config',
        sa.Column('tax_number', sa.String(length=30), nullable=True),
    )
    op.add_column(
        'outlet_tax_config',
        sa.Column('receipt_footer', sa.String(length=200), nullable=True),
    )


def downgrade():
    op.drop_column('outlet_tax_config', 'receipt_footer')
    op.drop_column('outlet_tax_config', 'tax_number')
