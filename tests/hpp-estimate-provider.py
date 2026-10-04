"""Synthetic inputs only. No database access or merchant payloads."""
import asyncio
import importlib.util
import sys
from types import SimpleNamespace

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
    oil = SimpleNamespace(id='synthetic-oil', name='Minyak Goreng', base_unit='kg',
        cost_per_base_unit=26000, buy_price=52000, buy_qty=2, row_version=2, needs_review=False)
    egg = SimpleNamespace(id='synthetic-egg', name='Telur Ayam', base_unit='pcs',
        cost_per_base_unit=2250, buy_price=45000, buy_qty=20, row_version=1, needs_review=False)
    ctx = ([oil, egg], [], [])
    saved_draft = {'product_name': 'Mi goreng telur QA', 'servings': '1', 'servings_source': 'estimate',
        'ingredients': [
            {'name': 'Mie Telur', 'quantity': '125', 'quantity_unit': 'gram', 'quantity_source': 'estimate', 'price_source': 'estimate'},
            {'name': 'Telur Ayam', 'quantity': '1', 'quantity_unit': 'pcs', 'quantity_source': 'estimate', 'price_source': 'existing'},
            {'name': 'Kecap Manis', 'quantity': '12', 'quantity_unit': 'ml', 'quantity_source': 'estimate', 'price_source': 'estimate'},
            {'name': 'Minyak Goreng', 'quantity': '10', 'quantity_unit': 'ml', 'quantity_source': 'estimate', 'price_source': 'existing'}]}
    story = 'Bantu lengkapi estimasi menu mi goreng telur QA. Harga mie dan kecap belum ada. Takaran minyak boleh diperkirakan mengikuti satuan bahan toko.'
    history = [SimpleNamespace(message=story, reply=None)]
    mode = setup.conversation_mode(story, 'manual')
    assert mode == 'estimate'
    output, _ = await setup.generate(saved_draft, history, ctx, mode)
    preview = setup.prepare(output.draft, ctx, [story], mode)
    print('SYNTHETIC_REPLY:', output.reply)
    print('VALIDATION:', {'ready': preview['ready'], 'missing': preview['missing'], 'ingredients': len(preview['lines'])})
    assert preview['ready'], preview['missing']
    assert preview['is_estimated'] and len(preview['lines']) >= 4
    for line in preview['lines']:
        if line['ingredient_id']:
            assert line['action'] == 'reuse'
    history[0].reply = output.reply
    correction = 'telurnya 2 butir saja, jangan tambah nori'
    history.append(SimpleNamespace(message=correction, reply=None))
    corrected, _ = await setup.generate(output.draft.model_dump(mode='json'), history, ctx, mode)
    reviewed = setup.prepare(corrected.draft, ctx, [t.message for t in history], mode)
    assert reviewed['ready'], reviewed['missing']
    egg_line = next(line for line in reviewed['lines'] if line['ingredient_id'] == 'synthetic-egg')
    assert float(egg_line['quantity']) == 2 and egg_line['quantity_source'] == 'user'
    assert not any('nori' in line['name'].lower() for line in reviewed['lines'])
    single = 'aku mau buat nasi ayam penyet'
    draft, _ = await setup.generate(None, [SimpleNamespace(message=single, reply=None)], ([], [], []), 'estimate')
    first = setup.prepare(draft.draft, ([], [], []), [single], 'estimate')
    assert first['ready'] and first['is_estimated'], first['missing']
    print('PASS synthetic missing prices and oil units repaired, fixture costs unchanged, exact correction preserved; single-menu estimate ready; no database access or merchant export')

asyncio.run(main())
