"""Saran Selaris: satu baris per saran proaktif (docs/SARAN_DESIGN.md).

Tabel baru, tidak numpang `notifications`: notifikasi itu kabar satu arah,
saran punya siklus hidup (diterapkan, diabaikan, dibatalkan, kedaluwarsa).
Tidak ada baris lama, jadi tidak ada default yang menulis data palsu.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from backend.core.config import settings

revision = "117"
down_revision = "116"
branch_labels = None
depends_on = None

KINDS = ("stock_low", "ingredient_price_up", "thin_margin", "recipe_missing")
STATUSES = ("open", "applied", "skipped", "undone", "expired")


def upgrade():
    op.create_table(
        "suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outlet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outlets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dedup_key", sa.String(120), nullable=False),
        sa.Column("data_hash", sa.String(64), nullable=False),
        sa.Column("facts", postgresql.JSONB(), nullable=False),
        sa.Column("proposal", postgresql.JSONB(), nullable=False),
        sa.Column("impact_rp", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("urgent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("visibility", sa.String(8), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skip_reason", sa.String(40), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("undo", postgresql.JSONB(), nullable=True),
        sa.Column("hpp_session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("hpp_setup_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('" + "','".join(KINDS) + "')", name="ck_suggestions_kind"),
        sa.CheckConstraint("status IN ('" + "','".join(STATUSES) + "')", name="ck_suggestions_status"),
        sa.CheckConstraint("visibility IN ('hpp','stock')", name="ck_suggestions_visibility"),
    )
    # Satu saran terbuka per subjek. Upsert WAJIB membawa predikat yang sama
    # (CLAUDE.md: ON CONFLICT dengan index parsial).
    op.create_index("uq_suggestions_open", "suggestions", ["tenant_id", "outlet_id", "dedup_key"],
                    unique=True, postgresql_where=sa.text("status = 'open'"))
    op.create_index("ix_suggestions_outlet", "suggestions", ["tenant_id", "outlet_id", "status", "created_at"])
    op.create_index("ix_suggestions_history", "suggestions", ["tenant_id", "outlet_id", "dedup_key", "created_at"])
    op.execute("ALTER TABLE suggestions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE suggestions FORCE ROW LEVEL SECURITY")
    scope = "current_setting('app.current_tenant_id', true) = '' OR tenant_id::text = current_setting('app.current_tenant_id', true)"
    op.execute(f"CREATE POLICY tenant_isolation ON suggestions USING ({scope}) WITH CHECK ({scope})")
    role = settings.POSTGRES_APP_USER
    if role and role != settings.POSTGRES_USER:
        conn = op.get_bind()
        existing = conn.execute(sa.text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = :role"), {"role": role}).first()
        if existing:
            if existing.rolsuper or existing.rolbypassrls:
                raise RuntimeError("suggestions requires the application role to enforce RLS")
            quoted = conn.dialect.identifier_preparer.quote_identifier(role)
            op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON suggestions TO {quoted}")


def downgrade():
    op.drop_table("suggestions")
