"""Upgrade reservations: add fields, reservation_settings, tables floor_section

Revision ID: 064
Revises: 063
Create Date: 2026-04-11 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '064'
down_revision = '063'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- tables: add floor_section ---
    op.add_column('tables', sa.Column('floor_section', sa.String(50), nullable=True))

    # --- reservations: add new columns ---
    # Make customer_id nullable (storefront booking tanpa akun customer)
    op.alter_column('reservations', 'customer_id', existing_type=sa.UUID(), nullable=True)
    # Make reservation_time nullable (replaced by reservation_date + start_time)
    op.alter_column('reservations', 'reservation_time', existing_type=sa.DateTime(timezone=True), nullable=True)

    # Split reservation_time into date + start_time + end_time
    op.add_column('reservations', sa.Column('reservation_date', sa.Date(), nullable=True))
    op.add_column('reservations', sa.Column('start_time', sa.Time(), nullable=True))
    op.add_column('reservations', sa.Column('end_time', sa.Time(), nullable=True))

    # Customer info (denormalized — no customer account needed)
    op.add_column('reservations', sa.Column('customer_name', sa.String(100), nullable=True))
    op.add_column('reservations', sa.Column('customer_phone', sa.String(20), nullable=True))

    # Tenant scoping
    op.add_column('reservations', sa.Column('tenant_id', sa.UUID(), nullable=True))

    # Deposit
    op.add_column('reservations', sa.Column('deposit_amount', sa.Numeric(15, 2), nullable=True))
    op.add_column('reservations', sa.Column('deposit_payment_id', sa.UUID(), nullable=True))

    # Source & timestamps
    op.add_column('reservations', sa.Column('source', sa.String(20), server_default='manual', nullable=False))
    op.add_column('reservations', sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('reservations', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))

    # Add no_show and seated to reservation_status enum
    op.execute("ALTER TYPE reservation_status ADD VALUE IF NOT EXISTS 'seated'")
    op.execute("ALTER TYPE reservation_status ADD VALUE IF NOT EXISTS 'no_show'")

    # Migrate existing data: copy reservation_time to reservation_date + start_time
    op.execute("""
        UPDATE reservations
        SET reservation_date = reservation_time::date,
            start_time = reservation_time::time,
            end_time = (reservation_time + interval '2 hours')::time
        WHERE reservation_time IS NOT NULL
    """)

    # Foreign keys
    op.create_foreign_key(
        'fk_reservations_tenant', 'reservations', 'tenants',
        ['tenant_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_reservations_deposit_payment', 'reservations', 'payments',
        ['deposit_payment_id'], ['id'], ondelete='SET NULL'
    )

    # Index for querying by date
    op.create_index('ix_reservations_outlet_date', 'reservations', ['outlet_id', 'reservation_date'])

    # --- reservation_settings ---
    op.create_table(
        'reservation_settings',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('outlet_id', sa.UUID(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('slot_duration_minutes', sa.Integer(), server_default='120', nullable=False),
        sa.Column('max_advance_days', sa.Integer(), server_default='30', nullable=False),
        sa.Column('min_advance_hours', sa.Integer(), server_default='2', nullable=False),
        sa.Column('require_deposit', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deposit_amount', sa.Numeric(15, 2), server_default='0', nullable=False),
        sa.Column('auto_confirm', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('opening_hour', sa.Time(), server_default=sa.text("'08:00'::time"), nullable=False),
        sa.Column('closing_hour', sa.Time(), server_default=sa.text("'22:00'::time"), nullable=False),
        sa.Column('max_reservations_per_slot', sa.Integer(), server_default='10', nullable=False),
        sa.Column('reminder_hours_before', sa.Integer(), server_default='2', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['outlet_id'], ['outlets.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('outlet_id', name='uq_reservation_settings_outlet'),
    )


def downgrade() -> None:
    op.drop_table('reservation_settings')
    op.drop_index('ix_reservations_outlet_date', table_name='reservations')
    op.drop_constraint('fk_reservations_deposit_payment', 'reservations', type_='foreignkey')
    op.drop_constraint('fk_reservations_tenant', 'reservations', type_='foreignkey')
    op.drop_column('reservations', 'cancelled_at')
    op.drop_column('reservations', 'confirmed_at')
    op.drop_column('reservations', 'source')
    op.drop_column('reservations', 'deposit_payment_id')
    op.drop_column('reservations', 'deposit_amount')
    op.drop_column('reservations', 'tenant_id')
    op.drop_column('reservations', 'customer_phone')
    op.drop_column('reservations', 'customer_name')
    op.drop_column('reservations', 'end_time')
    op.drop_column('reservations', 'start_time')
    op.drop_column('reservations', 'reservation_date')
    op.alter_column('reservations', 'customer_id', existing_type=sa.UUID(), nullable=False)
    op.drop_column('tables', 'floor_section')
