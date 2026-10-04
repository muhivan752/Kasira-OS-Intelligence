// Production Next.js preview uses BACKEND_INTERNAL_URL=http://127.0.0.1:8186/api/v1.
// Writes are isolated in this fixture. No merchant stock or recipes are changed.
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3107';
const id = '11111111-1111-4111-8111-111111111111';
const calls = [];
let failure = null, ingredientFailure = null, loadFailure = false, empty = false, starter = false;
const products = [
  { id: 'coffee', name: 'Kopi fixture', brand_id: id, base_price: 20000, stock_qty: 10, row_version: 1, is_active: true, stock_enabled: true },
  { id: 'legacy', name: 'Resep lama fixture', brand_id: id, base_price: 12000, stock_qty: 2, row_version: 1, is_active: true, stock_enabled: true },
];
let ingredients = [
  { id: 'beans', name: 'Biji kopi fixture', base_unit: 'kg', unit_type: 'WEIGHT', buy_price: 120000, buy_qty: 1, cost_per_base_unit: 120000, row_version: 1, ingredient_type: 'recipe' },
  { id: 'sugar', name: 'Gula fixture', base_unit: 'gram', unit_type: 'WEIGHT', buy_price: 20000, buy_qty: 1000, cost_per_base_unit: 20, row_version: 1, ingredient_type: 'recipe' },
  { id: 'optional', name: 'Topping fixture', base_unit: 'pcs', unit_type: 'COUNT', buy_price: 10000, buy_qty: 10, cost_per_base_unit: 1000, row_version: 1, ingredient_type: 'recipe' },
  ...Array.from({ length: 100 }, (_, index) => ({ id: `extra-${index}`, name: `Bahan halaman dua ${index}`, base_unit: 'pcs', unit_type: 'COUNT', buy_price: 100, buy_qty: 1, cost_per_base_unit: 100, row_version: 1, ingredient_type: 'recipe' })),
];
let recipes = [{ id: 'legacy-recipe', product_id: 'legacy', notes: 'Catatan resep dipertahankan', total_cost: 200,
  ingredients: [{ ingredient_id: 'sugar', ingredient_name: 'Gula fixture', quantity: .01, quantity_unit: 'kg', is_optional: false, notes: 'Catatan bahan dipertahankan' },
    { ingredient_id: 'optional', ingredient_name: 'Topping fixture', quantity: 2, quantity_unit: 'pcs', is_optional: true, notes: 'Tambahan terpisah' }] }];

const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {};
  const url = new URL(req.url, 'http://fixture');
  const path = url.pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body, search: url.search });
  let data = [], status = 200, detail;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Pemilik fixture', subscription_tier: starter ? 'starter' : 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = [{ id, brand_id: id, name: 'Toko fixture', slug: 'fixture', stock_mode: 'simple' }];
  else if (loadFailure && req.method === 'GET' && /\/(products|recipes|ingredients)$/.test(path)) { status = 500; detail = 'INTERNAL LOAD SECRET'; }
  else if (path.endsWith('/products')) data = empty ? [] : products.slice(Number(url.searchParams.get('skip') || 0), Number(url.searchParams.get('skip') || 0) + Number(url.searchParams.get('limit') || 100));
  else if (path.endsWith('/ingredients') && req.method === 'GET') data = ingredients.slice(Number(url.searchParams.get('skip') || 0), Number(url.searchParams.get('skip') || 0) + Number(url.searchParams.get('limit') || 100));
  else if (path.endsWith('/recipes') && req.method === 'GET') data = recipes.filter(recipe => !url.searchParams.has('product_id') || recipe.product_id === url.searchParams.get('product_id'));
  else if (req.method === 'POST' && path.endsWith('/ingredients') || req.method === 'PUT' && path.includes('/ingredients/')) {
    if (ingredientFailure) { ({ status, detail } = ingredientFailure); ingredientFailure = null; }
    else {
      const old = ingredients.find(i => i.id === path.split('/').pop());
      data = { ...(old || {}), ...body, id: old?.id || `new-${ingredients.length}`, row_version: (old?.row_version || 0) + 1, cost_per_base_unit: body.buy_price / body.buy_qty };
      ingredients = old ? ingredients.map(i => i.id === old.id ? data : i) : [...ingredients, data];
    }
  } else if (req.method === 'POST' && path.endsWith('/recipes') || req.method === 'PUT' && path.includes('/recipes/')) {
    if (failure) { ({ status, detail } = failure); failure = null; }
    else {
      const old = recipes.find(r => r.id === path.split('/').pop());
      data = { ...body, id: `recipe-${calls.length}`, product_id: old?.product_id || body.product_id,
        total_cost: body.ingredients.filter(row => !row.is_optional).reduce((sum, row) => sum + row.quantity * Number(ingredients.find(i => i.id === row.ingredient_id).cost_per_base_unit), 0) };
      recipes = [...recipes.filter(r => r.product_id !== data.product_id), data];
    }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status >= 400 ? { detail } : { success: true, data }));
});

