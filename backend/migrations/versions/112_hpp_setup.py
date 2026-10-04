"""Durable HPP conversations and ingredient cost precision."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "112"
down_revision = "111"
branch_labels = None
depends_on = None


def base_columns():
    return [sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True))]


def upgrade():
    op.alter_column("ingredients", "cost_per_base_unit", type_=sa.Numeric(18, 8), existing_type=sa.Numeric(12, 2))
    op.add_column("recipes", sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default="false"))
    op.create_table("hpp_setup_sessions", *base_columns(),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("outlet_id", UUID(as_uuid=True), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mode", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False), sa.Column("draft", JSONB()),
        sa.Column("preview", JSONB()), sa.Column("result", JSONB()),
        sa.Column("pending_request", UUID(as_uuid=True)), sa.Column("pending_until", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()))
    op.create_table("hpp_setup_turns", *base_columns(),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("hpp_setup_sessions.id"), nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(), nullable=False), sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reply", sa.Text()), sa.Column("usage", JSONB()),
        sa.UniqueConstraint("session_id", "request_id", name="uq_hpp_setup_request"))
    op.create_index("ix_hpp_setup_owner", "hpp_setup_sessions", ["tenant_id", "outlet_id", "user_id", "updated_at"])
    op.create_index("ix_hpp_setup_turns_session", "hpp_setup_turns", ["session_id", "created_at"])
    for table in ("hpp_setup_sessions", "hpp_setup_turns"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING (current_setting('app.current_tenant_id', true) = '' OR tenant_id::text = current_setting('app.current_tenant_id', true))")


def downgrade():
    op.drop_table("hpp_setup_turns")
    op.drop_table("hpp_setup_sessions")
    op.drop_column("recipes", "is_estimated")
    op.alter_column("ingredients", "cost_per_base_unit", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(18, 8))
