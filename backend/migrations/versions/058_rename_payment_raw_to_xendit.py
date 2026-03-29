"""rename midtrans_raw to xendit_raw in payments

Revision ID: 058
Revises: 057
Create Date: 2026-03-29 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text


# revision identifiers, used by Alembic.
revision: str = '058'
down_revision: Union[str, None] = '057'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename kolom midtrans_raw → xendit_raw (Golden Rule #44: JSONB WAJIB disimpan untuk debug/dispute)
    op.alter_column('payments', 'midtrans_raw', new_column_name='xendit_raw')


def downgrade() -> None:
    # Rollback: kembalikan nama kolom
    op.alter_column('payments', 'xendit_raw', new_column_name='midtrans_raw')
