"""Row Level Security policies and composite indexes for tenant isolation

Revision ID: 069
Revises: 068
Create Date: 2026-04-12 22:00:00.000000
"""
from alembic import op

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


# Tables with direct tenant_id column
DIRECT_TENANT_TABLES = [
    "brands",
    "customers",
    "invoices",
    "knowledge_graph_edges",
    "notifications",
    "outlets",
    "reservations",
    "roles",
    "subscriptions",
    "subscription_invoices",
    "suppliers",
    "users",
]

# Tables isolated via outlet_id → outlets.tenant_id
OUTLET_TABLES = [
    "orders",
    "payments",
    "shifts",
    "tables",
    "tabs",
    "devices",
    "outlet_stock",
    "outlet_tax_config",
    "outlet_location_detail",
    "outlet_product_overrides",
    "reservation_settings",
    "sessions",
    "stock_events",
    "stock_snapshots",
    "purchase_orders",
    "connect_outlets",
    "customer_points",
    "point_transactions",
]

# Tables isolated via brand_id → brands.tenant_id
BRAND_TABLES = [
    "categories",
    "ingredients",
    "modifiers",
    "products",
    "pricing_rules",
]

# Tables isolated via parent FK (indirect)
# order_items → orders.outlet_id
# cash_activities → shifts.outlet_id
# recipe_ingredients → recipes.product_id → products.brand_id
# recipes → products.brand_id
# product_variants → products.brand_id
# tab_splits → tabs.outlet_id
# partial_payments → payments.outlet_id
# payment_refunds → payments.outlet_id
INDIRECT_TABLES = {
    "order_items": ("order_id", "orders", "outlet_id"),
    "cash_activities": ("shift_id", "shifts", "outlet_id"),
    "recipes": ("product_id", "products", "brand_id"),
    "recipe_ingredients": ("recipe_id", "recipes", "id"),  # via recipes policy
    "product_variants": ("product_id", "products", "brand_id"),
    "tab_splits": ("tab_id", "tabs", "outlet_id"),
    "partial_payments": ("payment_id", "payments", "outlet_id"),
    "payment_refunds": ("payment_id", "payments", "outlet_id"),
    "ingredient_suppliers": ("ingredient_id", "ingredients", "brand_id"),
    "ingredient_units": ("ingredient_id", "ingredients", "brand_id"),
    "supplier_price_history": ("supplier_id", "suppliers", "tenant_id"),
    "subscription_payments": ("subscription_id", "subscriptions", "tenant_id"),
    "connect_orders": ("connect_outlet_id", "connect_outlets", "outlet_id"),
    "connect_chats": ("connect_outlet_id", "connect_outlets", "outlet_id"),
    "connect_customer_profiles": ("customer_id", "customers", "tenant_id"),
    "connect_behavior_log": ("connect_customer_profile_id", "connect_customer_profiles", "id"),
    "purchase_order_items": ("purchase_order_id", "purchase_orders", "outlet_id"),
}


def _policy_bypass():
    """Allow access when app.current_tenant_id is not set (migrations, superadmin)."""
    return "current_setting('app.current_tenant_id', true) = ''"


