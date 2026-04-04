"""outlet cover image

Revision ID: 060
Revises: 059
Create Date: 2026-04-03 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '060'
down_revision = '059'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('outlets', sa.Column('cover_image_url', sa.String(), nullable=True))


def downgrade():
    op.drop_column('outlets', 'cover_image_url')
