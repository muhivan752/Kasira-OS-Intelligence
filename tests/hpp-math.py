import random
import unittest
import json
from unittest.mock import patch
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

from backend.services import hpp_math as math
from backend.services import hpp_setup_service as setup


class HppMathTests(unittest.TestCase):
    def test_purchase_and_portion(self):
        bought, cost = math.purchase_cost(15000, 1, "kg", "gram")
        self.assertEqual(bought, 1000)
        self.assertEqual(cost, 15)
        portion = math.portion_quantity(2, "kg", "gram", 20, "batch")
        self.assertEqual(portion, 100)
        self.assertEqual(math.line_cost(portion, "gram", SimpleNamespace(base_unit="gram", cost_per_base_unit=cost)), 1500)

    def test_legacy_base_and_volume(self):
        self.assertEqual(math.convert(18, "gram", "kg"), Decimal("0.018"))
        self.assertEqual(math.convert(120, "ml", "liter"), Decimal("0.12"))
        self.assertEqual(math.convert(2, "ons", "gram"), 200)
        self.assertEqual(math.purchase_cost(22000, 1, "liter", "ml"), (1000, 22))

    def test_precision(self):
        _, cost = math.purchase_cost(1, 1000, "gram", "gram")
        self.assertEqual(cost, Decimal("0.00100000"))
        self.assertEqual(math.money(math.line_cost(1000, "gram", SimpleNamespace(base_unit="gram", cost_per_base_unit=cost))), "1.00")
        self.assertEqual(math.purchase_cost(1, 3, "pcs", "pcs")[1], Decimal("0.33333333"))

    def test_weighted_ingredient_cost_precision(self):
        from backend.services.purchasing_service import moving_average
        self.assertEqual(moving_average(1000, Decimal("0.001"), 1000, Decimal("0.003"), precision=math.UNIT_COST), Decimal("0.00200000"))
        self.assertEqual(moving_average(0, Decimal(0), 1000, Decimal("0.001"), precision=math.UNIT_COST), Decimal("0.00100000"))
        self.assertEqual(moving_average(2, Decimal("10000"), 2, Decimal("10001")), Decimal("10000.50"))

    def test_independent_fraction_oracle(self):
        rng = random.Random(430)
        for _ in range(500):
            price, qty, portions, used = [rng.randint(1, 1000) for _ in range(4)]
            bought, cost = math.purchase_cost(price, qty, "kg", "gram")
            self.assertEqual(bought, qty * 1000)
            oracle_cost = Decimal(price) / Decimal(qty * 1000)
            self.assertLessEqual(abs(cost - oracle_cost), Decimal("0.000000005"))
            q = math.portion_quantity(used, "kg", "gram", portions, "batch")
            exact_q = Fraction(used * 1000, portions)
            self.assertAlmostEqual(float(q), float(exact_q), places=8)
            actual = math.line_cost(q, "gram", SimpleNamespace(base_unit="gram", cost_per_base_unit=cost))
            self.assertEqual(actual, q * cost)

    def test_invalid_and_ambiguous_units(self):
        for value in (None, True, 0, -1, "NaN", "Infinity", "1e100"):
            with self.assertRaises(ValueError, msg=str(value)):
                math.number(value)
        for source, target in (("kg", "ml"), ("potong", "gram"), ("dus", "pcs"), ("papan", "pcs")):
            with self.assertRaises(ValueError):
                math.convert(1, source, target)
        self.assertEqual(math.convert(2, "potong", "potong"), 2)
        self.assertEqual(math.purchase_cost(0, 1000, "gram", "gram")[1], 0)
        with self.assertRaises(ValueError):
            math.purchase_cost("10.001", 1, "pcs", "pcs")

    def test_explicit_pack_contents_are_multiplied_in_backend(self):
        self.assertEqual(math.purchase_cost(40000, 2, "papan", "potong", pack_size=10, pack_unit="potong"), (20, 2000))
        self.assertEqual(math.purchase_cost(30000, 2, "bungkus", "gram", pack_size=200, pack_unit="gram"), (400, 75))
        self.assertEqual(math.purchase_cost(54000, 3, "kotak", "ml", pack_size=1, pack_unit="liter"), (3000, 18))
        with self.assertRaises(ValueError):
            math.purchase_cost(54000, 3, "kg", "gram", pack_size=1000, pack_unit="gram")

    def test_unit_purchase_price_is_multiplied_in_backend(self):
        total = math.purchase_total(15000, 5, "per_unit")
        self.assertEqual(total, 75000)
        self.assertEqual(math.purchase_cost(total, 5, "kg", "gram"), (5000, 15))
        self.assertEqual(math.purchase_total("0.001", 1000, "per_unit"), Decimal("1.000"))
        with self.assertRaises(ValueError):
            math.purchase_total("0.001", 1, "per_unit")
        story = "satu porsi beras 100 gram beli 5 kg harga 15000 per kg"
        draft = setup.Draft.model_validate({"product_name": "Nasi", "servings": 1,
            "servings_source": "user", "servings_evidence": "satu porsi", "ingredients": [
                {"name": "Beras", "quantity": 100, "quantity_unit": "gram",
                 "quantity_source": "user", "quantity_evidence": "beras 100 gram",
                 "buy_price": 15000, "buy_price_basis": "per_unit", "buy_qty": 5, "buy_unit": "kg",
                 "price_source": "user", "price_evidence": "beli 5 kg harga 15000 per kg"}]})
        preview = setup.prepare(draft, ([], [], []), [story], "manual")
        self.assertTrue(preview["ready"], preview["missing"])
        self.assertEqual(preview["total_cost"], "1500.00")
        self.assertEqual(preview["lines"][0]["buy_price"], "75000")
        self.assertEqual(preview["lines"][0]["buy_qty"], "5000.0")
        self.assertFalse(preview["is_estimated"])

    def test_model_total_is_ignored(self):
        data = {"reply": "Periksa draft.", "draft": {"product_name": "Nasi", "servings": 1,
            "servings_source": "user", "servings_evidence": "satu porsi", "total_cost": 999999999,
            "ingredients": [{"name": "Beras", "quantity": 100, "quantity_unit": "gram",
                "quantity_source": "user", "quantity_evidence": "beras 100 gram",
                "buy_price": 15000, "buy_qty": 1, "buy_unit": "kg",
                "price_source": "user", "price_evidence": "beli 1 kg 15000"}]}}
        draft = setup.ModelReply.model_validate(data).draft
        preview = setup.prepare(draft, ([], [], []), ["satu porsi beras 100 gram beli 1 kg 15000"], "manual")
        self.assertTrue(preview["ready"], preview["missing"])
        self.assertEqual(preview["total_cost"], "1500.00")
        self.assertFalse(preview["is_estimated"])

    def test_sources_and_missing_values(self):
        draft = setup.Draft.model_validate({"product_name": "Nasi", "servings": 1,
            "servings_source": "estimate", "ingredients": [{"name": "Beras", "quantity": 100,
                "quantity_unit": "gram", "quantity_source": "user", "quantity_evidence": "invented",
                "buy_price": 15000, "buy_qty": 1, "buy_unit": "kg", "price_source": "estimate"}]})
        manual = setup.prepare(draft, ([], [], []), ["aku bingung"], "manual")
        self.assertFalse(manual["ready"])
        estimate = setup.prepare(draft, ([], [], []), ["aku bingung"], "estimate")
        self.assertTrue(estimate["ready"])
        self.assertTrue(estimate["is_estimated"])
        draft.ingredients[0].buy_price = None
        incomplete = setup.prepare(draft, ([], [], []), [], "estimate")
        self.assertFalse(incomplete["ready"])
        self.assertIsNone(incomplete["lines"][0]["buy_price"])

    def test_existing_cost_and_optional(self):
        ing = SimpleNamespace(id="rice", name="Beras", base_unit="kg", row_version=2,
            buy_price=20000, buy_qty=1, cost_per_base_unit=17500, needs_review=False)
        draft = setup.Draft.model_validate({"product_name": "Nasi", "servings": 1,
            "servings_source": "user", "servings_evidence": "satu porsi", "ingredients": [
                {"name": "Beras", "quantity": 100, "quantity_unit": "gram", "quantity_source": "user",
                 "quantity_evidence": "100 gram", "buy_price": 999, "buy_qty": 1,
                 "buy_unit": "gram", "price_source": "estimate"},
                {"name": "Topping", "quantity": 1, "quantity_unit": "pcs", "quantity_source": "estimate",
                 "buy_price": 100000, "buy_qty": 1, "buy_unit": "pcs", "price_source": "estimate", "is_optional": True}]})
        preview = setup.prepare(draft, ([ing], [], []), ["satu porsi 100 gram"], "estimate")
        self.assertEqual(preview["total_cost"], "1750.00")
        self.assertEqual(preview["lines"][0]["quantity"], "0.1")
        self.assertEqual(preview["lines"][0]["price_source"], "existing")
        self.assertEqual(preview["lines"][1]["line_cost"], "0")
        draft.ingredients[0].update_price = True
        self.assertFalse(setup.prepare(draft, ([ing], [], []), ["satu porsi 100 gram"], "estimate")["ready"])

    def test_existing_quantity_source_is_verified(self):
        ing = SimpleNamespace(id="rice", name="Beras", base_unit="kg", row_version=2,
            buy_price=20000, buy_qty=1, cost_per_base_unit=17500, needs_review=False)
        product = SimpleNamespace(id="menu", name="Nasi", row_version=0)
        row = SimpleNamespace(id="row", ingredient_id="rice", quantity=.1, quantity_unit="kg",
            row_version=0, deleted_at=None, is_optional=False)
        recipe = SimpleNamespace(id="recipe", product_id="menu", row_version=0,
            is_estimated=False, ingredients=[row])
        draft = setup.Draft.model_validate({"product_name": "Nasi", "servings": 1,
            "servings_source": "existing", "ingredients": [{"name": "Beras", "quantity": 100,
                "quantity_unit": "gram", "quantity_source": "existing", "price_source": "existing"}]})
        ctx = ([ing], [product], [recipe])
        preview = setup.prepare(draft, ctx, [], "manual")
        self.assertTrue(preview["ready"])
        self.assertEqual(preview["total_cost"], "1750.00")
        draft.ingredients[0].quantity = Decimal(110)
        self.assertFalse(setup.prepare(draft, ctx, [], "manual")["ready"])

    def test_claimed_user_quantity_must_match_quote(self):
        draft = setup.Draft.model_validate({"product_name": "Nasi", "servings": 1,
            "servings_source": "user", "servings_evidence": "satu porsi", "ingredients": [
                {"name": "Beras", "quantity": 200, "quantity_unit": "gram", "quantity_source": "user",
                 "quantity_evidence": "100 gram", "buy_price": 15000, "buy_qty": 1,
                 "buy_unit": "kg", "price_source": "user", "price_evidence": "beli 1 kg 15000"}]})
        preview = setup.prepare(draft, ([], [], []), ["satu porsi 100 gram beli 1 kg 15000"], "manual")
        self.assertFalse(preview["ready"])
        self.assertEqual(preview["lines"][0]["quantity_source"], "estimate")


class HppProviderProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_long_history_and_schema_repair(self):
        calls = []
        value = {"reply": "Periksa draft", "draft": {"product_name": "Nasi", "total_cost": 900000,
            "ingredients": []}}
        outputs = ["{broken", json.dumps(value)]
        async def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=outputs.pop(0))],
                usage=SimpleNamespace(input_tokens=123, output_tokens=234), model="fixture")
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        stories = [SimpleNamespace(message=f"Catatan dapur {n}: " + "cerita panjang " * 200, reply="Bisa dilanjutkan.") for n in range(12)]
        with patch.object(setup, "chat_configured", return_value=True), patch.object(setup, "get_llm_client", return_value=client):
            output, usage = await setup.generate(None, stories, ([], [], []), "manual")
        self.assertEqual([call["max_tokens"] for call in calls], [8192, 16384])
        self.assertEqual([m["content"] for m in calls[0]["messages"] if m["role"] == "user"][:12], [t.message for t in stories])
        self.assertNotIn("total_cost", output.draft.model_dump())
        self.assertEqual(usage["output_tokens"], 234)

    async def test_compaction_preserves_latest_story_and_exact_draft(self):
        calls = []
        async def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"reply":"Periksa draft","draft":{"ingredients":[]}}')],
                usage=SimpleNamespace(input_tokens=123, output_tokens=234), model="fixture")
        state = {"product_name": "Nasi", "servings": "10", "notes": "Tanpa kacang. Koreksi terbaru: pakai 120 gram.",
            "ingredients": [{"name": "Beras", "quantity": "120", "quantity_unit": "gram", "quantity_evidence": "pakai 120 gram", "price_evidence": "beli 5 kg 75000"}]}
        stories = [SimpleNamespace(message=f"Cerita {n}. " + "persiapan dapur " * 4000, reply="Periksa draft.") for n in range(6)]
        latest = "Koreksi terbaru: pakai 120 gram, tanpa kacang. " + "cerita lengkap " * 4000
        stories.append(SimpleNamespace(message=latest, reply=None))
        with patch.object(setup, "chat_configured", return_value=True), patch.object(setup, "get_llm_client", return_value=SimpleNamespace(messages=SimpleNamespace(create=create))):
            _, usage = await setup.generate(state, stories, ([], [], []), "manual")
        self.assertTrue(usage["history_compacted"])
        messages = calls[0]["messages"]
        self.assertIn(latest, [m["content"] for m in messages])
        context = json.loads(messages[-1]["content"].split('\n', 1)[1])
        self.assertEqual(context["current_draft"], state)
        self.assertEqual(usage["stored_turns"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
