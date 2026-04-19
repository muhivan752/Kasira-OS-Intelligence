"""add composite (updated_at, row_version) indexes untuk sync pagination

Revision ID: 082
Revises: 081
Create Date: 2026-04-19

CRITICAL #7 fix: cursor-based sync pagination butuh efficient ORDER BY
(updated_at, row_version) + LIMIT. Tanpa composite index = seq scan saat
data ribuan = slow + OOM risk.

Existing indexes (from earlier migrations):
  - orders(updated_at, row_version) ✓
  - payments(updated_at, row_version) ✓
  - products(updated_at, row_version) ✓

Missing — tambah di migration ini:
  - order_items(updated_at, row_version)  ← PALING KRITIKAL (biggest table)
  - cash_activities(updated_at, row_version)
  - ingredients(updated_at, row_version)
  - shifts(updated_at, row_version)
  - recipes(updated_at) — no row_version di model
  - recipe_ingredients(updated_at) — no row_version di model
  - categories(updated_at, row_version) — small table tapi konsisten
  - outlet_stock(updated_at, row_version)

CREATE INDEX CONCURRENTLY gak di-dukung di alembic upgrade transaction, pake
regular CREATE INDEX. Acceptable karena tables masih manageable size.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '082'
down_revision = '081'
branch_labels = None
depends_on = None


# Tables dgn row_version (composite index)
_COMPOSITE_INDEXES = [
    ("order_items", "ix_order_items_updated", "updated_at, row_version"),
    ("cash_activities", "ix_cash_activities_updated", "updated_at, row_version"),
    ("ingredients", "ix_ingredients_updated", "updated_at, row_version"),
    ("shifts", "ix_shifts_updated", "updated_at, row_version"),
    ("categories", "ix_categories_updated", "updated_at, row_version"),
    ("outlet_stock", "ix_outlet_stock_updated", "updated_at, row_version"),
]

# Tables tanpa row_version (single col)
_SINGLE_INDEXES = [
    ("recipes", "ix_recipes_updated", "updated_at"),
    ("recipe_ingredients", "ix_recipe_ingredients_updated", "updated_at"),
]


def upgrade():
    for table, idx, cols in _COMPOSITE_INDEXES + _SINGLE_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {idx} ON public.{table} "
            f"USING btree ({cols});"
        )


def downgrade():
    for _, idx, _ in _COMPOSITE_INDEXES + _SINGLE_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS public.{idx};")
