"""Shift otomatis: status 'paused', asal buka/tutup, hitung kas terpisah

Revision ID: 097
Revises: 096
Create Date: 2026-09-02 23:30:00.000000

Latar: 25 dari 27 shift di produksi terbuka lebih dari sehari (satu di
antaranya sejak 26 April). Toggle buka/tutup yang wajib kalah di lapangan.
Gelombang satu "shift otomatis" (keputusan Ivan 2 Sep 2026, rujukan desain
cash drawer Toast):

- sesi terbuka sendiri di transaksi pertama (`opened_by = 'auto'`)
- ditutup sendiri di batas hari usaha 04.00 waktu outlet (`closed_reason =
  'auto_cutoff'`), TANPA mengaku kasnya cocok: `ending_cash` dan `counted_at`
  dibiarkan NULL = "belum dihitung"
- status baru `paused` = "hitung nanti": laci lama dijeda, laci baru
  langsung jalan, penjualan nggak berhenti

Data lama: semua shift yang masih terbuka lebih dari 24 jam ditutup dengan
`closed_reason = 'auto_migration'`. Selisihnya TIDAK dihitung (ending_cash
NULL); angka empat bulan nggak ada artinya. `expected_ending_cash` diisi
karena itu memang bisa dihitung dari data.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '097'
down_revision = '096'
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE nggak boleh di dalam transaksi yang sama dengan
    # pemakaiannya (pola sama dengan 083).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE shift_status ADD VALUE IF NOT EXISTS 'paused';")

    op.add_column('shifts', sa.Column('opened_by', sa.String(length=16), server_default='manual', nullable=False))
    op.add_column('shifts', sa.Column('closed_reason', sa.String(length=24), nullable=True))
    op.add_column('shifts', sa.Column('counted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shifts', sa.Column('closed_by_user_id', postgresql.UUID(as_uuid=True),
                                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('shifts', sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True))
    # Indeks ini ternyata udah ada dari migrasi lama; IF NOT EXISTS biar
    # idempoten (kegigit pas jalan pertama: DuplicateTableError).
    op.execute("CREATE INDEX IF NOT EXISTS ix_shifts_outlet_status ON shifts (outlet_id, status) WHERE deleted_at IS NULL")

    # Shift yang udah ditutup manual sebelum ini = pernah dihitung.
    op.execute("""
        UPDATE shifts
           SET counted_at = COALESCE(end_time, updated_at),
               closed_reason = 'manual'
         WHERE status = 'closed' AND ending_cash IS NOT NULL AND closed_reason IS NULL
    """)

    # Shift basi: tutup, jangan hitung selisihnya.
    op.execute("""
        WITH kas AS (
            SELECT p.shift_session_id AS shift_id,
                   COALESCE(SUM(p.amount_paid - COALESCE(p.change_amount, 0)), 0) AS cash_in
              FROM payments p
             WHERE p.payment_method = 'cash' AND p.status = 'paid' AND p.deleted_at IS NULL
             GROUP BY p.shift_session_id
        ), aktivitas AS (
            SELECT ca.shift_id,
                   COALESCE(SUM(CASE WHEN ca.activity_type = 'income' THEN ca.amount ELSE 0 END), 0) AS income,
                   COALESCE(SUM(CASE WHEN ca.activity_type = 'expense' THEN ca.amount ELSE 0 END), 0) AS expense
              FROM cash_activities ca
             WHERE ca.deleted_at IS NULL
             GROUP BY ca.shift_id
        )
        UPDATE shifts s
           SET status = 'closed',
               end_time = now(),
               closed_reason = 'auto_migration',
               expected_ending_cash = s.starting_cash
                                      + COALESCE(k.cash_in, 0)
                                      + COALESCE(a.income, 0)
                                      - COALESCE(a.expense, 0),
               notes = NULLIF(TRIM(BOTH ' |' FROM COALESCE(s.notes, '') ||
                       ' | Ditutup sistem saat pindah ke shift otomatis (terbuka sejak ' ||
                       to_char(s.start_time AT TIME ZONE 'Asia/Jakarta', 'DD Mon YYYY') || ')'), ''),
               row_version = s.row_version + 1,
               updated_at = now()
          FROM shifts s2
          LEFT JOIN kas k ON k.shift_id = s2.id
          LEFT JOIN aktivitas a ON a.shift_id = s2.id
         WHERE s.id = s2.id
           AND s.status = 'open'
           AND s.deleted_at IS NULL
           AND s.start_time < now() - interval '24 hours'
    """)


def downgrade():
    op.drop_column('shifts', 'paused_at')
    op.drop_column('shifts', 'closed_by_user_id')
    op.drop_column('shifts', 'counted_at')
    op.drop_column('shifts', 'closed_reason')
    op.drop_column('shifts', 'opened_by')
    # Nilai enum 'paused' sengaja nggak dicabut: Postgres nggak punya DROP VALUE.
