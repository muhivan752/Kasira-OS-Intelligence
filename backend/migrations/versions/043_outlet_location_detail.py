"""outlet_location_detail

Revision ID: 043
Revises: 042
Create Date: 2026-03-20 10:43:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'outlet_location_detail',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=True),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=True),
        sa.Column('address_line_1', sa.String(), nullable=False),
        sa.Column('address_line_2', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('postal_code', sa.String(), nullable=True),
        sa.Column('country', sa.String(), server_default='Indonesia', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.UniqueConstraint('outlet_id', name='uq_outlet_location_detail_outlet')
    )

def downgrade():
    op.drop_table('outlet_location_detail')
