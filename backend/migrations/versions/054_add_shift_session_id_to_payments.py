"""add shift_session_id to payments

Revision ID: 053
Revises: 052
Create Date: 2026-03-22 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '054_add_shift_session_id_to_payments'
down_revision = '053_cash_activities'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('payments', sa.Column('shift_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True))

def downgrade():
    op.drop_column('payments', 'shift_session_id')
