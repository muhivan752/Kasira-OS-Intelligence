const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const output = mkdtempSync(join(tmpdir(), 'hpp-units-'));
try {
  execFileSync(process.execPath, [require.resolve('typescript/lib/tsc.js'), 'lib/hpp.ts', '--target', 'ES2020', '--module', 'commonjs', '--outDir', output, '--skipLibCheck']);
  const { convertHppQuantity, existingHppQuantity } = require(join(output, 'hpp.js'));
  const cases = [
    { qty: 15, from: 'gram', base: 'kg', cost: 120000, expectedQty: .015, expectedCost: 1800 },
    { qty: .015, from: 'kg', base: 'gram', cost: 120, expectedQty: 15, expectedCost: 1800 },
    { qty: 150, from: 'ml', base: 'liter', cost: 20000, expectedQty: .15, expectedCost: 3000 },
    { qty: .15, from: 'liter', base: 'ml', cost: 20, expectedQty: 150, expectedCost: 3000 },
    { qty: 2, from: 'ons', base: 'gram', cost: 14, expectedQty: 200, expectedCost: 2800 },
    { qty: 1, from: 'tray', base: 'pcs', cost: 2000, expectedQty: 30, expectedCost: 60000 },
    { qty: 2, from: 'pack', base: 'bungkus', cost: 500, expectedQty: 2, expectedCost: 1000 },
    { qty: .5, from: 'papan', base: 'pcs', cost: 100, expectedQty: 15, expectedCost: 1500 },
    { qty: 2, from: 'kg', base: 'ml', cost: 20, expectedQty: null },
    { qty: 2, from: 'unknown', base: 'pcs', cost: 500, expectedQty: null },
  ];
  const oracle = JSON.parse(execFileSync('python3', ['-c', `
import json, sys
from types import SimpleNamespace as S
from backend.services.unit_utils import ingredient_cost_contribution, normalize_recipe_qty
cases = json.load(sys.stdin)
results = []
for c in cases:
    original = S(quantity=c['qty'], quantity_unit=c['from'], ingredient=S(base_unit=c['base'], cost_per_base_unit=c['cost']))
    canonical = S(quantity=c['expectedQty'], quantity_unit=c['base'], ingredient=original.ingredient)
    results.append({'existing': normalize_recipe_qty(original), 'savedCost': ingredient_cost_contribution(canonical)})
print(json.dumps(results))
`], { input: JSON.stringify(cases), encoding: 'utf8' }));
  for (const [index, test] of cases.entries()) {
    const actual = convertHppQuantity(test.qty, test.from, test.base);
    if (test.expectedQty === null) assert.equal(actual, null);
    else {
      assert(Math.abs(actual - test.expectedQty) < 1e-9, `${test.from} to ${test.base}`);
      assert(Math.abs(oracle[index].savedCost - test.expectedCost) < 1e-9, 'Canonical saved quantities must produce the expected backend HPP');
    }
    assert.equal(existingHppQuantity(test.qty, test.from, test.base), oracle[index].existing, 'Unreviewed legacy preview must match backend unit rules');
  }
  for (const value of [0, -1, NaN, Infinity]) assert.equal(convertHppQuantity(value, 'gram', 'kg'), null);
  assert.equal(convertHppQuantity(2, 'satuan khusus', 'satuan khusus'), 2);
  console.log('PASS HPP unit conversions and legacy previews against the actual Python backend helper; invalid/cross-family inputs rejected.');
} finally { rmSync(output, { recursive: true, force: true }); }
