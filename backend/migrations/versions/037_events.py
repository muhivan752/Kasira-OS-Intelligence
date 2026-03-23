"""events

Revision ID: 037
Revises: 036
Create Date: 2026-03-20 10:37:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None

def upgrade():
    # Create the partitioned table
    op.execute("""
        CREATE TABLE events (
            id UUID DEFAULT gen_random_uuid() NOT NULL,
            outlet_id UUID NOT NULL,
            stream_id VARCHAR NOT NULL,
            event_type VARCHAR NOT NULL,
            event_data JSONB,
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            PRIMARY KEY (id, outlet_id)
        ) PARTITION BY HASH (outlet_id);
    """)

    # Create default partitions (e.g., 4 partitions for hash partitioning)
    op.execute("CREATE TABLE events_p0 PARTITION OF events FOR VALUES WITH (MODULUS 4, REMAINDER 0);")
    op.execute("CREATE TABLE events_p1 PARTITION OF events FOR VALUES WITH (MODULUS 4, REMAINDER 1);")
    op.execute("CREATE TABLE events_p2 PARTITION OF events FOR VALUES WITH (MODULUS 4, REMAINDER 2);")
    op.execute("CREATE TABLE events_p3 PARTITION OF events FOR VALUES WITH (MODULUS 4, REMAINDER 3);")

    # Create indexes on the partitioned table
    op.execute("CREATE INDEX ix_events_outlet_id ON events (outlet_id);")
    op.execute("CREATE INDEX ix_events_stream_id ON events (stream_id);")
    op.execute("CREATE INDEX ix_events_event_type ON events (event_type);")
    op.execute("CREATE INDEX ix_events_created_at ON events (created_at);")

def downgrade():
    op.execute("DROP TABLE events CASCADE;")
