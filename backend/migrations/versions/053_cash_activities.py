"""cash activities

Revision ID: 053_cash_activities
Revises: 052_missing_row_versions
Create Date: 2026-03-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '053_cash_activities'
down_revision = '052_missing_row_versions'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create enum type
    op.execute("CREATE TYPE cash_activity_type AS ENUM ('income', 'expense')")

    # Create table
    op.create_table(
        'cash_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_type', postgresql.ENUM('income', 'expense', name='cash_activity_type', create_type=False), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('cash_activities')
    op.execute("DROP TYPE cash_activity_type")
