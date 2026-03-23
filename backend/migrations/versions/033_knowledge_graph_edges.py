"""knowledge_graph_edges

Revision ID: 033
Revises: 032
Create Date: 2026-03-20 10:33:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'knowledge_graph_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_node_type', sa.String(), nullable=False),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_node_type', sa.String(), nullable=False),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('weight', sa.Numeric(5, 4), server_default='1.0', nullable=False),
        sa.Column('metadata_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_kg_edges_source', 'knowledge_graph_edges', ['source_node_type', 'source_node_id'])
    op.create_index('ix_kg_edges_target', 'knowledge_graph_edges', ['target_node_type', 'target_node_id'])
    op.create_index('ix_kg_edges_relation', 'knowledge_graph_edges', ['relation_type'])

def downgrade():
    op.drop_table('knowledge_graph_edges')
