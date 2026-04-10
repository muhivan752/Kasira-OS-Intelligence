"""add unique partial index to prevent duplicate open shifts

Revision ID: 063
Revises: 062
Create Date: 2026-04-10 10:00:00.000000

"""
from alembic import op

# revision identifiers
revision = '063'
down_revision = '062'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Unique partial index: hanya 1 shift open per user per outlet
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_shift_one_open_per_user_outlet
        ON shifts (outlet_id, user_id)
        WHERE status = 'open' AND deleted_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uix_shift_one_open_per_user_outlet")
