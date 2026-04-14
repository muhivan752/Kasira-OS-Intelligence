"""Layer 4: Embedding infrastructure — resize vector column, add HNSW index

Revision ID: 073
Revises: 072
"""

from alembic import op

revision = "073"
down_revision = "072"


def upgrade():
    # 1. Resize products.embedding from vector(1536) to vector(512) for voyage-3-lite
    #    All values are NULL so safe to drop and recreate
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE products ADD COLUMN embedding vector(512)")

    # 2. HNSW index for fast cosine similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_embedding_hnsw
        ON products
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # 3. Add embedding column to platform_insights for semantic retrieval
    op.execute("ALTER TABLE platform_insights ADD COLUMN IF NOT EXISTS embedding vector(512)")

    # 4. Index on platform_insights embedding
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_platform_insights_embedding_hnsw
        ON platform_insights
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_platform_insights_embedding_hnsw")
    op.execute("ALTER TABLE platform_insights DROP COLUMN IF EXISTS embedding")
    op.execute("DROP INDEX IF EXISTS idx_products_embedding_hnsw")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE products ADD COLUMN embedding vector(1536)")
