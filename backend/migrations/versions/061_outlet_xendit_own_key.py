"""outlet xendit own key

Revision ID: 061
Revises: 060
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa

revision = '061'
down_revision = '060'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    from alembic import op as _op
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('outlets')]
    if 'xendit_api_key' not in columns:
        op.add_column('outlets', sa.Column('xendit_api_key', sa.String(), nullable=True))


def downgrade():
    op.drop_column('outlets', 'xendit_api_key')
