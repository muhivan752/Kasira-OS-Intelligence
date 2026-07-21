"""point_transactions.row_version — nutup drift model vs DB

Revision ID: 089
Revises: 088
Create Date: 2026-07-21 14:50:00.000000

Model `PointTransaction` (backend/models/loyalty.py) sejak awal punya kolom
`row_version`, tapi migration 059 yang bikin ulang tabelnya gak pernah nambahin
kolom itu. Efeknya bukan kosmetik: SQLAlchemy nyusun SELECT dari definisi
model, jadi SETIAP query ORM ke point_transactions meledak
`UndefinedColumnError`.

Yang ikut mati gara-gara ini:
  - `_try_earn_loyalty_points` — cek idempotensinya `select(PointTransaction)`,
    gagal, lalu ditelan `except Exception: pass`. Jadi earn poin gak pernah
    jalan di jalur MANAPUN, bukan cuma kelewat waktu customer belum ke-link.
  - `GET /loyalty/history` — 500.
  - `POST /loyalty/earn` — 500 di cek idempotensi.

Rule #29 juga minta tabel kritikal punya `row_version`, jadi arah fix-nya
nambahin kolom di DB (bukan ngebuang kolom dari model).
"""
from alembic import op
import sqlalchemy as sa

revision = '089'
down_revision = '088'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'point_transactions',
        sa.Column('row_version', sa.Integer(), server_default='0', nullable=False),
    )


def downgrade():
    op.drop_column('point_transactions', 'row_version')
