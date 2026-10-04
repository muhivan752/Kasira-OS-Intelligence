import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from sqlalchemy.dialects import postgresql
from sqlalchemy import select

from backend.models.payment import Payment
from backend.models.recipe import Recipe
from backend.services.crdt import HLC
from backend.services.sync import next_page_cursor, get_table_changes, apply_pull_cursor, pull_order_columns


def row(ts, id='00000000-0000-0000-0000-000000000001', version=0):
    return {'id': id, 'hlc': f'{ts}:{version}:server:outlet'}


class SyncPullTests(unittest.IsolatedAsyncioTestCase):
    async def test_order_payment_cache_excludes_standalone_deposits(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: []))))
        await get_table_changes(db, Payment, {}, None, 'server:outlet',
                                required_fields=('order_id',))
        sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn('payments.order_id IS NOT NULL', sql)

    def test_newer_complete_table_does_not_skip_full_table_remainder(self):
        self.assertEqual(next_page_cursor((([row(10), row(20)], True),
                                           ([row(100)], False))),
                         (row(20)['hlc'], row(20)['id']))

    def test_slowest_full_table_limits_shared_cursor(self):
        self.assertEqual(next_page_cursor((([row(30)], True),
                                           ([row(10)], True)))[0], row(10)['hlc'])

    def test_variant_only_pagination_has_cursor(self):
        self.assertEqual(next_page_cursor((([row(40)], True),))[0], row(40)['hlc'])
        self.assertEqual(next_page_cursor((([row(40)], False),)), (None, None))

    def test_recipe_cursor_has_id_tie_break_without_row_version(self):
        stmt = apply_pull_cursor(select(Recipe), Recipe, HLC(1000, 0, 'server'), row(1)['id'])
        stmt = stmt.order_by(*pull_order_columns(Recipe))
        sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        self.assertIn('recipes.id >', sql)
        self.assertIn("date_trunc('milliseconds', recipes.updated_at)", sql)

    def test_normal_delta_replays_boundary_millisecond(self):
        stmt = apply_pull_cursor(select(Payment), Payment, HLC(1000, 9, 'server'))
        sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        self.assertIn('payments.updated_at >=', sql)
        self.assertNotIn('payments.row_version >', sql)


if __name__ == '__main__':
    unittest.main()
