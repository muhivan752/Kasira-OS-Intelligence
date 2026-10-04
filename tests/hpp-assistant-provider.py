"""Catalog questions against the configured provider using only synthetic data."""
import asyncio
import importlib.util
import sys
from decimal import Decimal
from types import SimpleNamespace as Obj


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load('backend.services.unit_utils', '/tmp/hpp_unit_qa.py')
load('backend.services.hpp_math', '/tmp/hpp_math_qa.py')
load('backend.services.hpp_catalog', '/tmp/hpp_catalog_qa.py')
setup = load('backend.services.hpp_setup_service', '/tmp/hpp_setup_qa.py')


async def main():
    rice = Obj(id='fixture-rice', name='Beras QA', base_unit='gram', cost_per_base_unit=Decimal('17'),
        buy_price=17000, buy_qty=1000, needs_review=False, row_version=1)
    menu = Obj(id='fixture-menu', name='Nasi QA')
    bare = Obj(id='fixture-bare', name='Teh QA')
    row = Obj(ingredient_id=rice.id, quantity=100, quantity_unit='gram',
        is_optional=False, deleted_at=None, notes='')
    recipe = Obj(id='fixture-recipe', product_id=menu.id, ingredients=[row], notes='', is_estimated=False)
    ctx = ([rice], [menu, bare], [recipe])
    draft = {'product_name': 'Draft belum disimpan QA', 'ingredients': []}
    cases = [
        ('Cek bahan dan resep yang tersimpan sekarang, ada atau masih kosong?', 'overview', ([], [], []), '0 bahan, 0 resep aktif'),
        ('Bahan apa saja yang sudah tersimpan di toko?', 'ingredients', ctx, 'Beras QA'),
        ('Lihat seluruh resep yang ada sekarang beserta HPP-nya.', 'recipes', ctx, 'Rp1.700 per porsi'),
        ('Menu apa yang belum punya resep?', 'missing_recipes', ctx, 'Teh QA'),
        ('Apa bahan dan takaran resep Nasi QA yang sudah tersimpan?', 'recipe_details', ctx, '100 gram'),
        ('Beras QA dipakai di resep apa saja?', 'ingredient_usage', ctx, 'Nasi QA'),
    ]
    for message, kind, context, expected in cases:
        output, _ = await setup.generate(draft, [Obj(message=message, reply=None)], context, 'estimate')
        assert output.action == 'answer' and output.draft is None, (kind, output)
        assert output.lookup and output.lookup.kind == kind, (kind, output.lookup)
        assert expected in output.reply, (kind, output.reply)
        print('PASS synthetic catalog question:', kind)
    output, _ = await setup.generate(None, [Obj(message='Boleh mulai menyusun resep kalau bahan belum diinput? Jelaskan singkat caranya.', reply=None)], ([], [], []), 'estimate')
    assert output.action == 'answer' and output.draft is None and output.lookup is None, output
    assert 'Mau bikin menu apa?' not in output.reply
    print('PASS synthetic general help: no forced recipe or draft; no DB access or merchant export')


asyncio.run(main())
