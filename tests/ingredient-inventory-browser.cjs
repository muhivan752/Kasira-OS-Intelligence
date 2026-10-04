// All mutations go to this local API fixture; production shops are never written.
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3108';
const id = '11111111-1111-4111-8111-111111111111';
const calls = [];
let failure, loadFailure = false, empty = false, starter = false;
const ingredient = (id, name, extra = {}) => ({ id, name, brand_id: 'brand', base_unit: 'gram', unit_type: 'WEIGHT', buy_price: 20000,
  buy_qty: 1000, cost_per_base_unit: 20, row_version: 1, ingredient_type: 'recipe', current_stock: 10, min_stock: 0, used_in: [], ...extra });
let items = [
  ingredient('beans', 'Biji kopi fixture', { base_unit: 'kg', buy_price: 120000, buy_qty: 1, cost_per_base_unit: 110000,
    current_stock: .5, min_stock: 1, used_in: [{ product_name: 'Kopi susu fixture', qty_per_serving: .015, unit: 'kg' }] }),
  ingredient('sugar', 'Gula fixture', { current_stock: 0, needs_review: true }),
  ingredient('unknown', 'Air fixture', { base_unit: 'ml', unit_type: 'VOLUME', current_stock: null, cost_per_base_unit: .25 }),
  ingredient('gas', 'Gas fixture', { ingredient_type: 'overhead', overhead_cost_per_day: 5000, current_stock: null }),
  ...Array.from({ length: 100 }, (_, index) => ingredient(`extra-${index}`, `Bahan pagination ${index}`)),
];
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {}, url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body, search: url.search });
  let data = [], status = 200, detail;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Pemilik fixture', subscription_tier: starter ? 'starter' : 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = [{ id, brand_id: 'brand', name: 'Toko fixture', stock_mode: 'simple' }];
  else if (req.method === 'GET' && path.endsWith('/ingredients')) {
    if (loadFailure) { status = 500; detail = 'PRIVATE DATABASE SECRET'; }
    else data = empty ? [] : items.slice(Number(url.searchParams.get('skip') || 0), Number(url.searchParams.get('skip') || 0) + Number(url.searchParams.get('limit') || 100));
  } else if (path.includes('/ingredients') && ['POST', 'PUT', 'DELETE'].includes(req.method)) {
    const itemId = path.endsWith('/restock') ? path.split('/').at(-2) : path.split('/').at(-1), old = items.find(item => item.id === itemId);
    if (failure) { ({ status, detail } = failure);
      if (failure.committed && old) old.current_stock = Number(old.current_stock || 0) + body.quantity;
      failure = undefined;
    } else if (path.endsWith('/restock')) {
      assert.equal(req.method, 'POST'); assert.equal(body.outlet_id, id); assert(body.quantity > 0);
      old.current_stock = Number(old.current_stock || 0) + body.quantity;
      data = { ...old, min_stock: null, used_in: null };
    } else if (req.method === 'DELETE') { items = items.filter(item => item.id !== itemId); data = { ok: true }; }
    else {
      data = old ? { ...old, ...body, row_version: old.row_version + 1, needs_review: false }
        : ingredient(`new-${calls.length}`, body.name, { ...body, current_stock: null });
      if (data.ingredient_type !== 'overhead') data.cost_per_base_unit = body.buy_price / body.buy_qty;
      items = old ? items.map(item => item.id === old.id ? data : item) : [...items, data];
      data = { ...data, current_stock: null, min_stock: null, used_in: null };
    }
    await new Promise(resolve => setTimeout(resolve, 120));
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status < 400 ? { data } : { detail }));
});

