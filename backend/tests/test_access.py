import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from backend.schemas.access import AccessPolicy, HRIS_MANAGE, PERMISSIONS
from backend.services.access import AccessContext, enforce_route, role_permissions, validate_tenant_header


class AccessTests(unittest.TestCase):
    def user(self, **updates):
        return SimpleNamespace(id=uuid4(), tenant_id=uuid4(), is_superuser=False, role_id=None, **updates)

    def role(self, **updates):
        return SimpleNamespace(permissions=updates.pop("permissions", {}), **updates)

    def context(self, mode="managed", **updates):
        values = dict(user_id=uuid4(), tenant_id=uuid4(), permissions=frozenset({"hris.self"}),
            outlets=(), employee=None, mode=mode, version="qa")
        return AccessContext(**{**values, **updates})

    def request(self, path, method="GET", headers=()):
        from backend.api.routes import auth, hris
        endpoints = {"/api/v1/auth/access": auth.get_access, "/auth/access": auth.get_access,
            "/auth/me": auth.get_me, "/hris/schedules/{record_id}": hris.edit_schedule,
            "/auth/logout": auth.logout, "/hris/setup": hris.setup}
        return Request({"type": "http", "method": method, "path": path, "headers": list(headers),
            "endpoint": endpoints.get(path)})

    def test_owner_is_tenant_owner_without_role_name_inference(self):
        user = self.user(); user.is_superuser = True
        permissions, mode, _ = role_permissions(user, self.role(permissions={"access_policy": None}))
        self.assertEqual(permissions, PERMISSIONS)
        self.assertEqual(mode, "owner")
        permissions, _, _ = role_permissions(self.user(), self.role(name="Owner", is_system=True))
        self.assertNotIn("access.manage", permissions)
        self.assertNotIn("hris.employees.manage", permissions)

    def test_legacy_cashier_does_not_gain_management_or_ai(self):
        permissions, mode, policy = role_permissions(self.user(), None)
        self.assertEqual(mode, "legacy"); self.assertIsNone(policy)
        self.assertIn("pos.sell", permissions)
        for permission in ("finance.manage", "hris.employees.manage", "access.manage", "ai.chat"):
            self.assertNotIn(permission, permissions)

    def test_legacy_hris_manager_and_explicit_denial(self):
        permissions, _, _ = role_permissions(self.user(), self.role(permissions={
            "hris_manage": True, "hris.attendance.manage": False}))
        self.assertEqual(permissions & HRIS_MANAGE, HRIS_MANAGE - {"hris.attendance.manage"})

    def test_legacy_role_flags_map_independently(self):
        permissions, _, _ = role_permissions(self.user(), self.role(can_view_hpp=True,
            can_view_supplier_price=False, can_refund=True, can_approve_refund=False))
        self.assertTrue({"hpp.view", "pos.refund"} <= permissions)
        self.assertTrue({"supplier.price.view", "pos.refund.approve"}.isdisjoint(permissions))

    def test_truthy_values_and_wildcards_do_not_grant(self):
        permissions, _, _ = role_permissions(self.user(), self.role(permissions={
            "hris_manage": "true", "finance.manage": 1, "*": True}, can_view_hpp=1))
        self.assertTrue(HRIS_MANAGE.isdisjoint(permissions))
        self.assertNotIn("hpp.view", permissions)
        self.assertNotIn("finance.manage", permissions)

    def test_missing_or_deleted_role_fails_closed(self):
        user = self.user(); user.role_id = uuid4()
        with self.assertRaises(HTTPException) as rejected:
            role_permissions(user, None)
        self.assertEqual(rejected.exception.detail["code"], "ROLE_UNAVAILABLE")

    def test_managed_policy_replaces_legacy_grants(self):
        role = self.role(can_view_hpp=True, permissions={"hris_manage": True, "access_policy": {
            "version": 1, "permissions": {"hris.schedules.manage": True, "hris.attendance.manage": False}}})
        permissions, mode, _ = role_permissions(self.user(), role)
        self.assertEqual(mode, "managed")
        self.assertEqual(permissions, frozenset({"hris.schedules.manage"}))

    def test_malformed_policy_does_not_fall_back_to_legacy(self):
        for policy in (None, {}, {"version": 2}, {"version": True}, {"version": "1"},
                       {"version": 1, "permissions": {"hris.self": "true"}},
                       {"version": 1, "permissions": {"finance.manage": 1}},
                       {"version": 1, "permissions": {"*": True}}, {"version": 1, "unknown": True}):
            with self.subTest(policy=policy), self.assertRaises(HTTPException) as rejected:
                role_permissions(self.user(), self.role(permissions={"hris_manage": True, "access_policy": policy}))
            self.assertEqual(rejected.exception.detail["code"], "ACCESS_POLICY_INVALID")

    def test_invalid_uuid_and_duplicate_scope_are_rejected(self):
        oid = str(uuid4())
        for ids in (["not-a-uuid"], [oid, oid]):
            with self.assertRaises(ValidationError):
                AccessPolicy(version=1, outlet_ids=ids)

    def test_unknown_permission_cannot_be_required_or_allowed(self):
        context = self.context(permissions=frozenset({"invented.permission"}))
        self.assertFalse(context.allows("invented.permission"))
        with self.assertRaises(HTTPException):
            context.require("invented.permission")

    def test_outlet_membership_is_exact(self):
        allowed = SimpleNamespace(id=uuid4())
        context = self.context(outlets=(allowed,))
        context.require_outlet(allowed.id)
        for target in (uuid4(), str(allowed.id)):
            with self.assertRaises(HTTPException) as rejected:
                context.require_outlet(target)
            self.assertEqual(rejected.exception.status_code, 404)

    def test_tenant_header_never_changes_authenticated_tenant(self):
        tid = uuid4()
        validate_tenant_header(self.request("/auth/access"), tid)
        validate_tenant_header(self.request("/auth/access", headers=[(b"x-tenant-id", str(tid).upper().encode())]), tid)
        for value in (str(uuid4()), "public", "", "tenant_name", "invalid"):
            with self.assertRaises(HTTPException) as rejected:
                validate_tenant_header(self.request("/auth/access", headers=[(b"x-tenant-id", value.encode())]), tid)
            self.assertEqual(rejected.exception.detail["code"], "TENANT_MISMATCH")

    def test_managed_route_guard_accepts_only_supported_method_and_template(self):
        context = self.context()
        for path, method in (("/api/v1/auth/access", "GET"), ("/auth/me", "GET"),
                             ("/hris/schedules/{record_id}", "PUT"), ("/auth/logout", "DELETE")):
            enforce_route(self.request(path, method), context)
        for path, method in (("/api/v1/ai/chat", "POST"), ("/sync/", "POST"), ("/finance/summary", "GET"),
                             ("/hris/unknown", "GET"), ("/hris/setup", "POST"),
                             ("/attacker/api/v1/hris/setup", "GET"), ("", "GET")):
            with self.subTest(path=path), self.assertRaises(HTTPException) as rejected:
                enforce_route(self.request(path, method), context)
            self.assertEqual(rejected.exception.detail["code"], "ACCESS_ROUTE_NOT_READY")

    def test_owner_and_legacy_routes_keep_existing_handlers(self):
        for mode in ("owner", "legacy"):
            enforce_route(self.request("/api/v1/finance/summary"), self.context(mode=mode))

    def endpoint_request(self, endpoint, method):
        return Request({"type": "http", "method": method, "path": "/", "headers": [], "endpoint": endpoint})

    def test_legacy_staff_keeps_cashier_routes_but_not_owner_work(self):
        from backend.api.routes import (campaigns, categories, finance, orders, outlets, payments, products,
            reports, shifts, sync, tabs)
        from backend.services.access import LEGACY_BASE
        staff = self.context(mode="legacy", permissions=LEGACY_BASE)
        for endpoint, method in ((orders.create_order, "POST"), (payments.create_payment, "POST"),
                                 (sync.sync_data, "POST"), (tabs.pay_tab_full, "POST"), (shifts.open_shift, "POST"),
                                 (products.read_products, "GET"), (products.restock_product, "POST"),
                                 (outlets.read_outlet, "GET"), (reports.get_daily_report, "GET"),
                                 (products.update_product, "PUT")):
            with self.subTest(endpoint=endpoint.__name__):
                enforce_route(self.endpoint_request(endpoint, method), staff)
        for endpoint, method, code in ((outlets.update_outlet, "PUT", "OWNER_ONLY"),
                                       (outlets.setup_payment_own_key, "POST", "OWNER_ONLY"),
                                       (products.delete_product, "DELETE", "OWNER_ONLY"),
                                       (categories.create_category, "POST", "OWNER_ONLY"),
                                       (campaigns.list_campaigns, "GET", "OWNER_ONLY"),
                                       (reports.get_report_summary, "GET", "PERMISSION_DENIED"),
                                       (finance.finance_summary, "GET", "PERMISSION_DENIED")):
            with self.subTest(endpoint=endpoint.__name__), self.assertRaises(HTTPException) as rejected:
                enforce_route(self.endpoint_request(endpoint, method), staff)
            self.assertEqual(rejected.exception.detail["code"], code)
        granted = self.context(mode="legacy", permissions=LEGACY_BASE | {"finance.view", "sales.detail.view"})
        enforce_route(self.endpoint_request(finance.finance_summary, "GET"), granted)
        enforce_route(self.endpoint_request(reports.get_report_summary, "GET"), granted)
        owner = self.context(mode="owner", permissions=PERMISSIONS)
        for endpoint, method in ((outlets.update_outlet, "PUT"), (campaigns.list_campaigns, "GET")):
            enforce_route(self.endpoint_request(endpoint, method), owner)

    def test_public_contract_excludes_private_profile_and_role_contents(self):
        outlet = SimpleNamespace(id=uuid4(), name="QA", timezone="Asia/Jakarta")
        employee = SimpleNamespace(id=uuid4(), phone="PRIVATE", notes="PRIVATE")
        public = self.context(outlets=(outlet,), employee=employee).public()
        self.assertEqual(public["enforced_modules"], ["hris", "pos", "stock", "sync", "finance", "purchasing", "customers", "hpp", "ai"])
        self.assertEqual(public["scope"], "tenant")
        self.assertFalse(public["offline_pos_allowed"])
        self.assertNotIn("PRIVATE", str(public))
        self.assertNotIn("access_policy", public)


class DefaultRoleTests(unittest.TestCase):
    def test_templates_are_valid_managed_policies(self):
        from backend.services.default_roles import TEMPLATES
        names = set()
        for name, key, perms in TEMPLATES:
            policy = AccessPolicy.model_validate({"version": 1, "permissions": {p: True for p in perms}, "outlet_ids": [], "brand_ids": []})
            self.assertIn("hris.self", policy.permissions)
            self.assertNotIn("access.manage", perms)
            self.assertNotIn("hris.accounts.manage", perms)
            names.add(name)
        self.assertEqual(names, {"Kasir", "Barista", "Kepala toko"})
