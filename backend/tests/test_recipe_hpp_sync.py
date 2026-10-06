import json
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from backend.schemas.sync import SyncPayload
from backend.services.recipe_hpp_sync import get_recipe_hpp_changes, recipe_hpp_snapshot
from backend.services.unit_utils import UNIT_ALIASES


def ingredient(name='Beras', unit='gram', cost='17', review=False, deleted=None):
    return NS(name=name, base_unit=unit, cost_per_base_unit=Decimal(cost),
              needs_review=review, deleted_at=deleted)


def line(ing=None, qty=0.1, unit='kg', optional=False, deleted=None):
    return NS(ingredient=ing or ingredient(), quantity=qty, quantity_unit=unit,
              is_optional=optional, deleted_at=deleted)


def recipe(lines=None, estimated=False):
    return NS(id=uuid4(), product_id=uuid4(), is_active=True, deleted_at=None,
              is_estimated=estimated, ingredients=lines if lines is not None else [line()])


class RecipeHppTests(unittest.IsolatedAsyncioTestCase):
    def test_conversion_optional_deleted_and_nonpositive(self):
        r = recipe([line(), line(ingredient('Tambahan', 'pcs', '500'), 1, 'pcs', True),
                    line(qty=0), line(qty=-1), line(deleted='archived'),
                    line(ingredient(deleted='archived'))])
        result = recipe_hpp_snapshot(r)
        self.assertEqual(result['total_cost'], '1700.00')
        self.assertEqual(result['ingredients'][1]['line_cost'], '0')
        self.assertEqual(len(result['ingredients']), 4)

    def test_all_backend_unit_aliases(self):
        for alias, (base, multiplier) in UNIT_ALIASES.items():
            result = recipe_hpp_snapshot(recipe([line(ingredient(unit=base, cost='2'), 1, f' {alias.upper()} ')]))
            self.assertEqual(Decimal(result['total_cost']), Decimal(multiplier) * 2, alias)

    def test_unknown_and_cross_family_do_not_show_partial_total(self):
        for unit in ('ml', 'unknown'):
            result = recipe_hpp_snapshot(recipe([line(), line(unit=unit)]))
            self.assertIsNone(result['total_cost'])
            self.assertIsNone(result['ingredients'][1]['line_cost'])

    def test_round_total_once_and_estimate_provenance(self):
        r = recipe([line(ingredient(cost='0.33333333', review=True), 1, 'gram')] * 3, True)
        result = recipe_hpp_snapshot(r)
        self.assertEqual(result['total_cost'], '1.00')
        self.assertTrue(result['is_estimated'])
        self.assertTrue(result['needs_review'])
        self.assertTrue(result['ingredients'][0]['needs_review'])
        r.ingredients[0].ingredient.needs_review = False
        r.is_estimated = False
        self.assertFalse(recipe_hpp_snapshot(r)['needs_review'])
        self.assertFalse(recipe_hpp_snapshot(r)['is_estimated'])

    def test_inactive_and_deleted_are_tombstones(self):
        r = recipe()
        r.is_active = False
        self.assertIsNone(recipe_hpp_snapshot(r)['total_cost'])
        r.is_active = True
        r.deleted_at = 'archived'
        self.assertEqual(recipe_hpp_snapshot(r)['ingredients'], [])

    async def test_dependency_pull_is_brand_scoped_even_for_ingredient_only_delta(self):
        r = recipe()
        db = NS(execute=AsyncMock(return_value=NS(scalars=lambda: NS(all=lambda: [r]))))
        brand = uuid4()
        changes = SyncPayload(ingredients=[{'id': str(uuid4())}])
        result = await get_recipe_hpp_changes(db, brand, changes)
        self.assertEqual(result[0]['total_cost'], '1700.00')
        sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn('products.brand_id =', sql)
        self.assertIn('recipe_ingredients.ingredient_id IN', sql)
        self.assertIn('recipes.id IN', sql)
        db.execute.reset_mock()
        self.assertEqual(await get_recipe_hpp_changes(db, brand, SyncPayload()), [])
        db.execute.assert_not_called()

    def test_export_synthetic_protocol_for_native_regression(self):
        path = os.environ.get('HPP_SYNTHETIC_FIXTURE')
        if path:
            r = recipe([line(), line(ingredient('Tambahan', 'pcs', '500', True), 1, 'pcs', True)], True)
            r.id, r.product_id = 'recipe', 'product'
            with open(path, 'w') as f:
                json.dump(recipe_hpp_snapshot(r), f)


if __name__ == '__main__':
    unittest.main()
