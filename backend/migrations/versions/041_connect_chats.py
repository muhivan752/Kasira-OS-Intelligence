"""connect_chats

Revision ID: 041
Revises: 040
Create Date: 2026-03-20 10:41:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '041'
down_revision = '040'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TYPE chat_direction AS ENUM ('inbound', 'outbound')")
    op.execute("CREATE TYPE chat_status AS ENUM ('sent', 'delivered', 'read', 'failed')")

    op.create_table(
        'connect_chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('connect_outlet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connect_outlets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connect_customer_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connect_customer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('direction', postgresql.ENUM('inbound', 'outbound', name='chat_direction', create_type=False), nullable=False),
        sa.Column('message_encrypted', sa.Text(), nullable=False, comment='AES-256 encrypted'),
        sa.Column('status', postgresql.ENUM('sent', 'delivered', 'read', 'failed', name='chat_status', create_type=False), server_default='sent', nullable=False),
        sa.Column('external_message_id', sa.String(), nullable=True),
        sa.Column('metadata_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_connect_chats_external_id', 'connect_chats', ['external_message_id'])
    op.create_index('ix_connect_chats_customer_profile', 'connect_chats', ['connect_customer_profile_id'])

def downgrade():
    op.drop_table('connect_chats')
    op.execute("DROP TYPE chat_status")
    op.execute("DROP TYPE chat_direction")
