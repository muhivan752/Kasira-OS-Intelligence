"""outlets

Revision ID: 003
Revises: 002
Create Date: 2026-03-20 10:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE geocode_source AS ENUM ('gps', 'manual', 'gmaps')")
    op.execute("CREATE TYPE kitchen_mode AS ENUM ('off', 'print', 'display')")

    op.create_table(
        'outlets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('gmaps_place_id', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('district', sa.String(), nullable=True),
        sa.Column('province', sa.String(), nullable=True),
        sa.Column('postal_code', sa.String(), nullable=True),
        sa.Column('geocoded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('geocode_source', postgresql.ENUM('gps', 'manual', 'gmaps', name='geocode_source', create_type=False), nullable=True),
        sa.Column('location_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('delivery_radius_km', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), server_default='Asia/Jakarta', nullable=False),
        sa.Column('currency', sa.String(), server_default='IDR', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_open', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('opening_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('self_order_url_token', sa.String(), nullable=True, unique=True),
        
        # Feature Toggles (Default OFF except cash & qris)
        sa.Column('table_management_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('self_order_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('reservation_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('kitchen_mode', postgresql.ENUM('off', 'print', 'display', name='kitchen_mode', create_type=False), server_default='off', nullable=False),
        sa.Column('qris_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('cash_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('split_bill_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('tax_pb1_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('tax_ppn_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('service_charge_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('wa_receipt_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('loyalty_points_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('customer_tracking_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('pilot_otomatis_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('ai_assistant_enabled', sa.Boolean(), server_default='false', nullable=False),
        
        # Limits
        sa.Column('table_limit_override', sa.Integer(), nullable=True),
        sa.Column('product_limit_override', sa.Integer(), nullable=True),
        
        # Standard columns
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Indexes for geo queries
    op.execute("CREATE INDEX idx_outlets_location ON outlets (latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    op.execute("CREATE INDEX idx_outlets_city ON outlets (city, province) WHERE city IS NOT NULL")

def downgrade():
    op.drop_index('idx_outlets_city', table_name='outlets')
    op.drop_index('idx_outlets_location', table_name='outlets')
    op.drop_table('outlets')
    op.execute("DROP TYPE kitchen_mode")
    op.execute("DROP TYPE geocode_source")
