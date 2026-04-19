"""Xendit reliability: pending_manual_check status + webhook dedup table

Revision ID: 083
Revises: 082
Create Date: 2026-04-19

Fix CRITICAL #12 Xendit retry + webhook idempotency:

1. ALTER TYPE payment_status ADD VALUE 'pending_manual_check'
   — fail-safe state saat Xendit retry exhausted. Beda dari 'failed'
   (terminal) — admin perlu verify manual via dashboard Xendit atau
   reconcile cron pake get_qr_code_status.

2. CREATE TABLE xendit_webhook_events
   — dedup table webhook callback. PRIMARY KEY (callback_id) atomic
   INSERT ON CONFLICT DO NOTHING = race-safe idempotent webhook. Kalau
   Xendit kirim callback sama 2x (retry), kita process sekali.
   Include payload_hash untuk audit trail + tenant_id untuk RLS.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '083'
down_revision = '082'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add payment_status enum value — ALTER TYPE ... ADD VALUE harus di luar
    # transaction di beberapa PG version. Alembic 1.13+ handle ini otomatis
    # via op.execute dgn COMMIT marker.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'pending_manual_check';"
        )

    # 2. Webhook dedup table — simple dedup by callback event id
    op.create_table(
        'xendit_webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('callback_id', sa.String(length=128), nullable=False, unique=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=True),
        sa.Column('payload_hash', sa.String(length=64), nullable=True),  # SHA256 hex
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'processed_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index(
        'ix_xendit_webhook_events_processed',
        'xendit_webhook_events',
        ['processed_at'],
    )
    op.create_index(
        'ix_xendit_webhook_events_external',
        'xendit_webhook_events',
        ['external_id'],
    )

    # RLS tenant isolation (konsisten migration 069 pattern) — webhook admin
    # perspective tenant_id bisa null (unknown reference), jadi policy
    # tolerate null + current_setting match.
    op.execute("ALTER TABLE xendit_webhook_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE xendit_webhook_events FORCE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON xendit_webhook_events "
        "USING ("
        "  tenant_id IS NULL OR "
        "  tenant_id = current_setting('app.current_tenant_id', true)::uuid"
        ");"
    )


def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON xendit_webhook_events;")
    op.drop_index('ix_xendit_webhook_events_external', table_name='xendit_webhook_events')
    op.drop_index('ix_xendit_webhook_events_processed', table_name='xendit_webhook_events')
    op.drop_table('xendit_webhook_events')
    # Note: PostgreSQL doesn't support removing enum values cleanly.
    # The 'pending_manual_check' value will remain in payment_status enum.
    # This is acceptable — no data loss; value just becomes unused.
