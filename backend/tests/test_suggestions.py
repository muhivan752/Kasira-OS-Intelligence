import unittest
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.services.suggestions import ceil500, display_qty, price_target, stock_candidate


class PriceRules(unittest.TestCase):
    def test_round_up_to_500(self):
        self.assertEqual(ceil500(19019.9), Decimal(19500))
        self.assertEqual(ceil500(19500), Decimal(19500))

    def test_target_margin_capped_at_25_percent(self):
        # Croffle: modal 15.600, jual 17.000. Target 30% = 22.500, dibatasi 21.250 → 21.500.
        self.assertEqual(price_target(Decimal(15600), Decimal(17000), Decimal("0.30")), Decimal(21500))

    def test_no_proposal_when_price_already_enough(self):
        self.assertIsNone(price_target(Decimal(5000), Decimal(18000), Decimal("0.30")))


class StockRules(unittest.TestCase):
    def base(self, **kw):
        args = dict(kind_subject="ingredient", subject_id="x", name="Biji kopi", unit="gram", stock=1000.0,
                    used_7d=2660.0, active_days=7, min_stock=0.0, pack=1000.0, price_per_unit=180,
                    supplier=SimpleNamespace(id="s", name="Pemasok", phone="0812"), cycle=None,
                    tz=ZoneInfo("Asia/Jakarta"), mode="recipe")
        args.update(kw)
        return stock_candidate(**args)

    def test_low_stock_orders_whole_packs_for_a_week(self):
        c = self.base()
        self.assertEqual(c.facts["days_left"], 2.6)
        self.assertEqual((c.facts["order_qty"], c.facts["order_unit"]), (2, "kg"))
        self.assertEqual(c.facts["order_total"], 360000)
        self.assertTrue(c.urgent)

    def test_enough_stock_is_quiet(self):
        self.assertIsNone(self.base(stock=5000.0))

    def test_too_little_history_is_quiet_unless_below_minimum(self):
        self.assertIsNone(self.base(active_days=2))
        self.assertIsNotNone(self.base(active_days=2, min_stock=1500.0))

    def test_display_units(self):
        self.assertEqual(display_qty(1500, "ml"), (1.5, "liter"))
        self.assertEqual(display_qty(400, "gram"), (400, "gram"))


if __name__ == "__main__":
    unittest.main()
