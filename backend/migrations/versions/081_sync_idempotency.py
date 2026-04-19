"""add sync_idempotency_keys table untuk dedup offline sync retry

Revision ID: 081
Revises: 080
Create Date: 2026-04-19

Security audit CRITICAL #6 fix: `POST /sync/` saat ini tidak enforce
idempotency — Flutter retry saat network flaky = duplicate stock deduct
(offline order di-push 2x karena response timeout bikin client retry).

Table ini track idempotency_key per tenant. Atomic `INSERT ON CONFLICT
DO NOTHING RETURNING` di handler = race-safe claim. Kalau claimed =
first request, proses push. Kalau hit (claimed by earlier request) =
skip push tapi tetap jalan pull (stateless by last_sync_hlc).

Composite PK (tenant_id, key) untuk tenant-scoped uniqueness. RLS enabled
konsisten dgn Migration 069 pattern.

Retention: manual sekarang (TRUNCATE sesekali atau cron DELETE WHERE
processed_at < NOW() - 7 days). Index di processed_at untuk cleanup
efisien nanti.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '081'
down_revision = '080'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sync_idempotency_keys',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('response_hlc', sa.String(length=200), nullable=True),
        sa.Column(
            'processed_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('tenant_id', 'key', name='pk_sync_idempotency_keys'),
    )
    op.create_index(
        'ix_sync_idempotency_processed',
        'sync_idempotency_keys',
        ['processed_at'],
    )

    # Enable RLS konsisten dgn migration 069 pattern (tenant isolation)
    op.execute("ALTER TABLE sync_idempotency_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE sync_idempotency_keys FORCE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON sync_idempotency_keys "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);"
    )


def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON sync_idempotency_keys;")
    op.drop_index('ix_sync_idempotency_processed', table_name='sync_idempotency_keys')
    op.drop_table('sync_idempotency_keys')
