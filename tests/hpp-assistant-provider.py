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
    menu = Obj(id='fixture-menu', name='Nasi QA', row_version=0)
    bare = Obj(id='fixture-bare', name='Teh QA', row_version=0)
    row = Obj(id='fixture-row', row_version=0, ingredient_id=rice.id, quantity=100, quantity_unit='gram',
        is_optional=False, deleted_at=None, notes='')
    recipe = Obj(id='fixture-recipe', row_version=0, product_id=menu.id, ingredients=[row], notes='', is_estimated=False)
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
    assert not any(word in output.reply.casefold() for word in ('harus diinput dulu', 'wajib ditambahkan dulu'))
    print('PASS synthetic general help: no forced recipe or draft; no DB access or merchant export')
    old = {'product_name': 'Nasi QA', 'servings': '1', 'servings_source': 'estimate',
        'ingredients': [{'name': 'Beras QA', 'quantity': '100', 'quantity_unit': 'gram',
            'quantity_source': 'estimate', 'price_source': 'existing'}]}
    history = [Obj(message='Siapkan Nasi QA.', reply='Menu dan bahan baru perlu diisi manual dulu.'),
        Obj(message='Lihat bahan resep HPP yang belum diisi', reply=None)]
    output, _ = await setup.generate(old, history, ctx, 'estimate')
    assert output.action == 'answer' and output.lookup.kind == 'missing_recipes' and not output.lookup.name, output
    assert 'Teh QA' in output.reply and output.draft is None
    print('PASS synthetic broad missing-recipe lookup despite old draft/manual advice')
    pudding = Obj(id='fixture-pudding', name='Puding QA', row_version=0)
    tea = Obj(id='fixture-tea', name='Teh QA', row_version=0)
    next_ctx = ([rice], [pudding, tea], [])
    history[-1].reply = 'Menu yang belum punya resep: Puding QA dan Teh QA.'
    history.append(Obj(message='Sekarang siapkan pudingqa dan tehqa, mulai dari puding dulu.', reply=None))
    output, _ = await setup.generate(old, history, next_ctx, 'estimate')
    assert output.action == 'edit_recipe' and output.lookup is None, output
    assert output.draft.product_name == 'Puding QA', output.draft.product_name
    preview = setup.prepare(output.draft, next_ctx, [t.message for t in history], 'estimate')
    assert preview['ready'] and preview['is_estimated'], preview['missing']
    assert len(preview['lines']) >= 2 and not any('beras' in line['name'].casefold() for line in preview['lines'])
    print('PASS synthetic multi-menu request: new first-menu estimate ready without interviewing or carrying old ingredients')
    output, _ = await setup.generate(output.draft.model_dump(mode='json'),
        [Obj(message='Bagaimana lanjut menu lain setelah resep ini saya approve?', reply=None)], next_ctx, 'estimate', status='applied')
    assert output.action == 'answer' and output.draft is None and output.lookup is None, output
    assert 'resep baru' in output.reply.casefold(), output.reply
    print('PASS synthetic applied recipe status: next menu through Resep baru; no false unsaved claim')


asyncio.run(main())
