"""shifts

Revision ID: 023b
Revises: 023
Create Date: 2026-03-20 10:23:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '023b'
down_revision = '023'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE shift_status AS ENUM ('open', 'closed')")

    op.create_table(
        'shifts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', postgresql.ENUM('open', 'closed', name='shift_status', create_type=False), server_default='open', nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('starting_cash', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('ending_cash', sa.Numeric(12, 2), nullable=True),
        sa.Column('expected_ending_cash', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('shifts')
    op.execute("DROP TYPE shift_status")
