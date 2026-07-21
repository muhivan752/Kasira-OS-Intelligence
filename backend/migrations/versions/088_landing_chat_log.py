"""landing chat log — simpan pertanyaan pengunjung landing page

Tujuannya riset produk: tau apa yang sebenernya ditanyain calon pelanggan
sebelum mereka daftar — keberatan apa yang muncul, fitur apa yang dicari,
harga bagian mana yang bikin ragu.

Tabel ini SENGAJA tanpa RLS dan tanpa tenant_id: pengunjung landing belum
punya tenant. Datanya juga sengaja nggak nyimpen IP atau apa pun yang bisa
ngidentifikasi orang — cuma `session_id` acak dari browser buat nyambungin
satu percakapan.

Revision ID: 088
Revises: 087
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '088'
down_revision = '087'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'landing_chat_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        # Acak dari browser, bukan identitas. Cuma buat ngelompokin percakapan.
        sa.Column('session_id', sa.String(64), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=True),
        # Giliran ke berapa dalam satu percakapan — pertanyaan pembuka biasanya
        # beda sifatnya dari pertanyaan lanjutan.
        sa.Column('turn', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_landing_chat_logs_created', 'landing_chat_logs',
                    [sa.text('created_at DESC')])
    op.create_index('ix_landing_chat_logs_session', 'landing_chat_logs', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_landing_chat_logs_session', table_name='landing_chat_logs')
    op.drop_index('ix_landing_chat_logs_created', table_name='landing_chat_logs')
    op.drop_table('landing_chat_logs')
