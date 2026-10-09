"""Jadwal hapus akun pemilik (masa tenggang 30 hari).

Baris lama: NULL = tidak sedang dijadwalkan dihapus. Itu memang keadaan
semua tenant sebelum fitur ini ada, jadi default-nya tidak menulis data palsu.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "116"
down_revision = "115"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("deletion_requested_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_tenants_deletion_due", "tenants", ["deletion_scheduled_at"],
                    postgresql_where=sa.text("deletion_scheduled_at IS NOT NULL AND deleted_at IS NULL"))


def downgrade():
    op.drop_index("ix_tenants_deletion_due", table_name="tenants")
    op.drop_column("tenants", "deletion_requested_by")
    op.drop_column("tenants", "deletion_scheduled_at")
