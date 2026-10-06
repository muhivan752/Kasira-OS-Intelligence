import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from backend.schemas.finance import ExpenseCreate, ExpenseUpdate
from backend.services.finance_service import month_bounds, purchase_payments_in_period, cost_map_for_brand, account_for_method
from backend.services.finance_context import report_month, is_finance_question, build_finance_context
from backend.api.routes.finance import _expense_account


def when(month, day=1):
    return datetime(2026, month, day, tzinfo=timezone.utc)


def event(kind, month, data, day=1):
    return NS(id=uuid4(), event_type=f'purchase.{kind}', created_at=when(month, day), event_data=data)


class FinanceTests(unittest.IsolatedAsyncioTestCase):
    def test_month_format_and_wib_boundaries(self):
        for month in ['2026-1', '2026-13', '2026-00', '1999-12', '9999-12', '2026-01-01', 'not-a-month']:
            with self.assertRaises(HTTPException):
                month_bounds(month)
        self.assertEqual(month_bounds('2026-01'), (datetime(2025, 12, 31, 17, tzinfo=timezone.utc), datetime(2026, 1, 31, 17, tzinfo=timezone.utc)))

    def test_installments_follow_payment_month_without_rewriting_receipt_month(self):
        purchase = NS(paid_amount=Decimal('1000'), received_at=when(9, 30))
        events = [event('received', 9, {'paid': '100'}, 30), event('paid', 10, {'amount': '300', 'paid_after': '400'}), event('paid', 11, {'amount': '600', 'paid_after': '1000'})]
        for month, expected in [('2026-09', '100.00'), ('2026-10', '300.00'), ('2026-11', '600.00')]:
            self.assertEqual(purchase_payments_in_period(purchase, events, *month_bounds(month)), (Decimal(expected), False))

    def test_old_overpayment_event_uses_actual_change_in_paid_total(self):
        p = NS(paid_amount=Decimal('1000'), received_at=when(9))
        rows = [event('received', 9, {'paid': '400'}), event('paid', 10, {'amount': '9999', 'paid_after': '1000'})]
        self.assertEqual(purchase_payments_in_period(p, rows, *month_bounds('2026-10')), (Decimal('600.00'), False))

    def test_legacy_without_events_is_explicitly_estimated(self):
        p = NS(paid_amount=Decimal('200'), received_at=when(10))
        self.assertEqual(purchase_payments_in_period(p, [], *month_bounds('2026-10')), (Decimal('200.00'), True))
        self.assertEqual(purchase_payments_in_period(p, [], *month_bounds('2026-09')), (Decimal('0.00'), True))

    def test_invalid_payment_history_does_not_make_up_cash(self):
        p = NS(paid_amount=Decimal('100'), received_at=when(9))
        with self.assertRaises(ValueError):
            purchase_payments_in_period(p, [event('received', 9, {'paid': '200'})], *month_bounds('2026-10'))

    def test_expense_update_validates_method_category_precision_and_nulls(self):
        for payload in [{'payment_method': 'fake'}, {'category': 'fake'}, {'recurring': 'daily'}, {'amount': '1.001'},
                        {'amount': '10000000000'}, {'amount': None}, {'category': None}, {'paid_at': None},
                        {'paid_at': '2026-01-01T00:00:00'}, {'paid_at': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()}]:
            with self.assertRaises(ValidationError, msg=str(payload)):
                ExpenseUpdate.model_validate({'row_version': 0, **payload})
        self.assertEqual(ExpenseUpdate.model_validate({'row_version': 0, 'payment_method': ' Transfer ', 'amount': '12.34'}).payment_method, 'transfer')
        self.assertEqual(ExpenseUpdate.model_validate({'row_version': 0}).model_dump(exclude_unset=True), {'row_version': 0})
        self.assertIsNone(ExpenseUpdate.model_validate({'row_version': 0, 'cash_account_id': None}).cash_account_id)

    def test_create_preserves_decimal_precision(self):
        self.assertEqual(ExpenseCreate(amount='10.11').amount, Decimal('10.11'))
        with self.assertRaises(ValidationError):
            ExpenseCreate(amount='1.001')

    def test_inactive_and_foreign_accounts_are_rejected(self):
        a = NS(id=uuid4(), name='Bank', kind='bank', default_for=['transfer'], is_active=True)
        closed = NS(id=uuid4(), kind='cash_drawer', default_for=['cash'], is_active=False)
        self.assertEqual(_expense_account([a, closed], 'transfer', None), a.id)
        for account_id in [closed.id, uuid4()]:
            with self.assertRaises(HTTPException):
                _expense_account([a, closed], 'cash', account_id)
        self.assertIsNone(account_for_method([closed], 'cash'))

    async def test_partial_invalid_recipe_does_not_become_known_hpp_or_fall_back_to_old_buy_price(self):
        from backend.tests.test_recipe_hpp_sync import recipe, line
        r = recipe([line(), line(unit='ml')])
        valid = recipe(); plain = uuid4()
        results = [NS(scalars=lambda: NS(all=lambda: [r, valid])), NS(all=lambda: [(r.product_id, Decimal('50')), (plain, Decimal('99'))])]
        db = NS(execute=AsyncMock(side_effect=results))
        costs = await cost_map_for_brand(db, uuid4())
        self.assertNotIn(r.product_id, costs)
        self.assertEqual(costs[valid.product_id], Decimal('1700.00'))
        self.assertEqual(costs[plain], Decimal('99.00'))

    def test_finance_context_periods_and_query_detection(self):
        now = when(1)
        self.assertEqual(report_month('pengeluaran bulan lalu', now), '2025-12')
        self.assertEqual(report_month('laba 2026-09', now), '2026-09')
        self.assertTrue(is_finance_question('Utang supplier gue berapa?'))
        self.assertFalse(is_finance_question('Tambahkan gula ke resep'))

    async def test_nonfinancial_message_skips_db(self):
        db = NS(execute=AsyncMock())
        self.assertEqual(await build_finance_context('stok gula', uuid4(), uuid4(), db), '')
        db.execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
