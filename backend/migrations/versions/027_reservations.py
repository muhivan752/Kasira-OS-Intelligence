"""reservations

Revision ID: 027
Revises: 026
Create Date: 2026-03-20 10:27:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE reservation_status AS ENUM ('pending', 'confirmed', 'cancelled', 'completed')")

    op.create_table(
        'reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reservation_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('guest_count', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'confirmed', 'cancelled', 'completed', name='reservation_status', create_type=False), server_default='pending', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_check_constraint('chk_reservations_guest_count', 'reservations', 'guest_count > 0')

def downgrade():
    op.drop_table('reservations')
    op.execute("DROP TYPE reservation_status")
