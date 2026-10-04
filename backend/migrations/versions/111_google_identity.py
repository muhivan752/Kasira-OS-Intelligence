"""Google identity shared with the configured Firebase project.

Revision ID: 111
Revises: 110
"""
from alembic import op
import sqlalchemy as sa

revision = "111"
down_revision = "110"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("google_project_id", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("google_uid", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("google_email", sa.String(320), nullable=True))
    op.create_unique_constraint("uq_users_google_identity", "users", ["google_project_id", "google_uid"])
    op.create_check_constraint("ck_users_google_identity_pair", "users", "(google_uid IS NULL) = (google_project_id IS NULL)")


def downgrade():
    op.drop_constraint("ck_users_google_identity_pair", "users", type_="check")
    op.drop_constraint("uq_users_google_identity", "users", type_="unique")
    op.drop_column("users", "google_email")
    op.drop_column("users", "google_uid")
    op.drop_column("users", "google_project_id")
