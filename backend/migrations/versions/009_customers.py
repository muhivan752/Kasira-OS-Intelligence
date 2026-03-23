"""customers

Revision ID: 009
Revises: 008
Create Date: 2026-03-20 10:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE consent_source AS ENUM ('self_order', 'kasir_input', 'profile')")

    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False), # Encrypted AES-256
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('total_visits', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_spent', sa.Numeric(12, 2), server_default='0', nullable=False),
        sa.Column('first_visit_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_visit_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('phone_hmac', sa.String(), nullable=False), # For searching
        sa.Column('email_encrypted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('wa_marketing_consent', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consent_source', postgresql.ENUM('self_order', 'kasir_input', 'profile', name='consent_source', create_type=False), nullable=True),
        sa.Column('data_retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Unique constraint on tenant_id and phone_hmac (since phone is encrypted)
    op.create_unique_constraint('uq_customers_tenant_phone_hmac', 'customers', ['tenant_id', 'phone_hmac'])

def downgrade():
    op.drop_table('customers')
    op.execute("DROP TYPE consent_source")
