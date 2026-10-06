"""Employee roster, work schedules and recorded attendance."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from backend.core.config import settings

revision = "113"
down_revision = "112"
branch_labels = None
depends_on = None


def common():
    return [sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("outlet_id", UUID(as_uuid=True), sa.ForeignKey("outlets.id"), nullable=False),
            sa.Column("row_version", sa.Integer(), nullable=False)]


def upgrade():
    op.create_table("hr_employees", *common(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("code", sa.String(30), nullable=False), sa.Column("name", sa.String(120), nullable=False),
        sa.Column("position", sa.String(100), nullable=False), sa.Column("phone", sa.String(40)),
        sa.Column("started_on", sa.Date(), nullable=False), sa.Column("ended_on", sa.Date()),
        sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("tenant_id", "id", name="uq_hr_employee_tenant_id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_hr_employee_code"),
        sa.CheckConstraint("ended_on IS NULL OR ended_on >= started_on", name="ck_hr_employment_dates"))
    op.create_index("ix_hr_employee_outlet", "hr_employees", ["tenant_id", "outlet_id"])
    op.create_index("uq_hr_employee_user", "hr_employees", ["tenant_id", "user_id"], unique=True,
                    postgresql_where=sa.text("user_id IS NOT NULL AND deleted_at IS NULL"))
    op.create_table("hr_schedules", *common(),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False), sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False), sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["tenant_id", "employee_id"], ["hr_employees.tenant_id", "hr_employees.id"]),
        sa.CheckConstraint("ends_at > starts_at AND ends_at <= starts_at + interval '24 hours'", name="ck_hr_schedule_window"))
    op.create_table("hr_attendance", *common(),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False), sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False), sa.Column("clock_in", sa.DateTime(timezone=True)),
        sa.Column("clock_out", sa.DateTime(timezone=True)), sa.Column("reason", sa.Text()),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("recorded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "employee_id"], ["hr_employees.tenant_id", "hr_employees.id"]),
        sa.CheckConstraint("(status = 'hadir' AND clock_in IS NOT NULL AND (clock_out IS NULL OR clock_out >= clock_in)) OR (status IN ('izin','sakit','cuti','libur') AND clock_in IS NULL AND clock_out IS NULL)", name="ck_hr_attendance_times"),
        sa.CheckConstraint("source IN ('manual','self')", name="ck_hr_attendance_source"))
    for table, label in (("hr_schedules", "schedule"), ("hr_attendance", "attendance")):
        op.create_index(f"ix_hr_{label}_period", table, ["tenant_id", "outlet_id", "work_date"])
        op.create_index(f"uq_hr_{label}_day", table, ["tenant_id", "employee_id", "work_date"], unique=True,
                        postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_hr_attendance_open", "hr_attendance", ["tenant_id", "employee_id"], unique=True,
                    postgresql_where=sa.text("deleted_at IS NULL AND status = 'hadir' AND clock_out IS NULL"))
    for table in ("hr_employees", "hr_schedules", "hr_attendance"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        scope = "current_setting('app.current_tenant_id', true) = '' OR tenant_id::text = current_setting('app.current_tenant_id', true)"
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING ({scope}) WITH CHECK ({scope})")
    role = settings.POSTGRES_APP_USER
    if role and role != settings.POSTGRES_USER:
        conn = op.get_bind()
        existing = conn.execute(sa.text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = :role"), {"role": role}).first()
        if existing:
            if existing.rolsuper or existing.rolbypassrls:
                raise RuntimeError("HRIS requires the existing application role to enforce RLS")
            quoted = conn.dialect.identifier_preparer.quote_identifier(role)
            op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON hr_employees,hr_schedules,hr_attendance TO {quoted}")


def downgrade():
    op.drop_table("hr_attendance")
    op.drop_table("hr_schedules")
    op.drop_table("hr_employees")
