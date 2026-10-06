const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const id = '11111111-1111-4111-8111-111111111111';
const recipeId = '22222222-2222-4222-8222-222222222222';
let permissions = ['stock.view'], fail = false, uncertain = false, empty = false;
let stock = 10, flour = 200;
const calls = [];
const outlets = [{ id, name: 'QA outlet', brand_id: id, stock_mode: 'simple' }, { id: recipeId, name: 'QA recipe outlet', brand_id: recipeId, stock_mode: 'recipe' }];
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const part of req) raw += part;
  const body = raw ? JSON.parse(raw) : {};
  const url = new URL(req.url, 'http://qa'), path = url.pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body, query: url.searchParams });
  let data = [], status = 200;
  if (path.endsWith('/auth/access')) data = { enforcement_mode: 'managed', permissions, outlets, user_id: id, tenant_id: id };
  else if (path.endsWith('/users/me')) data = { id, full_name: 'QA staff', subscription_tier: 'pro' };
  else if (path.includes('/outlets/')) data = outlets.find(o => path.endsWith(o.id));
  else if (path.endsWith('/products')) {
    if (fail) status = 503;
    else data = empty ? [] : [{ id, name: 'QA coffee', stock_enabled: true, stock_qty: stock, buy_price: null }];
  } else if (path.endsWith('/ingredients')) data = empty ? [] : [{ id, name: 'QA flour', current_stock: flour, base_unit: 'gram', cost_per_base_unit: null }];
  else if (path.endsWith('/restock') || path.endsWith('/stock-count')) {
    if (!permissions.includes(path.endsWith('/stock-count') ? 'stock.adjust' : 'stock.receive')) status = 403;
    else {
      if (path.includes('/ingredients/')) flour += body.quantity;
      else stock = body.counted_qty ?? stock + body.quantity;
      if (uncertain) status = 503;
      data = { id };
    }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status === 200 ? { success: true, data } : { detail: status === 503 ? 'QA request not confirmed' : 'Tidak diizinkan' }));
});
async function check(page, label) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${label}: horizontal overflow`);
  const bounds = await page.evaluate(() => [...document.querySelectorAll('main,.finance-workspace,.f-panel')].map(el => ({tag: el.className, width: el.clientWidth, scroll: el.scrollWidth, left: el.getBoundingClientRect().left, right: el.getBoundingClientRect().right})));
  for (const box of bounds) assert(box.scroll <= box.width + 1 && box.right <= (await page.viewportSize()).width + 1, `${label}: inner overflow ${JSON.stringify(bounds)}`);
  const samples = await page.evaluate(() => Array.from(document.querySelectorAll('.finance-workspace h1,.finance-workspace h2,.finance-workspace h3,.finance-workspace p,.finance-workspace button,.finance-workspace a,.finance-workspace label,.finance-workspace strong')).flatMap(el => {
    if (el.disabled || !el.getClientRects().length) return [];
    const style = getComputedStyle(el); let current = el, bg = 'rgb(255,255,255)';
    while (current) { const color = getComputedStyle(current).backgroundColor; if (color.startsWith('rgb(')) { bg = color; break; } current = current.parentElement; }
    return [{ text: el.textContent.slice(0, 30), fg: style.color, bg, min: parseFloat(style.fontSize) >= 24 || parseFloat(style.fontSize) >= 18.67 && +style.fontWeight >= 700 ? 3 : 4.5 }];
  }));
  const luminance = color => {
    const rgb = color.match(/[\d.]+/g).slice(0, 3).map(v => { const n = +v / 255; return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4; });
    return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
  };
  for (const s of samples) { const a = luminance(s.fg), b = luminance(s.bg); assert((Math.max(a, b) + .05) / (Math.min(a, b) + .05) >= s.min, `${label}: contrast ${s.text}`); }
  console.log(`PASS ${label}: layout and contrast`);
}
(async () => {
  await new Promise(resolve => fixture.listen(8188, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 320, height: 760 } });
  await context.tracing.start({ screenshots: true, snapshots: true });
  await context.addCookies([{ name: 'token', value: 'fixture-staff', domain: '127.0.0.1', path: '/' }, { name: 'tenant_id', value: id, domain: '127.0.0.1', path: '/' }]);
  const page = await context.newPage(), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.setDefaultTimeout(10000);
  try {
    await page.goto('http://127.0.0.1:3188/dashboard/operasional');
    await page.getByRole('heading', { name: 'Stok QA outlet', exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: /Terima barang/ }).count(), 0);
    assert.equal(await page.getByRole('button', { name: /Stok opname/ }).count(), 0);
    assert.equal(await page.getByRole('link', { name: 'Keuangan', exact: true }).count(), 0);
    await check(page, 'read-only staff 320');
    await page.getByRole('button', { name: 'Buka menu', exact: true }).click();
    await page.getByRole('link', { name: 'Operasional', exact: true }).click();
    await page.getByRole('button', { name: 'Buka menu', exact: true }).click(); await page.keyboard.press('Escape');
    console.log('PASS staff navigation');
    permissions = ['stock.view', 'stock.receive', 'stock.adjust', 'pos.sell'];
    await page.getByRole('button', { name: 'Muat ulang akses dan stok' }).click();
    await page.getByRole('button', { name: /Terima barang/ }).click();
    assert(await page.getByLabel('Jumlah (pcs)').evaluate(el => el === document.activeElement));
    await page.getByLabel('Jumlah (pcs)').fill('5'); await page.getByRole('button', { name: 'Simpan stok', exact: true }).click();
    await page.getByText('15 pcs', { exact: true }).waitFor();
    await page.getByRole('button', { name: /Stok opname/ }).click();
    await page.getByLabel('Jumlah (pcs)').fill('8'); await page.getByRole('button', { name: 'Simpan stok', exact: true }).click();
    await page.getByText('8 pcs', { exact: true }).waitFor();
    uncertain = true;
    await page.getByRole('button', { name: /Terima barang/ }).click(); await page.getByLabel('Jumlah (pcs)').fill('2'); await page.getByRole('button', { name: 'Simpan stok', exact: true }).click();
    await page.getByRole('alert').waitFor();
    assert(await page.getByRole('button', { name: /Terima barang/ }).isDisabled());
    await page.getByRole('button', { name: 'Tutup', exact: true }).click();
    assert(await page.getByRole('button', { name: /Terima barang/ }).isDisabled());
    uncertain = false;
    await page.getByRole('button', { name: 'Muat ulang akses dan stok' }).click(); await page.getByText('10 pcs', { exact: true }).waitFor();
    assert.equal(calls.filter(c => c.method === 'POST').length, 3);
    await page.getByLabel('Outlet', { exact: true }).selectOption(recipeId);
    await page.getByRole('heading', { name: 'Bahan resep' }).waitFor();
    await page.getByRole('button', { name: /Terima barang/ }).click(); await page.getByLabel('Jumlah (gram)').fill('2.5'); await page.getByRole('button', { name: 'Simpan stok', exact: true }).click();
    await page.getByText('202,5 gram', { exact: true }).waitFor();
    assert.equal(calls.filter(c => c.method === 'POST').at(-1).body.outlet_id, recipeId);
    for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 }); await check(page, `${width} light`);
      await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await check(page, `${width} dark`);
      await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    }
    await page.setViewportSize({ width: 320, height: 760 });
    await page.evaluate(() => document.documentElement.style.fontSize = '200%'); await check(page, '200% text'); await page.evaluate(() => document.documentElement.style.fontSize = '');
    await page.keyboard.press('Escape'); await page.waitForTimeout(400);
    await page.screenshot({ path: '/tmp/selaris-pos-access-stock.png', fullPage: true });
    await page.getByRole('link', { name: 'Unduh aplikasi POS' }).click(); await page.waitForURL('**/download');
    await page.goto('http://127.0.0.1:3188/dashboard/operasional');
    fail = true; await page.getByRole('button', { name: 'Muat ulang akses dan stok' }).click(); await page.getByRole('alert').waitFor();
    fail = false; empty = true; await page.getByRole('button', { name: 'Muat ulang akses dan stok' }).click(); await page.getByText('Belum ada barang untuk outlet ini.').waitFor();
    empty = false; permissions = ['hris.self']; await page.getByRole('button', { name: 'Muat ulang akses dan stok' }).click(); await page.getByText('Izin melihat stok belum diberikan untuk akun ini.').waitFor();
    assert.equal(await page.getByRole('button', { name: /Terima barang/ }).count(), 0);
    assert.equal(await page.getByRole('link', { name: 'Unduh aplikasi POS' }).count(), 0);
    permissions = ['pos.cash.manage']; await page.goto('http://127.0.0.1:3188/dashboard/operasional'); await page.getByRole('link', { name: 'Unduh aplikasi POS' }).waitFor();
    assert.equal(await page.getByRole('button', {name: /Terima barang/}).count(), 0);
    await page.getByRole('button', { name: 'Muat ulang akses dan stok' }).focus(); await page.keyboard.press('Tab');
    assert(await page.evaluate(() => document.activeElement.tagName !== 'BODY' && getComputedStyle(document.activeElement).outlineStyle !== 'none'));
    assert.deepEqual(errors, []);
    console.log('PASS scoped receipt/count, recipe units, uncertain request lock/no retry, reload, empty/error, revocation, download, keyboard and theme controls');
  } catch (error) { console.error(error); console.error(await page.locator('body').innerText()); await page.screenshot({path: '/tmp/selaris-pos-access-browser-failure.png', fullPage: true}); throw error; } finally {
    await context.tracing.stop({ path: '/tmp/selaris-pos-access-browser-trace.zip' });
    await browser.close(); fixture.closeAllConnections(); await new Promise(resolve => fixture.close(resolve));
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
