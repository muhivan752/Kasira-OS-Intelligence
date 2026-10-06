"""Bind HPP conversations to the permissions used to create them."""
from alembic import op
import sqlalchemy as sa

revision = "115"
down_revision = "114"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("hpp_setup_sessions", sa.Column("access_version", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("hpp_setup_sessions", "access_version")
