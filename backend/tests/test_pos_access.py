import unittest
from uuid import uuid4

from pydantic import ValidationError
from starlette.requests import Request
from backend.schemas.account import RoleSave
from backend.services.access import AccessContext, enforce_route
from backend.services.pos_access import redact, route_rules


class PosAccessTests(unittest.TestCase):
    def context(self, *permissions):
        return AccessContext(user_id=uuid4(), tenant_id=uuid4(), permissions=frozenset(permissions),
                             outlets=(), employee=None, mode='managed', version='qa')

    def test_registry_matches_real_endpoints_and_methods(self):
        rules = route_rules()
        self.assertGreater(len(rules), 60)
        for (method, endpoint), permissions in rules.items():
            request = Request({'type': 'http', 'method': method, 'path': '/api/v1/anything',
                               'headers': [], 'endpoint': endpoint})
            enforce_route(request, self.context(*permissions))
            self.assertTrue(callable(endpoint))
        # Same path text cannot whitelist a different callable or method.
        request = Request({'type': 'http', 'method': 'DELETE', 'path': '/api/v1/products',
                           'headers': [], 'endpoint': next(iter(rules))[1]})
        from fastapi import HTTPException
        with self.assertRaises(HTTPException): enforce_route(request, self.context('stock.view'))

    def test_recursive_cost_and_secrets_redaction(self):
        source = {'data': [{'name': 'Coffee', 'buy_price': 100, 'sold_total': 99,
                            'nested': {'cost_per_base_unit': 7, 'xendit_raw': {'secret': True}}}]}
        value = redact(source, self.context('stock.view'), 'products')['data'][0]
        self.assertIsNone(value['buy_price']); self.assertIsNone(value['sold_total'])
        self.assertIsNone(value['nested']['cost_per_base_unit']); self.assertNotIn('xendit_raw', value['nested'])
        self.assertEqual(source['data'][0]['buy_price'], 100)
        hpp_only = redact(source, self.context('hpp.view'), 'products')['data'][0]
        self.assertIsNone(hpp_only['buy_price'])
        self.assertEqual(hpp_only['nested']['cost_per_base_unit'], 7)
        price_only = redact(source, self.context('supplier.price.view'), 'products')['data'][0]
        self.assertEqual(price_only['buy_price'], 100)
        self.assertIsNone(price_only['nested']['cost_per_base_unit'])
        value = redact(source, self.context('hpp.view', 'supplier.price.view', 'sales.detail.view'), 'products')['data'][0]
        self.assertEqual(value['buy_price'], 100); self.assertEqual(value['sold_total'], 99)
        self.assertNotIn('xendit_raw', value['nested'])

    def test_cash_amount_is_operational_without_revealing_drawer_or_sales(self):
        value = redact({'id': 'shift', 'starting_cash': 900, 'variance': 5,
                        'activities': [{'amount': 120, 'description': 'Water'}], 'cash_payments': [{'amount': 30}],
                        'review': [{'total': 30}]}, self.context('pos.cash.manage'), 'shifts')
        self.assertIsNone(value['starting_cash']); self.assertIsNone(value['variance'])
        self.assertEqual(value['activities'][0]['amount'], 120)
        self.assertEqual(value['cash_payments'], []); self.assertEqual(value['review'], [])
        self.assertTrue(value['blind_close']); self.assertFalse(value['is_owner'])

    def test_role_grants_are_strict_and_ai_is_explicit(self):
        body = dict(id=uuid4(), client_request_id=uuid4(), name='Cashier', outlet_ids=[uuid4()])
        RoleSave(**body, permissions={'pos.sell': True, 'stock.receive': False})
        RoleSave(**body, permissions={'finance.manage': True, 'hpp.view': True, 'customers.export': True})
        self.assertTrue(RoleSave(**body, permissions={'ai.chat': True}).permissions['ai.chat'])
        for permissions in ({'pos.sell': 1}, {'pos.sell': 'true'}, {'ai.superuser': True}, {'unknown.view': True}):
            with self.subTest(permissions=permissions), self.assertRaises(ValidationError):
                RoleSave(**body, permissions=permissions)

    def test_tenant_scope_is_explicit_and_outlet_scope_cannot_be_empty(self):
        body = dict(id=uuid4(), client_request_id=uuid4(), name='Finance', permissions={'finance.view': True})
        RoleSave(**body, scope='tenant', outlet_ids=[])
        RoleSave(**body, scope='outlet', outlet_ids=[uuid4()])
        for scope, outlets in [('outlet', []), ('tenant', [uuid4()]), ('brand', [])]:
            with self.subTest(scope=scope), self.assertRaises(ValidationError):
                RoleSave(**body, scope=scope, outlet_ids=outlets)