async function visual(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${label}: page overflow`);
  const problems = await page.locator('.inventory-workspace').evaluate(root => {
    const rgb = color => color.match(/[\d.]+/g).slice(0, 3).map(Number);
    const lum = color => rgb(color).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const bad = [];
    for (const el of root.querySelectorAll('*')) {
      const style = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || style.visibility === 'hidden' || el.tagName === 'OPTION' || el.closest(':disabled')) continue;
      if (['BUTTON', 'SELECT', 'INPUT', 'TEXTAREA', 'A'].includes(el.tagName) && (box.width < 43 || box.height < 43)) bad.push(`target ${el.textContent || el.id}: ${box.width}x${box.height}`);
      if (!Array.from(el.childNodes).some(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim())) continue;
      let bg = el; while (bg.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
      const ink = lum(style.color), paper = lum(getComputedStyle(bg).backgroundColor), ratio = (Math.max(ink, paper) + .05) / (Math.min(ink, paper) + .05);
      if (ratio < 4.5) bad.push(`contrast ${el.textContent.trim().slice(0, 45)} ${ratio.toFixed(2)}`);
    }
    for (const input of root.querySelectorAll('input[placeholder]')) {
      const ink = lum(getComputedStyle(input, '::placeholder').color), paper = lum(getComputedStyle(input).backgroundColor);
      const ratio = (Math.max(ink, paper) + .05) / (Math.min(ink, paper) + .05);
      if (ratio < 4.5) bad.push(`placeholder ${input.placeholder}: ${ratio.toFixed(2)}`);
    }
    return bad;
  });
  assert.deepEqual(problems, [], label);
}

(async () => {
  await new Promise(resolve => fixture.listen(8187, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const cookies = () => context.addCookies(['token', 'tenant_id', 'outlet_id'].map(name => ({ name, value: name === 'token' ? 'fixture-token' : id, url: base })));
    await cookies();
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const row = id => page.locator(`[data-ingredient="${id}"]`), dialog = page.getByRole('dialog');
    const button = name => dialog.getByRole('button', { name, exact: true });
    const close = async () => { if (await dialog.count()) await dialog.getByRole('button', { name: /^Tutup / }).click(); };
    const go = async () => { await page.goto(`${base}/dashboard/bahan-baku`, { waitUntil: 'networkidle' }); await page.getByLabel('Cari bahan', { exact: true }).waitFor(); };
    await go();
    assert(calls.some(call => call.search.includes('skip=100')), 'Inventory must load more than 100 ingredients');
    assert.equal(await row('extra-99').count(), 1);
    assert.match(await row('unknown').innerText(), /Belum dicatat/); assert.doesNotMatch(await row('unknown').innerText(), /Stok habis/);
    assert.match(await row('unknown').innerText(), /0,25/); assert.match(await row('sugar').innerText(), /Stok habis/);
    assert.match(await row('beans').innerText(), /110\.000/); assert.match(await row('beans').innerText(), /120\.000/);
    assert.equal(await row('gas').count(), 0);
    await page.getByLabel('Tampilkan', { exact: true }).selectOption('low'); assert.equal(await page.locator('.inventory-row').count(), 2);
    await page.getByLabel('Tampilkan', { exact: true }).selectOption('unknown'); assert.equal(await page.locator('.inventory-row').count(), 1);
    await page.getByLabel('Tampilkan', { exact: true }).selectOption('review'); assert.equal(await row('sugar').count(), 1);
    await page.getByLabel('Tampilkan', { exact: true }).selectOption('unused'); assert.equal(await row('beans').count(), 0);
    await page.getByLabel('Tampilkan', { exact: true }).selectOption('all');
    await page.getByLabel('Cari bahan', { exact: true }).fill('missing'); await page.getByText('Tidak ada hasil yang sesuai', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Reset pencarian' }).click();
    await row('beans').getByRole('button', { name: 'Lihat pemakaian' }).click(); await dialog.getByText('Kopi susu fixture', { exact: true }).waitFor();
    assert.match(await dialog.innerText(), /0,015 kg per porsi/); await close();
    await row('beans').getByRole('button', { name: 'Hapus Biji kopi fixture' }).click();
    assert.match(await dialog.innerText(), /Lepaskan bahan/); assert.equal(await button('Hapus bahan').count(), 0); await close();
    console.log('PASS inventory read: pagination, recorded/unknown stock, fractional and server HPP, filters, search, usage and deletion guard.');

    await page.getByRole('button', { name: 'Tambah bahan', exact: true }).click();
    assert.equal(await dialog.getByLabel('Total harga pembelian (Rp)').inputValue(), '');
    await button('Simpan bahan').click(); await dialog.getByRole('alert').waitFor();
    await dialog.getByLabel('Nama bahan', { exact: true }).fill('Gula fixture'); await dialog.getByLabel('Total harga pembelian (Rp)').fill('20000');
    await dialog.getByLabel('Jumlah yang dibeli').fill('1'); await dialog.getByLabel('Satuan pembelian').selectOption('kg');
    await button('Simpan bahan').click(); await dialog.getByText(/Nama ini sudah ada/).waitFor();
    await dialog.getByLabel('Nama bahan', { exact: true }).fill('Tepung baru fixture');
    await button('Simpan bahan').click(); await dialog.waitFor({ state: 'hidden' });
    const create = calls.findLast(call => call.method === 'POST' && call.path.endsWith('/ingredients'));
    assert.equal(create.body.base_unit, 'gram'); assert.equal(create.body.buy_qty, 1000); assert.equal(create.body.buy_price, 20000);
    assert.equal(calls.filter(call => call.path.endsWith('/restock')).length, 0, 'Creating ingredient must not restock');
    const newId = items.find(item => item.name === 'Tepung baru fixture').id;
    assert.match(await row(newId).innerText(), /Belum dicatat/);
    await page.getByRole('button', { name: 'Catat stok Tepung baru fixture' }).click();
    await button('Simpan tambahan stok').click(); await dialog.getByText(/lebih dari nol/).waitFor();
    await dialog.getByLabel('Jumlah yang ditambahkan').fill('2'); await dialog.getByLabel('Satuan tambahan stok').selectOption('kg');
    await dialog.getByLabel('Catatan (opsional)').fill('Pembelian fixture');
    await dialog.getByText('Stok setelah disimpan: 2.000 gram', { exact: true }).waitFor();
    await button('Simpan tambahan stok').evaluate(el => { el.click(); el.click(); }); await dialog.waitFor({ state: 'hidden' });
    assert.equal(calls.filter(call => call.path.endsWith('/restock')).length, 1, 'Double click must not duplicate stock');
    assert.equal(calls.findLast(call => call.path.endsWith('/restock')).body.quantity, 2000);
    assert.match(await row(newId).innerText(), /2\.000 gram/);

    await row('beans').getByRole('button', { name: 'Ubah harga' }).click();
    await dialog.getByLabel('Satuan pembelian').selectOption('gram'); await dialog.getByLabel('Jumlah yang dibeli').fill('500');
    await dialog.getByLabel('Total harga pembelian (Rp)').fill('65000');
    failure = { status: 409, detail: 'Data sudah diubah, silakan refresh' };
    await button('Simpan harga').click(); await dialog.getByText(/silakan refresh/).waitFor();
    assert.equal(calls.findLast(call => call.method === 'PUT').body.buy_qty, .5);
    assert.equal(await dialog.getByLabel('Jumlah yang dibeli').inputValue(), '500');
    await dialog.getByRole('button', { name: 'Muat ulang data', exact: true }).click(); await dialog.waitFor({ state: 'hidden' });
    await row('beans').getByRole('button', { name: 'Ubah harga' }).click();
    await dialog.getByLabel('Total harga pembelian (Rp)').fill('130000'); await button('Simpan harga').click(); await dialog.waitFor({ state: 'hidden' });
    const edit = calls.findLast(call => call.method === 'PUT');
    assert.equal(edit.body.row_version, 1); assert.equal(edit.body.base_unit, undefined); assert.equal(edit.body.unit_type, undefined);
    assert.match(await row('beans').innerText(), /0,5 kg/); assert.match(await row('beans').innerText(), /Dipakai di 1 resep/);

    for (const status of [400, 422]) {
      await row('sugar').getByRole('button', { name: 'Tambah stok' }).click(); await dialog.getByLabel('Jumlah yang ditambahkan').fill('10');
      failure = { status, detail: `Validasi fixture ${status}` }; await button('Simpan tambahan stok').click(); await dialog.getByText(`Validasi fixture ${status}`).waitFor();
      assert.equal(await dialog.getByLabel('Jumlah yang ditambahkan').inputValue(), '10');
      await button('Simpan tambahan stok').click(); await dialog.waitFor({ state: 'hidden' });
    }
    await row('sugar').getByRole('button', { name: 'Tambah stok' }).click(); await dialog.getByLabel('Jumlah yang ditambahkan').fill('5');
    failure = { status: 500, detail: 'PRIVATE SAVE SECRET', committed: true };
    await button('Simpan tambahan stok').click(); await dialog.getByText(/Hasil penyimpanan belum dapat dipastikan/).waitFor();
    assert.equal(await button('Simpan tambahan stok').isDisabled(), true);
    assert.doesNotMatch(await dialog.innerText(), /PRIVATE SAVE/);
    const stockCalls = calls.filter(call => call.path.endsWith('/restock')).length;
    await dialog.getByRole('button', { name: 'Periksa data terbaru' }).click(); await dialog.waitFor({ state: 'hidden' });
    assert.equal(calls.filter(call => call.path.endsWith('/restock')).length, stockCalls); assert.match(await row('sugar').innerText(), /25 gram/);
    assert.equal(await page.getByRole('button', { name: 'Tambah bahan', exact: true }).evaluate(el => el === document.activeElement), true);
    await row('sugar').getByRole('button', { name: 'Tambah stok' }).click(); await dialog.getByLabel('Jumlah yang ditambahkan').fill('1');
    await page.route('**/dashboard/bahan-baku', route => route.request().method() === 'POST' ? route.abort('failed') : route.continue());
    await button('Simpan tambahan stok').click(); await dialog.getByText(/Hasil penyimpanan belum dapat dipastikan/).waitFor();
    assert.equal(await button('Simpan tambahan stok').isDisabled(), true);
    await page.unroute('**/dashboard/bahan-baku'); page.once('dialog', d => d.accept()); await close(); await dialog.waitFor({ state: 'hidden' });
    assert.equal(calls.filter(call => call.path.endsWith('/restock')).length, stockCalls); assert.match(await row('sugar').innerText(), /25 gram/);
    console.log('PASS inventory writes: separate create/restock, kg conversion, double click guard, version conflicts, preserved stock/usage, validation retry and uncertain result reconciliation.');

    await page.getByRole('button', { name: 'Tambah bahan', exact: true }).click();
    await dialog.getByLabel('Nama bahan', { exact: true }).fill('Susu gratis fixture'); await dialog.getByLabel('Total harga pembelian (Rp)').fill('0');
    await dialog.getByLabel('Jumlah yang dibeli').fill('1'); await dialog.getByLabel('Satuan pembelian', { exact: true }).selectOption('liter');
    await button('Simpan bahan').click(); await dialog.waitFor({ state: 'hidden' });
    const volume = calls.findLast(call => call.method === 'POST' && call.path.endsWith('/ingredients'));
    assert.equal(volume.body.base_unit, 'ml'); assert.equal(volume.body.buy_qty, 1000); assert.equal(volume.body.buy_price, 0);

    await page.getByRole('button', { name: /^Biaya operasional/ }).click(); assert.equal(await page.locator('.inventory-row').count(), 1);
    assert.equal(await row('gas').getByRole('button', { name: 'Tambah stok' }).count(), 0);
    await page.getByRole('button', { name: 'Tambah biaya', exact: true }).click();
    await dialog.getByLabel('Nama biaya').fill('Sewa fixture'); await dialog.getByLabel('Estimasi biaya per hari (Rp)').fill('10000');
    await button('Simpan biaya').click(); await dialog.waitFor({ state: 'hidden' });
    assert.equal(calls.findLast(call => call.method === 'POST' && call.path.endsWith('/ingredients')).body.ingredient_type, 'overhead');
    await row('gas').getByRole('button', { name: 'Ubah biaya' }).click(); await dialog.getByLabel('Estimasi biaya per hari (Rp)').fill('6000');
    await button('Simpan biaya').click(); await dialog.waitFor({ state: 'hidden' });
    assert.deepEqual(Object.keys(calls.findLast(call => call.method === 'PUT').body).sort(), ['name', 'overhead_cost_per_day', 'row_version']);
    await row('gas').getByRole('button', { name: 'Hapus Gas fixture' }).click(); await button('Hapus bahan').click(); await dialog.waitFor({ state: 'hidden' }); assert.equal(await row('gas').count(), 0);
    await page.getByRole('button', { name: /^Bahan resep/ }).click();

    for (const theme of ['light', 'dark']) for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(theme => { localStorage.setItem('selaris-theme', theme); document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
      await visual(page, `list ${theme} ${width}`);
      await page.getByRole('button', { name: 'Tambah bahan', exact: true }).click(); await visual(page, `form ${theme} ${width}`);
      if ([320, 1440].includes(width)) await page.screenshot({ path: `/tmp/selaris-inventory-form-${theme}-${width}.png` });
      for (let tab = 0; tab < 8; tab++) {
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => !!document.activeElement.closest('dialog')), true);
      }
      await page.keyboard.press('Shift+Tab');
      assert.equal(await page.evaluate(() => !!document.activeElement.closest('dialog')), true);
      assert.equal(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'solid');
      await page.keyboard.press('Escape'); await dialog.waitFor({ state: 'hidden' });
      assert.equal(await page.getByRole('button', { name: 'Tambah bahan', exact: true }).evaluate(el => el === document.activeElement), true);
      await row('beans').getByRole('button', { name: 'Tambah stok' }).click(); await dialog.getByLabel('Jumlah yang ditambahkan').fill('1');
      if ([320, 1440].includes(width)) await page.screenshot({ path: `/tmp/selaris-inventory-stock-${theme}-${width}.png` });
      await visual(page, `stock ${theme} ${width}`); page.once('dialog', d => d.accept()); await close();
      await row('beans').getByRole('button', { name: 'Ubah harga' }).click(); await visual(page, `price ${theme} ${width}`); await close();
      await page.getByRole('button', { name: /^Biaya operasional/ }).click(); await page.getByRole('button', { name: 'Tambah biaya', exact: true }).click();
      await visual(page, `overhead ${theme} ${width}`); await close(); await page.getByRole('button', { name: /^Bahan resep/ }).click();
      if ([320, 1440].includes(width)) await page.screenshot({ path: `/tmp/selaris-inventory-${theme}-${width}.png` });
    }
    await page.setViewportSize({ width: 320, height: 420 }); await page.getByRole('button', { name: 'Tambah bahan', exact: true }).click();
    await dialog.getByLabel('Jumlah yang dibeli').focus();
    const focused = await dialog.getByLabel('Jumlah yang dibeli').boundingBox(); assert(focused.y >= 0 && focused.y + focused.height <= 420);
    await close(); await page.evaluate(() => document.documentElement.style.fontSize = '32px'); await visual(page, '200% text');
    await page.getByRole('button', { name: 'Tambah bahan', exact: true }).click(); await visual(page, '200% form'); await close();
    await page.evaluate(() => document.documentElement.style.fontSize = '');
    await page.getByRole('button', { name: 'Tambah bahan', exact: true }).click(); await dialog.getByLabel('Nama bahan', { exact: true }).fill('Draft fixture');
    page.once('dialog', d => d.dismiss()); await page.keyboard.press('Escape'); assert.equal(await dialog.count(), 1);
    assert.equal(await dialog.getByLabel('Nama bahan', { exact: true }).inputValue(), 'Draft fixture');
    page.once('dialog', d => d.accept()); await close();

    loadFailure = true; await page.goto(`${base}/dashboard/bahan-baku`, { waitUntil: 'networkidle' });
    await page.getByText('Daftar bahan belum bisa dimuat. Coba lagi.', { exact: true }).waitFor(); assert.doesNotMatch(await page.locator('main').innerText(), /PRIVATE DATABASE/);
    loadFailure = false;
    await page.route('**/dashboard/bahan-baku', route => route.request().method() === 'POST' ? route.abort('failed') : route.continue());
    await page.getByRole('button', { name: 'Muat ulang', exact: true }).click();
    await page.getByText('Daftar bahan belum bisa dimuat. Coba lagi.', { exact: true }).waitFor();
    await page.unroute('**/dashboard/bahan-baku');
    await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await row('beans').waitFor();
    empty = true; await go(); await page.getByText('Belum ada bahan', { exact: true }).waitFor();
    await page.getByRole('button', { name: /^Biaya operasional/ }).click(); await page.getByRole('button', { name: 'Tambah biaya pertama' }).waitFor(); empty = false;
    await go(); await row('sugar').getByRole('button', { name: 'Tambah stok' }).click(); await dialog.getByLabel('Jumlah yang ditambahkan').fill('1');
    failure = { status: 401, detail: 'expired' }; await button('Simpan tambahan stok').click(); await dialog.getByRole('link', { name: 'Masuk kembali' }).waitFor();
    await cookies(); starter = true; await page.goto(`${base}/dashboard/bahan-baku`, { waitUntil: 'networkidle' }); await page.waitForURL(/\/dashboard\/pro/);
    assert.deepEqual(errors, []);
    console.log('PASS inventory: pagination, stock vs unknown, fractional/server cost, search/filter, usage/delete guard, blank create, unit conversion, separate stock, double click, price row_version, stock preservation, 400/422/409/500 uncertainty/401, overhead, load retry/empty/Pro, 5 widths × 2 themes AA/44px, dialog keyboard/focus/draft, 200% text and short viewport. Fixture writes only.');
  } finally { await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
