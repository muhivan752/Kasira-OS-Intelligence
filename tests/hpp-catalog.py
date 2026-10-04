import json
import unittest
from decimal import Decimal
from types import SimpleNamespace as Obj
from unittest.mock import patch
from backend.services import hpp_catalog as catalog
from backend.services import hpp_setup_service as setup


def ingredient(id='rice', name='Beras', cost=17500):
    return Obj(id=id, name=name, base_unit='kg', cost_per_base_unit=Decimal(str(cost)),
        buy_price=20000, buy_qty=1, needs_review=False, row_version=0)


class CatalogTests(unittest.TestCase):
    def test_empty_and_missing_recipe_are_distinct(self):
        query = catalog.CatalogQuery(kind='overview')
        self.assertIn('0 bahan, 0 resep aktif, dan 0 menu', catalog.answer(query, ([], [], [])))
        ctx = ([], [Obj(id='menu', name='Nasi')], [])
        self.assertIn('sudah ada, tetapi belum punya resep', catalog.answer(catalog.CatalogQuery(kind='recipe_details', name='Nasi'), ctx))
        self.assertIn('belum ditemukan', catalog.answer(catalog.CatalogQuery(kind='missing_recipes', name='Ayam'), ctx))

    def test_backend_hpp_and_optional_archived_filter(self):
        rice = ingredient()
        topping = ingredient('topping', 'Topping', 999999)
        rows = [Obj(ingredient_id='rice', quantity=0.1, quantity_unit='kg', is_optional=False, deleted_at=None, notes=''),
            Obj(ingredient_id='topping', quantity=1, quantity_unit='kg', is_optional=True, deleted_at=None, notes=''),
            Obj(ingredient_id='ghost', quantity=1, quantity_unit='kg', is_optional=False, deleted_at=None, notes=''),
            Obj(ingredient_id='rice', quantity=1000, quantity_unit='kg', is_optional=False, deleted_at=True, notes='')]
        recipe = Obj(product_id='menu', ingredients=rows, is_estimated=True, notes='Tanpa kacang')
        ctx = ([rice, topping], [Obj(id='menu', name='Nasi'), Obj(id='bare', name='Teh')], [recipe])
        details = catalog.answer(catalog.CatalogQuery(kind='recipe_details', name='nasi'), ctx)
        self.assertIn('Rp1.750 per porsi', details)
        self.assertIn('0.1 kg', details)
        self.assertIn('(estimasi)', details)
        self.assertNotIn('ghost', details)
        self.assertIn('Tanpa kacang', details)
        self.assertIn('Teh', catalog.answer(catalog.CatalogQuery(kind='missing_recipes'), ctx))
        self.assertEqual(catalog.answer(catalog.CatalogQuery(kind='ingredient_usage', name='beras'), ctx), 'Beras: Nasi.')
        self.assertIn('17500 Rp/kg', catalog.answer(catalog.CatalogQuery(kind='ingredients', name='beras'), ctx))

    def test_invalid_unit_is_not_a_guessed_cost(self):
        row = Obj(ingredient_id='rice', quantity=100, quantity_unit='ml', is_optional=False, deleted_at=None, notes='')
        recipe = Obj(product_id='menu', ingredients=[row], is_estimated=False, notes='')
        ctx = ([ingredient()], [Obj(id='menu', name='Nasi')], [recipe])
        self.assertIn('belum bisa dihitung', catalog.answer(catalog.CatalogQuery(kind='recipes'), ctx))
        self.assertNotIn('Rp0', catalog.answer(catalog.CatalogQuery(kind='recipes'), ctx))


class CatalogProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_question_never_enters_estimate_completion_or_changes_draft(self):
        value = {'reply': 'Model invented something', 'action': 'answer', 'lookup': {'kind': 'ingredients'},
            'draft': {'product_name': 'Wrong replacement', 'ingredients': []}}
        calls = []
        async def create(**kwargs):
            calls.append(json.loads(json.dumps(kwargs)))
            return Obj(content=[Obj(type='text', text=json.dumps(value))], usage=Obj(input_tokens=12, output_tokens=20), model='fixture')
        ctx = ([ingredient(str(n), 'Bahan panjang fixture ' + str(n)) for n in range(700)], [], [])
        existing = {'product_name': 'Unfinished recipe', 'ingredients': []}
        with patch.object(setup, 'chat_configured', return_value=True), patch.object(setup, 'get_llm_client',
                return_value=Obj(messages=Obj(create=create))):
            result, _ = await setup.generate(existing, [Obj(message='Lihat semua bahan toko', reply=None)], ctx, 'estimate')
        self.assertEqual(result.action, 'answer')
        self.assertIsNone(result.draft)
        self.assertIn('Bahan panjang fixture 699', result.reply)
        self.assertNotIn('Model invented', result.reply)
        self.assertEqual(len(calls), 1)
        envelope = json.loads(calls[0]['messages'][-1]['content'].split('\n', 1)[1])
        self.assertEqual(envelope['current_draft'], existing)
        self.assertEqual(envelope['catalog_summary']['ingredient_count'], 700)
        self.assertLess(envelope['included_catalog_counts']['ingredients'], 700)


if __name__ == '__main__':
    unittest.main(verbosity=2)
