import unittest
from uuid import uuid4

from fastapi import HTTPException

from backend.services.access import AccessContext
from backend.services.pos_access import validate_staff_push


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDb:
    """Pesanan yang sudah ada di server: {order_id: (user_id, outlet_id)}."""

    def __init__(self, existing):
        self.existing = existing

    async def execute(self, _stmt):
        return FakeResult([(oid, uid, out) for oid, (uid, out) in self.existing.items()])


class StaffOfflinePushTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.me = uuid4()
        self.outlet = uuid4()

    def context(self, *permissions):
        return AccessContext(user_id=self.me, tenant_id=uuid4(), permissions=frozenset(permissions),
                             outlets=(), employee=None, mode='managed', version='qa')

    def sale(self, **order):
        oid = str(uuid4())
        base = {'id': oid, 'user_id': str(self.me), 'outlet_id': str(self.outlet), 'subtotal': '20000', 'discount_amount': '0'}
        base.update(order)
        return {'orders': [base],
                'order_items': [{'id': str(uuid4()), 'order_id': oid}],
                'payments': [{'id': str(uuid4()), 'order_id': oid, 'outlet_id': str(self.outlet)}]}

    async def check(self, changes, *permissions, existing=None):
        await validate_staff_push(FakeDb(existing or {}), changes, self.context(*permissions), self.outlet)

    async def denied(self, changes, *permissions, existing=None):
        with self.assertRaises(HTTPException) as raised:
            await self.check(changes, *permissions, existing=existing)
        return raised.exception

    async def test_own_offline_sale_is_accepted(self):
        await self.check(self.sale(), 'pos.sell')
        # App lama mengirim user_id kosong; server mengisinya dengan akun yang sync.
        await self.check(self.sale(user_id=''), 'pos.sell')

    async def test_without_pos_sell_queue_waits_for_owner(self):
        error = await self.denied(self.sale(), 'stock.view')
        self.assertEqual(error.detail['code'], 'OFFLINE_SYNC_REVIEW_REQUIRED')

    async def test_other_tables_wait_for_owner(self):
        for key in ('products', 'shifts', 'cash_activities', 'outlet_stock', 'categories'):
            changes = self.sale()
            changes[key] = [{'id': str(uuid4())}]
            error = await self.denied(changes, 'pos.sell', 'pos.shift.manage', 'pos.cash.manage')
            self.assertEqual(error.detail['code'], 'OFFLINE_SYNC_REVIEW_REQUIRED')

    async def test_cannot_push_someone_elses_order(self):
        await self.denied(self.sale(user_id=str(uuid4())), 'pos.sell')
        changes = self.sale()
        oid = changes['orders'][0]['id']
        from uuid import UUID
        await self.denied(changes, 'pos.sell', existing={UUID(oid): (uuid4(), self.outlet)})

    async def test_items_and_payments_need_an_own_parent(self):
        stranger = uuid4()
        orphan = {'order_items': [{'id': str(uuid4()), 'order_id': str(stranger)}]}
        await self.denied(orphan, 'pos.sell')
        await self.denied(orphan, 'pos.sell', existing={stranger: (uuid4(), self.outlet)})
        await self.check(orphan, 'pos.sell', existing={stranger: (self.me, self.outlet)})

    async def test_other_outlet_or_cashier_is_rejected(self):
        await self.denied(self.sale(outlet_id=str(uuid4())), 'pos.sell')
        changes = self.sale()
        changes['payments'][0]['processed_by'] = str(uuid4())
        await self.denied(changes, 'pos.sell')

    async def test_discount_limit_matches_online_path(self):
        await self.check(self.sale(discount_amount='4000'), 'pos.sell')
        error = await self.denied(self.sale(discount_amount='4001'), 'pos.sell')
        self.assertEqual(error.detail['code'], 'PERMISSION_DENIED')
        await self.check(self.sale(discount_amount='9000'), 'pos.sell', 'pos.discount.override')


if __name__ == '__main__':
    unittest.main()
