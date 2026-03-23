"""outlet payment setup

Revision ID: 056
Revises: 055
Create Date: 2026-03-23 07:24:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '056'
down_revision: Union[str, None] = '055'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('outlets', sa.Column('midtrans_server_key_encrypted', sa.String(), nullable=True))
    op.add_column('outlets', sa.Column('midtrans_client_key', sa.String(), nullable=True))
    op.add_column('outlets', sa.Column('midtrans_is_production', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('outlets', sa.Column('midtrans_connected_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('outlets', 'midtrans_connected_at')
    op.drop_column('outlets', 'midtrans_is_production')
    op.drop_column('outlets', 'midtrans_client_key')
    op.drop_column('outlets', 'midtrans_server_key_encrypted')