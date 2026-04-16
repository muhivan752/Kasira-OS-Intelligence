"""Add tab_id FK to payments table for proper tab-payment linking

Revision ID: 077
Revises: 076
Create Date: 2026-04-16 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '077'
down_revision = '076'
branch_labels = None
depends_on = None


def upgrade():
    # Add tab_id FK to payments — links payment directly to tab (not just first order)
    op.add_column('payments', sa.Column(
        'tab_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('tabs.id', ondelete='SET NULL'),
        nullable=True,
    ))
    # Index for fast tab payment lookups
    op.create_index('ix_payments_tab_id', 'payments', ['tab_id'], unique=False)


def downgrade():
    op.drop_index('ix_payments_tab_id', table_name='payments')
    op.drop_column('payments', 'tab_id')
