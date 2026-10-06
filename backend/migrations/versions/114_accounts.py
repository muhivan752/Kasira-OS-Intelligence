"""Password identities, revocable device sessions and single-use challenges."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from backend.core.config import settings

revision = "114"
down_revision = "113"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("uq_account_access_request", "audit_log", [sa.text("(after_state->>'client_request_id')")],
        unique=True, postgresql_where=sa.text("entity = 'account_access' AND after_state->>'client_request_id' IS NOT NULL"))
    op.add_column("tenants", sa.Column("login_username", sa.String(64)))
    op.create_unique_constraint("uq_tenant_login_username", "tenants", ["login_username"])
    op.create_check_constraint("ck_tenant_login_username", "tenants", "login_username IS NULL OR login_username ~ '^[a-z0-9][a-z0-9_-]{2,63}$'")
    op.alter_column("users", "phone", nullable=True)
    op.add_column("users", sa.Column("login_username", sa.String(64)))
    op.add_column("users", sa.Column("password_hash", sa.String()))
    op.add_column("users", sa.Column("credential_version", sa.Integer(), server_default="0", nullable=False))
    op.create_unique_constraint("uq_user_login_username", "users", ["tenant_id", "login_username"])
    op.create_unique_constraint("uq_user_tenant_id", "users", ["tenant_id", "id"])
    op.create_check_constraint("ck_user_login_username", "users", "login_username IS NULL OR login_username ~ '^[a-z0-9][a-z0-9_-]{2,63}$'")
    op.create_check_constraint("ck_user_credential_version", "users", "credential_version >= 0")
    op.add_column("sessions", sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id")))
    op.add_column("sessions", sa.Column("credential_version", sa.Integer(), server_default="0", nullable=False))
    op.add_column("sessions", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE sessions SET tenant_id = users.tenant_id FROM users WHERE sessions.user_id = users.id")
    op.create_foreign_key("fk_session_tenant_user", "sessions", "users", ["tenant_id", "user_id"], ["tenant_id", "id"])
    op.create_index("ix_session_user_live", "sessions", ["tenant_id", "user_id", "revoked_at"])
    op.create_table("account_challenges",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("credential_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        sa.CheckConstraint("purpose IN ('activation','recovery')", name="ck_account_challenge_purpose"))
    op.create_index("ix_account_challenge_user", "account_challenges", ["tenant_id", "user_id"])
    for table in ("sessions", "account_challenges"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        scope = "current_setting('app.current_tenant_id', true) = '' OR tenant_id::text = current_setting('app.current_tenant_id', true)"
        if table == "sessions":
            op.execute("DROP POLICY tenant_isolation ON sessions")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING ({scope}) WITH CHECK ({scope})")
    role = settings.POSTGRES_APP_USER
    if role and role != settings.POSTGRES_USER:
        conn = op.get_bind()
        found = conn.execute(sa.text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=:role"), {"role": role}).first()
        if found:
            if found.rolsuper or found.rolbypassrls:
                raise RuntimeError("Account application role must enforce RLS")
            quoted = conn.dialect.identifier_preparer.quote_identifier(role)
            op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON sessions,account_challenges TO {quoted}")


def downgrade():
    # Refuse rollback before dropping anything when password-only identities exist.
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM users WHERE phone IS NULL)")).scalar():
        raise RuntimeError("Restore real verified phones before downgrading password-only accounts")
    op.drop_index("uq_account_access_request", table_name="audit_log")
    op.drop_table("account_challenges")
    op.execute("DROP POLICY tenant_isolation ON sessions")
    scope = "current_setting('app.current_tenant_id', true) = '' OR outlet_id IN (SELECT id FROM outlets WHERE tenant_id::text = current_setting('app.current_tenant_id', true))"
    op.execute(f"CREATE POLICY tenant_isolation ON sessions USING ({scope})")
    op.drop_index("ix_session_user_live", table_name="sessions")
    op.drop_constraint("fk_session_tenant_user", "sessions", type_="foreignkey")
    for column in ("expires_at", "credential_version", "tenant_id"):
        op.drop_column("sessions", column)
    op.drop_constraint("ck_user_login_username", "users", type_="check")
    op.drop_constraint("ck_user_credential_version", "users", type_="check")
    op.drop_constraint("uq_user_login_username", "users", type_="unique")
    op.drop_constraint("uq_user_tenant_id", "users", type_="unique")
    for column in ("credential_version", "password_hash", "login_username"):
        op.drop_column("users", column)
    op.alter_column("users", "phone", nullable=False)
    op.drop_constraint("ck_tenant_login_username", "tenants", type_="check")
    op.drop_constraint("uq_tenant_login_username", "tenants", type_="unique")
    op.drop_column("tenants", "login_username")