def upgrade():
    # ── 1. RLS Policies ──────────────────────────────────────────────

    # Direct tenant_id tables
    for table in DIRECT_TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                {_policy_bypass()}
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
        """)

    # Outlet-based tables
    for table in OUTLET_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                {_policy_bypass()}
                OR outlet_id IN (
                    SELECT id FROM outlets
                    WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
                )
            )
        """)

    # Brand-based tables
    for table in BRAND_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                {_policy_bypass()}
                OR brand_id IN (
                    SELECT id FROM brands
                    WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
                )
            )
        """)

    # Indirect tables — cascade via parent FK
    for table, (fk_col, parent_table, parent_filter_col) in INDIRECT_TABLES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        if parent_filter_col == "tenant_id":
            # Parent has direct tenant_id
            op.execute(f"""
                CREATE POLICY tenant_isolation ON {table}
                USING (
                    {_policy_bypass()}
                    OR {fk_col} IN (
                        SELECT id FROM {parent_table}
                        WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
                    )
                )
            """)
        elif parent_filter_col == "outlet_id":
            # Parent has outlet_id → outlets.tenant_id
            op.execute(f"""
                CREATE POLICY tenant_isolation ON {table}
                USING (
                    {_policy_bypass()}
                    OR {fk_col} IN (
                        SELECT id FROM {parent_table}
                        WHERE outlet_id IN (
                            SELECT id FROM outlets
                            WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
                        )
                    )
                )
            """)
        elif parent_filter_col == "brand_id":
            # Parent has brand_id → brands.tenant_id
            op.execute(f"""
                CREATE POLICY tenant_isolation ON {table}
                USING (
                    {_policy_bypass()}
                    OR {fk_col} IN (
                        SELECT id FROM {parent_table}
                        WHERE brand_id IN (
                            SELECT id FROM brands
                            WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
                        )
                    )
                )
            """)
        elif parent_filter_col == "id":
            # Parent is also RLS-protected, just check FK exists in parent
            op.execute(f"""
                CREATE POLICY tenant_isolation ON {table}
                USING (
                    {_policy_bypass()}
                    OR {fk_col} IN (SELECT id FROM {parent_table})
                )
            """)

    # Event partitions — RLS on parent, partitions inherit
    op.execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE events FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON events
        USING (
            {_policy_bypass()}
            OR outlet_id IN (
                SELECT id FROM outlets
                WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
            )
        )
    """)

    # Audit log — has tenant_id directly
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON audit_log
        USING (
            {_policy_bypass()}
            OR tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    """)

    # ── 2. Composite Indexes ─────────────────────────────────────────

    # Orders: most queried by outlet + time
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_outlet_created ON orders (outlet_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_outlet_status ON orders (outlet_id, status) WHERE deleted_at IS NULL")

    # Order items: queried via order
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items (order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_items_product_id ON order_items (product_id)")

    # Products: by brand (tenant scope)
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_brand ON products (brand_id) WHERE deleted_at IS NULL")

    # Categories: by brand
    op.execute("CREATE INDEX IF NOT EXISTS ix_categories_brand ON categories (brand_id) WHERE deleted_at IS NULL")

    # Payments: by outlet + time
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_outlet_created ON payments (outlet_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments (order_id)")

    # Shifts: by outlet + status
    op.execute("CREATE INDEX IF NOT EXISTS ix_shifts_outlet_status ON shifts (outlet_id, status) WHERE deleted_at IS NULL")

    # Ingredients: by brand
    op.execute("CREATE INDEX IF NOT EXISTS ix_ingredients_brand ON ingredients (brand_id) WHERE deleted_at IS NULL")

    # Outlet stock: by outlet
    op.execute("CREATE INDEX IF NOT EXISTS ix_outlet_stock_outlet ON outlet_stock (outlet_id) WHERE deleted_at IS NULL")

    # Customers: by tenant
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_tenant ON customers (tenant_id) WHERE deleted_at IS NULL")

    # Users: by tenant
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_tenant ON users (tenant_id) WHERE deleted_at IS NULL")

    # Outlets: by tenant
    op.execute("CREATE INDEX IF NOT EXISTS ix_outlets_tenant ON outlets (tenant_id) WHERE deleted_at IS NULL")

    # Brands: by tenant
    op.execute("CREATE INDEX IF NOT EXISTS ix_brands_tenant ON brands (tenant_id) WHERE deleted_at IS NULL")

    # Sync performance: updated_at + row_version for delta queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_updated ON orders (updated_at, row_version)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_updated ON products (updated_at, row_version)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_updated ON payments (updated_at, row_version)")

    # Recipes: by product
    op.execute("CREATE INDEX IF NOT EXISTS ix_recipes_product_active ON recipes (product_id) WHERE is_active = true AND deleted_at IS NULL")


def downgrade():
    # Drop all RLS policies
    all_tables = (
        DIRECT_TENANT_TABLES
        + OUTLET_TABLES
        + BRAND_TABLES
        + list(INDIRECT_TABLES.keys())
        + ["events", "audit_log"]
    )
    for table in all_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop composite indexes
    indexes = [
        "ix_orders_outlet_created", "ix_orders_outlet_status",
        "ix_order_items_order_id", "ix_order_items_product_id",
        "ix_products_brand", "ix_categories_brand",
        "ix_payments_outlet_created", "ix_payments_order_id",
        "ix_shifts_outlet_status", "ix_ingredients_brand",
        "ix_outlet_stock_outlet", "ix_customers_tenant",
        "ix_users_tenant", "ix_outlets_tenant", "ix_brands_tenant",
        "ix_orders_updated", "ix_products_updated", "ix_payments_updated",
        "ix_recipes_product_active",
    ]
    for idx in indexes:
        op.execute(f"DROP INDEX IF EXISTS {idx}")
