"""migrate payment xenplatform

Revision ID: 057
Revises: 056
Create Date: 2026-03-29 16:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '057'
down_revision: Union[str, None] = '056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop midtrans columns
    op.drop_column('outlets', 'midtrans_server_key_encrypted')
    op.drop_column('outlets', 'midtrans_client_key')
    op.drop_column('outlets', 'midtrans_is_production')
    op.drop_column('outlets', 'midtrans_connected_at')
    
    # Add xendit columns
    op.add_column('outlets', sa.Column('xendit_business_id', sa.String(), nullable=True))
    op.add_column('outlets', sa.Column('xendit_connected_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Drop xendit columns
    op.drop_column('outlets', 'xendit_business_id')
    op.drop_column('outlets', 'xendit_connected_at')
    
    # Re-add midtrans columns
    op.add_column('outlets', sa.Column('midtrans_server_key_encrypted', sa.String(), nullable=True))
    op.add_column('outlets', sa.Column('midtrans_client_key', sa.String(), nullable=True))
    op.add_column('outlets', sa.Column('midtrans_is_production', sa.Boolean(), server_default='False'))
    op.add_column('outlets', sa.Column('midtrans_connected_at', sa.DateTime(timezone=True), nullable=True))