async function checkAppearance(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${label}: document overflow`);
  const violations = await page.locator('.hpp-workspace').evaluate(root => {
    const rgb = color => color.match(/[\d.]+/g)?.slice(0, 3).map(Number);
    const lum = color => rgb(color).map(value => value / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4).reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i], 0);
    const bad = [];
    for (const el of root.querySelectorAll('*')) {
      const style = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || style.visibility === 'hidden' || el.tagName === 'OPTION' || el.closest(':disabled')) continue;
      if (['BUTTON', 'SELECT'].includes(el.tagName) || el.tagName === 'INPUT' && !['checkbox', 'radio'].includes(el.type) || el.tagName === 'A') {
        if (box.width < 43 || box.height < 43) bad.push(`target ${el.textContent || el.id}: ${box.width}x${box.height}`);
      }
      if (!Array.from(el.childNodes).some(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim())) continue;
      let bg = el;
      while (bg.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
      const ink = lum(style.color), paper = lum(getComputedStyle(bg).backgroundColor);
      const ratio = (Math.max(ink, paper) + .05) / (Math.min(ink, paper) + .05);
      if (ratio < 4.5) bad.push(`contrast ${el.textContent.trim().slice(0, 45)} ${ratio.toFixed(2)}`);
    }
    return bad;
  });
  assert.deepEqual(violations, [], label);
}

(async () => {
  await new Promise(resolve => fixture.listen(8186, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const cookies = () => context.addCookies(['token', 'tenant_id', 'outlet_id'].map(name => ({ name, value: name === 'token' ? 'fixture-token' : id, url: base })));
    await cookies();
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/dashboard/hpp`, { waitUntil: 'networkidle' });
    await page.getByLabel('Produk yang ingin dihitung').selectOption('coffee');
    await page.getByLabel('Tambahkan bahan ke resep').waitFor();
    assert(calls.some(call => call.path.endsWith('/ingredients') && call.search.includes('skip=100')), 'Ingredient list must include its second page');
    assert(await page.getByLabel('Tambahkan bahan ke resep').getByRole('option', { name: 'Bahan halaman dua 99', exact: true }).count());
    await page.getByRole('button', { name: 'Simpan resep dan HPP', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'minimal satu bahan utama' }).waitFor();
    assert.equal(calls.filter(call => call.method === 'POST' && call.path.endsWith('/recipes')).length, 0);

    await page.getByLabel('Tambahkan bahan ke resep').selectOption('beans');
    await page.getByRole('button', { name: 'Tambahkan', exact: true }).click();
    await page.getByLabel('Dipakai untuk satu porsi', { exact: true }).fill('15');
    assert.equal(await page.getByLabel('Satuan takaran Biji kopi fixture').inputValue(), 'gram');
    assert.match(await page.getByTestId('hpp-total').innerText(), /1\.800/);
    assert.equal(await page.getByLabel('Tambahkan bahan ke resep').getByRole('option', { name: 'Biji kopi fixture', exact: true }).count(), 0);

    await page.getByRole('button', { name: 'Bahan belum ada? Buat bahan baru', exact: true }).click();
    await page.getByLabel('Nama bahan').fill('Susu fixture');
    await page.getByLabel('Total harga pembelian (Rp)').fill('20000');
    await page.getByLabel('Jumlah bahan yang dibeli').fill('1');
    await page.getByLabel('Satuan pembelian').selectOption('liter');
    ingredientFailure = { status: 422, detail: [{ msg: 'Harga bahan tidak valid fixture' }] };
    await page.getByRole('button', { name: 'Simpan bahan dan gunakan' }).click();
    await page.getByRole('alert').filter({ hasText: 'Harga bahan tidak valid fixture' }).waitFor();
    assert.equal(await page.getByLabel('Nama bahan').inputValue(), 'Susu fixture');
    await page.getByRole('button', { name: 'Simpan bahan dan gunakan' }).click();
    await page.getByRole('status').filter({ hasText: 'Susu fixture: harga beli tersimpan' }).waitFor();
    await page.waitForFunction(() => document.activeElement?.id === 'hpp-add-ingredient');
    const creation = calls.filter(call => call.method === 'POST' && call.path.endsWith('/ingredients')).at(-1).body;
    assert.equal(creation.base_unit, 'ml'); assert.equal(creation.buy_qty, 1000); assert.equal(creation.buy_price, 20000);
    await page.getByLabel('Dipakai untuk satu porsi', { exact: true }).nth(1).fill('150');
    assert.match(await page.getByTestId('hpp-total').innerText(), /4\.800/);

    await page.getByRole('button', { name: 'Bahan belum ada? Buat bahan baru' }).click();
    await page.getByLabel('Nama bahan').fill('Susu fixture');
    await page.getByLabel('Total harga pembelian (Rp)').fill('20000');
    await page.getByLabel('Jumlah bahan yang dibeli').fill('1');
    await page.getByRole('button', { name: 'Simpan bahan dan gunakan' }).click();
    await page.getByRole('alert').filter({ hasText: 'nama ini sudah ada' }).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await page.getByLabel('Nama bahan').count(), 0);
    assert(await page.getByLabel('Tambahkan bahan ke resep').evaluate(el => el === document.activeElement));

    failure = { status: 500, detail: 'INTERNAL RECIPE SECRET' };
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('alert').filter({ hasText: 'Coba lagi beberapa saat' }).waitFor();
    assert.equal(await page.getByLabel('Dipakai untuk satu porsi').first().inputValue(), '15');
    assert(!(await page.locator('body').innerText()).includes('INTERNAL RECIPE SECRET'));
    failure = { status: 400, detail: 'Takaran belum valid fixture' };
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('alert').filter({ hasText: 'Takaran belum valid fixture' }).waitFor();
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('status').filter({ hasText: 'Resep tersimpan. HPP dari server' }).waitFor();
    const firstRecipe = recipes.find(recipe => recipe.product_id === 'coffee');
    assert.equal(firstRecipe.ingredients[0].quantity, .015); assert.equal(firstRecipe.ingredients[0].quantity_unit, 'kg');
    assert.equal(firstRecipe.ingredients[1].quantity, 150); assert.equal(firstRecipe.ingredients[1].quantity_unit, 'ml');
    assert.equal(firstRecipe.total_cost, 4800);
    assert.match(await page.getByTestId('hpp-total').innerText(), /4\.800/);
    assert.equal(await page.getByLabel('Dipakai untuk satu porsi').first().inputValue(), '15');
    assert(!calls.some(call => /restock|stock-mode/.test(call.path)), 'Recipe setup must not change physical stock or mode');
    loadFailure = true;
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('alert').filter({ hasText: 'Resep sudah tersimpan, tetapi harga bahan terbaru belum bisa dimuat' }).waitFor();
    assert.match(await page.getByTestId('hpp-total').innerText(), /4\.800/);
    loadFailure = false;
    await page.getByLabel('Bahan opsional, di luar HPP').first().check();
    assert.match(await page.getByTestId('hpp-total').innerText(), /3\.000/);
    await page.getByLabel('Bahan opsional, di luar HPP').first().uncheck();
    await page.getByLabel('Dipakai untuk satu porsi').first().fill('0');
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('alert').filter({ hasText: 'takaran lebih dari nol' }).waitFor();
    await page.getByLabel('Dipakai untuk satu porsi').first().fill('15');
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('status').filter({ hasText: 'Resep tersimpan' }).waitFor();
    console.log('PASS guided flow: existing/new ingredients, pagination, kg and liter conversion, duplicates, 400/422/500 retry, canonical stock quantities and server HPP.');

    await page.getByRole('button', { name: 'Ubah harga beli Susu fixture' }).click();
    await page.getByLabel('Total harga pembelian (Rp)').fill('22000');
    ingredientFailure = { status: 409, detail: 'Data sudah diubah, silakan refresh fixture' };
    await page.getByRole('button', { name: 'Simpan harga beli' }).click();
    await page.getByRole('alert').filter({ hasText: 'Data sudah diubah' }).waitFor();
    assert.equal(await page.getByLabel('Total harga pembelian (Rp)').inputValue(), '22000');
    await page.getByRole('button', { name: 'Simpan harga beli' }).click();
    await page.getByRole('status').filter({ hasText: 'Susu fixture: harga beli tersimpan' }).waitFor();
    const priceUpdate = calls.filter(call => call.method === 'PUT' && call.path.includes('/ingredients/')).at(-1).body;
    assert.equal(priceUpdate.row_version, 1); assert.equal(priceUpdate.base_unit, undefined);
    assert.match(await page.getByTestId('hpp-total').innerText(), /5\.100/);

    await page.getByLabel('Produk yang ingin dihitung').selectOption('legacy');
    await page.getByRole('button', { name: 'Konfirmasi takaran Gula fixture' }).waitFor();
    assert.match(await page.getByTestId('hpp-total').innerText(), /200/);
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('alert').filter({ hasText: 'konfirmasi satuan resep lama' }).waitFor();
    await page.getByRole('button', { name: 'Konfirmasi takaran Gula fixture' }).click();
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('status').filter({ hasText: 'Resep tersimpan' }).waitFor();
    const legacy = recipes.find(recipe => recipe.product_id === 'legacy');
    assert.equal(legacy.total_cost, 200); assert.equal(legacy.ingredients[0].quantity, 10);
    assert.equal(legacy.ingredients[0].quantity_unit, 'gram'); assert.equal(legacy.ingredients[1].is_optional, true);
    assert.equal(legacy.ingredients[0].notes, 'Catatan bahan dipertahankan'); assert.equal(legacy.notes, 'Catatan resep dipertahankan');
    console.log('PASS price updates preserve base units and optimistic versions; legacy units require review, optional ingredients and recipe notes preserved.');

    await page.getByRole('button', { name: 'Atur produk lain' }).click();
    assert.equal(await page.getByLabel('Produk yang ingin dihitung').inputValue(), '');
    assert(await page.getByLabel('Produk yang ingin dihitung').evaluate(el => el === document.activeElement));
    await page.getByLabel('Produk yang ingin dihitung').selectOption('legacy');
    await page.getByLabel('Satuan takaran Gula fixture').waitFor();

    await page.getByLabel('Dipakai untuk satu porsi').first().fill('20');
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByLabel('Produk yang ingin dihitung').selectOption('coffee');
    assert.equal(await page.getByLabel('Produk yang ingin dihitung').inputValue(), 'legacy');
    page.once('dialog', dialog => dialog.accept());
    await page.getByLabel('Produk yang ingin dihitung').selectOption('coffee');
    await page.getByLabel('Satuan takaran Biji kopi fixture').waitFor();
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.getByLabel('Produk yang ingin dihitung').inputValue(), 'coffee');
    assert.match(await page.getByTestId('hpp-total').innerText(), /5\.100/);
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => { localStorage.setItem('selaris-theme', theme); document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
      for (const width of [320, 390, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.waitForTimeout(350);
        await checkAppearance(page, `${theme} ${width}`);
        await page.getByLabel('Dipakai untuk satu porsi').first().focus();
        assert(await page.getByLabel('Dipakai untuk satu porsi').first().evaluate(el => getComputedStyle(el).outlineStyle !== 'none'));
        await page.screenshot({ path: `/tmp/selaris-hpp-${theme}-${width}.png`, fullPage: true });
      }
      await page.getByRole('button', { name: 'Ubah harga beli Susu fixture' }).click();
      await checkAppearance(page, `price form ${theme}`);
      await page.keyboard.press('Escape');
    }
    await page.setViewportSize({ width: 320, height: 1000 });
    await page.evaluate(() => document.documentElement.style.fontSize = '200%');
    await checkAppearance(page, '200% text resize');
    await page.evaluate(() => document.documentElement.style.fontSize = '');
    await page.setViewportSize({ width: 320, height: 420 });
    await page.getByRole('button', { name: 'Bahan belum ada? Buat bahan baru' }).click();
    for (const label of ['Nama bahan', 'Total harga pembelian (Rp)', 'Jumlah bahan yang dibeli']) {
      const input = page.getByLabel(label);
      await input.focus();
      assert(await input.evaluate(el => { const box = el.getBoundingClientRect(); return box.top >= 0 && box.bottom <= innerHeight; }), `${label}: focus must stay in the compressed visual viewport`);
    }
    await page.keyboard.press('Escape');
    await page.setViewportSize({ width: 320, height: 1000 });
    console.log('PASS layouts and AA: five widths, both themes, 44px controls, focus, Escape, reload and unsaved product-change guard, 200% text resize.');

    await page.getByRole('button', { name: 'Hapus Biji kopi fixture dari resep' }).click();
    assert.equal(await page.getByLabel('Satuan takaran Biji kopi fixture').count(), 0);
    await page.goto(`${base}/dashboard/hpp?product=unavailable`, { waitUntil: 'networkidle' });
    await page.getByRole('alert').filter({ hasText: 'tidak tersedia' }).waitFor();
    empty = true;
    await page.goto(`${base}/dashboard/hpp`, { waitUntil: 'networkidle' });
    await page.getByText('Belum ada produk.', { exact: false }).waitFor();
    assert.equal(await page.getByRole('link', { name: 'Tambah produk di Menu' }).getAttribute('href'), '/dashboard/menu');
    empty = false; loadFailure = true;
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByRole('alert').filter({ hasText: 'Data HPP belum bisa dimuat' }).waitFor();
    loadFailure = false;
    await page.getByRole('button', { name: 'Coba lagi', exact: true }).click();
    await page.getByLabel('Produk yang ingin dihitung').waitFor();
    loadFailure = true;
    await page.getByLabel('Produk yang ingin dihitung').selectOption('coffee');
    await page.getByRole('alert').filter({ hasText: 'Data HPP belum bisa dimuat' }).waitFor();
    loadFailure = false;
    await page.getByRole('button', { name: 'Coba lagi', exact: true }).click();
    await page.getByLabel('Satuan takaran Biji kopi fixture').waitFor();
    failure = { status: 401, detail: 'Unauthorized' };
    await page.getByRole('button', { name: 'Simpan resep dan HPP' }).click();
    await page.getByRole('alert').filter({ hasText: 'Sesi login sudah berakhir' }).waitFor();
    await cookies();
    await page.goto(`${base}/dashboard/menu`, { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Edit', exact: true }).first().click();
    await page.getByRole('button', { name: 'Resep', exact: true }).click();
    await page.getByLabel('Tambahkan bahan ke resep').waitFor();
    assert.match(await page.getByTestId('hpp-total').innerText(), /5\.100/);
    assert.equal(await page.getByRole('link', { name: 'Buka halaman Atur HPP' }).getAttribute('href'), '/dashboard/hpp?product=coffee');
    for (const path of ['/dashboard/settings', '/dashboard/bahan-baku', '/dashboard/menu', '/dashboard/laporan/hpp']) {
      await page.goto(`${base}${path}`, { waitUntil: 'networkidle' });
      const entry = page.locator('main a[href="/dashboard/hpp"]').first();
      await entry.waitFor(); await entry.click();
      await page.getByRole('heading', { name: 'Atur HPP', exact: true }).waitFor();
    }
    starter = true;
    await page.goto(`${base}/dashboard/hpp`, { waitUntil: 'networkidle' });
    await page.waitForURL(/\/dashboard\/pro/);
    assert.deepEqual(errors, []);
    console.log('PASS empty/error/loading retry, invalid product, session expiration, real entry links, Pro gating, no page errors.');
  } finally { await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
