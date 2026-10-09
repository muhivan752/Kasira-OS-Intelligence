import unittest

from backend.services.account_deletion import KEEP_TABLES, plan_purge


def catalog():
    # Potongan skema nyata: RESTRICT order_items->products, NO ACTION hr_*,
    # events tanpa FK (outlet_id implisit), referral CASCADE dari tenants.
    cols = {
        "tenants": {"id": "uuid"},
        "users": {"id": "uuid", "tenant_id": "uuid", "role_id": "uuid"},
        "roles": {"id": "uuid", "tenant_id": "uuid"},
        "brands": {"id": "uuid", "tenant_id": "uuid"},
        "outlets": {"id": "uuid", "tenant_id": "uuid", "brand_id": "uuid"},
        "products": {"id": "uuid", "brand_id": "uuid"},
        "orders": {"id": "uuid", "outlet_id": "uuid", "user_id": "uuid"},
        "order_items": {"id": "uuid", "order_id": "uuid", "product_id": "uuid"},
        "events": {"id": "uuid", "outlet_id": "uuid"},
        "hr_employees": {"id": "uuid", "tenant_id": "uuid", "user_id": "uuid"},
        "referrals": {"id": "uuid", "referrer_tenant_id": "uuid"},
        "subscription_invoices": {"id": "uuid", "tenant_id": "uuid"},
    }
    fks = [
        ("users", "tenant_id", "tenants", "id"), ("users", "role_id", "roles", "id"),
        ("roles", "tenant_id", "tenants", "id"), ("brands", "tenant_id", "tenants", "id"),
        ("outlets", "tenant_id", "tenants", "id"), ("outlets", "brand_id", "brands", "id"),
        ("products", "brand_id", "brands", "id"), ("orders", "outlet_id", "outlets", "id"),
        ("orders", "user_id", "users", "id"), ("order_items", "order_id", "orders", "id"),
        ("order_items", "product_id", "products", "id"), ("hr_employees", "user_id", "users", "id"),
        ("referrals", "referrer_tenant_id", "tenants", "id"),
    ]
    return set(cols), cols, fks


class PurgePlanTests(unittest.TestCase):
    def test_children_before_parents(self):
        order, _ = plan_purge(*catalog())
        pos = {t: i for i, t in enumerate(order)}
        for child, parent in [("order_items", "products"), ("order_items", "orders"), ("orders", "outlets"),
                              ("orders", "users"), ("hr_employees", "users"), ("users", "roles"),
                              ("outlets", "brands"), ("products", "brands"), ("events", "outlets")]:
            self.assertLess(pos[child], pos[parent], f"{child} harus sebelum {parent}")

    def test_keeps_finance_and_other_tenants_records(self):
        order, _ = plan_purge(*catalog())
        for kept in ("tenants", "referrals", "subscription_invoices"):
            self.assertNotIn(kept, order)
            self.assertIn(kept, KEEP_TABLES)

    def test_tables_without_tenant_id_reach_tenant(self):
        _, preds = plan_purge(*catalog())
        self.assertEqual(preds["users"], "tenant_id::text = :tid")
        self.assertIn('"order_id" IN (SELECT "id" FROM "orders"', preds["order_items"])
        self.assertIn('"outlet_id" IN (SELECT "id" FROM "outlets"', preds["events"])

    def test_fk_cycle_fails_loudly(self):
        tables, cols, fks = catalog()
        cols["outlets"]["favorite_order_id"] = "uuid"
        fks.append(("outlets", "favorite_order_id", "orders", "id"))
        with self.assertRaises(RuntimeError):
            plan_purge(tables, cols, fks)


if __name__ == "__main__":
    unittest.main()
