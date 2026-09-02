"""Purchasing dihidupkan — nota belanja di atas purchase_orders yang udah ada

Revision ID: 091
Revises: 090
Create Date: 2026-09-02 12:30:00.000000

Tabel `suppliers` (mig 008), `ingredient_suppliers` (019), `purchase_orders` +
`purchase_order_items` (028), dan `supplier_price_history` (044) dibikin lalu
**ditinggal** — nol model, nol route, nol UI, nol baris di produksi. Persis
nasib `product_variants` sebelum mig 090. Efeknya: HPP bahan baku diisi
manual sekali waktu setup, lalu basi; pemilik nggak pernah tahu belanja
bulan ini berapa, utang ke supplier berapa.

Gelombang 1 "ERP yang ngisi sendiri" (riset 2026-09-02): satu input manusia —
NOTA BELANJA — lalu stok, harga bahan (rata-rata bergerak), histori harga
per supplier, dan utang supplier keisi sendiri. Nota dimodelkan sebagai
`purchase_orders` berstatus `received` yang dibuat langsung (warkop belanja
ke pasar nggak bikin PO dulu), jadi PO formal tetap bisa nyusul di tabel
yang sama.

Yang ditambah:
- `purchase_orders.supplier_id` jadi NULLABLE — "beli di pasar" nggak punya
  supplier. Kolom nota: `received_at`, `invoice_no`, `photo_url`,
  `paid_amount` (utang = total − paid), `due_at`, `created_by`, `received_by`.
- `purchase_order_items.ingredient_id` jadi NULLABLE + `product_id` baru:
  tenant Starter non-F&B (vape, sepeda listrik) beli PRODUK JADI, bukan
  bahan. CHECK salah satu wajib terisi. `unit` (satuan di nota: kg/liter/
  dus) + `qty_base` (hasil konversi ke base_unit bahan) disimpan supaya
  struk bisa dibaca ulang tanpa ngitung lagi.
- `suppliers.payment_terms_days` — default jatuh tempo utang.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '091'
down_revision = '090'
branch_labels = None
depends_on = None


def upgrade():
    # ── suppliers ──
    op.add_column(
        'suppliers',
        sa.Column('payment_terms_days', sa.Integer(), server_default='0', nullable=False),
    )

    # ── purchase_orders → nota belanja ──
    op.alter_column('purchase_orders', 'supplier_id', existing_type=postgresql.UUID(), nullable=True)
    op.add_column('purchase_orders', sa.Column('received_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('purchase_orders', sa.Column('invoice_no', sa.String(), nullable=True))
    op.add_column('purchase_orders', sa.Column('photo_url', sa.String(), nullable=True))
    op.add_column(
        'purchase_orders',
        sa.Column('paid_amount', sa.Numeric(12, 2), server_default='0', nullable=False),
    )
    op.add_column('purchase_orders', sa.Column('due_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'purchase_orders',
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.add_column(
        'purchase_orders',
        sa.Column('received_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index(
        'ix_purchase_orders_outlet_received',
        'purchase_orders',
        ['outlet_id', 'deleted_at', 'received_at'],
    )

    # ── purchase_order_items → baris nota, bahan ATAU produk ──
    op.alter_column('purchase_order_items', 'ingredient_id', existing_type=postgresql.UUID(), nullable=True)
    op.add_column(
        'purchase_order_items',
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
    )
    op.add_column('purchase_order_items', sa.Column('unit', sa.String(), nullable=True))
    op.add_column('purchase_order_items', sa.Column('qty_base', sa.Float(), nullable=True))
    op.add_column('purchase_order_items', sa.Column('name_snapshot', sa.String(), nullable=True))
    op.create_check_constraint(
        'chk_poi_target',
        'purchase_order_items',
        'ingredient_id IS NOT NULL OR product_id IS NOT NULL',
    )


def downgrade():
    op.drop_constraint('chk_poi_target', 'purchase_order_items', type_='check')
    op.drop_column('purchase_order_items', 'name_snapshot')
    op.drop_column('purchase_order_items', 'qty_base')
    op.drop_column('purchase_order_items', 'unit')
    op.drop_column('purchase_order_items', 'product_id')
    op.alter_column('purchase_order_items', 'ingredient_id', existing_type=postgresql.UUID(), nullable=False)

    op.drop_index('ix_purchase_orders_outlet_received', table_name='purchase_orders')
    op.drop_column('purchase_orders', 'received_by')
    op.drop_column('purchase_orders', 'created_by')
    op.drop_column('purchase_orders', 'due_at')
    op.drop_column('purchase_orders', 'paid_amount')
    op.drop_column('purchase_orders', 'photo_url')
    op.drop_column('purchase_orders', 'invoice_no')
    op.drop_column('purchase_orders', 'received_at')
    op.alter_column('purchase_orders', 'supplier_id', existing_type=postgresql.UUID(), nullable=False)

    op.drop_column('suppliers', 'payment_terms_days')
