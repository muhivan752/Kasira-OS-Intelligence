// Synthetic fixtures only; no merchant records or financial writes against production.
const http = require('node:http');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3119';
const id = '11111111-1111-4111-8111-111111111111';
const second = '22222222-2222-4222-8222-222222222222';
let loadFailure = false, uncertainSave = false, empty = false;
const calls = [], writes = new Map();
let expenses = [{ id: 'expense-1', category: 'listrik_air', category_label: 'Listrik & air', amount: '123.45',
  paid_at: '2026-09-30T23:30:00Z', payment_method: 'transfer', cash_account_id: 'bank', cash_account_name: 'Bank fixture',
  note: 'Pembayaran fixture', recurring: 'none', row_version: 0 }];
const categories = [{ key: 'lainnya', label: 'Lainnya' }, { key: 'listrik_air', label: 'Listrik & air' }, { key: 'bahan', label: 'Bahan & stok' }];
const accounts = [{ id: 'drawer', name: 'Kas fixture', kind: 'cash_drawer', default_for: ['cash'], is_active: true },
  { id: 'bank', name: 'Bank fixture', kind: 'bank', default_for: ['transfer', 'card', 'qris', 'ewallet'], is_active: true }];
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {};
  const url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body, params: Object.fromEntries(url.searchParams) });
  let data = [], status = 200, detail;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Pemilik fixture', subscription_tier: 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = [{ id, name: 'Toko A fixture' }, { id: second, name: 'Toko B fixture' }];
  else if (path.endsWith('/finance/accounts')) data = accounts;
  else if (path.endsWith('/finance/categories')) data = categories;
  else if (path.endsWith('/finance/summary')) {
    if (loadFailure) { status = 500; detail = 'INTERNAL FINANCIAL SECRET'; }
    else {
      const month = url.searchParams.get('month');
      data = { month, outlet_id: url.searchParams.get('outlet_id'), revenue: empty ? '0' : '1234567.89', refunds: '10.11', net_revenue: '1234557.78',
        delivery_fees: '12.34', cogs: '60000.25', cogs_coverage: empty ? 1 : .8, gross_profit: '1174569.87', gross_margin_pct: 90.2,
        expenses_total: '350000.50', petty_cash_out: '100.25', expenses_by_category: [{ key: 'listrik_air', label: 'Listrik & air', amount: '350000.50', count: 1 }],
        net_profit: empty ? '0' : '824469.12', net_margin_pct: 66.7, orders_count: empty ? 0 : 5, cash_in: '1200000.25', cash_out: '350000.25', cash_net: '850000',
        accounts: [{ id: 'bank', name: 'Bank fixture', kind: 'bank', inflow: '1200000.25', outflow: '350000.25', net: '850000' }],
        purchases_paid: '300.50', payables_outstanding: '400.25', payables_overdue: '100.50', cash_history_estimated: true,
        recurring_pending: 1, report_timezone: 'Asia/Jakarta', generated_at: new Date().toISOString(),
        trend: Array.from({ length: 6 }, (_, i) => ({ month: `2026-${String(i + 4).padStart(2, '0')}`, revenue: '1234567.89', net: i === 0 ? '-5000.50' : '824469.12' })) };
    }
  } else if (path.endsWith('/finance/expenses') && req.method === 'GET') data = empty ? [] : expenses;
  else if (path.endsWith('/finance/expenses') && req.method === 'POST') {
    if (writes.has(body.client_request_id)) data = writes.get(body.client_request_id);
    else { data = { ...body, id: `expense-${expenses.length + 1}`, category_label: categories.find(c => c.key === body.category).label,
      cash_account_name: accounts.find(a => a.id === body.cash_account_id).name, row_version: 0 }; expenses.push(data); writes.set(body.client_request_id, data); }
    if (uncertainSave) { status = 500; detail = 'WRITE RESPONSE LOST SECRET'; uncertainSave = false; }
  } else if (path.includes('/finance/expenses/') && req.method === 'PUT') {
    const old = expenses.find(e => e.id === path.split('/').pop());
    data = { ...old, ...body, row_version: old.row_version + 1 };
    expenses = expenses.map(e => e.id === old.id ? data : e);
  } else if (path.includes('/finance/expenses/') && req.method === 'DELETE') {
    expenses = expenses.filter(e => e.id !== path.split('/').pop()); data = { ok: true };
  } else if (path.endsWith('/finance/expenses/copy-recurring')) { data = []; }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status >= 400 ? { detail } : { success: true, data, message: 'Pembayaran fixture dicatat' }));
});

async function appearance(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${label} overflow`);
  const problems = await page.locator('.finance-workspace').evaluate(root => {
    const rgb = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
    const lum = value => rgb(value).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const issues = [];
    for (const el of root.querySelectorAll('*')) {
      const style = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || style.visibility === 'hidden' || el.tagName === 'OPTION' || el.closest(':disabled')) continue;
      if (['BUTTON', 'SELECT', 'A'].includes(el.tagName) || el.tagName === 'INPUT' && el.type !== 'checkbox') {
        if (box.width < 43 || box.height < 43) issues.push(`target ${el.textContent || el.type} ${box.width}x${box.height}`);
      }
      if (!Array.from(el.childNodes).some(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())) continue;
      let bg = el;
      while (bg.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
      const a = lum(style.color), b = lum(getComputedStyle(bg).backgroundColor), ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      if (ratio < 4.5) issues.push(`contrast ${el.textContent.trim().slice(0, 40)} ${ratio}`);
    }
    return issues;
  });
  assert.deepEqual(problems, [], label);
}

(async () => {
  await new Promise(resolve => fixture.listen(8193, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  let debugPage;
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, timezoneId: 'America/Los_Angeles' });
    await context.addCookies(['token', 'tenant_id', 'outlet_id'].map(name => ({ name, value: name === 'token' ? 'fixture-token' : name === 'outlet_id' ? second : id, url: base })));
    const page = await context.newPage(), errors = []; debugPage = page;
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`${base}/dashboard/keuangan`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.getByRole('heading', { name: 'Laba setelah biaya tercatat', exact: true }).waitFor();
    assert.equal(await page.getByLabel('Outlet', { exact: true }).inputValue(), second);
    assert.match(await page.locator('.f-amount').innerText(), /824\.469,12/);
    await page.getByLabel('Outlet', { exact: true }).selectOption(id);
    await page.getByRole('heading', { name: 'Laba setelah biaya tercatat', exact: true }).waitFor();
    assert(calls.some(c => c.path.endsWith('/finance/summary') && c.params.outlet_id === id));
    assert.match(await page.locator('.finance-workspace').innerText(), /HPP baru tersedia untuk 80%/);
    assert.equal(await page.getByRole('link', { name: 'Periksa harga modal produk' }).getAttribute('href'), '/dashboard/menu');
    for (const route of ['menu', 'pembelian', 'settings']) await fs.access(`app/dashboard/${route}/page.tsx`);
    assert.match(await page.locator('.finance-workspace').innerText(), /bukan saldo rekening/);
    const originalMonth = await page.getByLabel('Bulan laporan').inputValue();
    await page.getByRole('button', { name: 'Bulan sebelumnya' }).click();
    await page.getByRole('heading', { name: 'Laba setelah biaya tercatat', exact: true }).waitFor();
    assert.notEqual(await page.getByLabel('Bulan laporan').inputValue(), originalMonth);
    await page.getByRole('button', { name: 'Bulan berikutnya' }).click();
    await page.getByRole('heading', { name: 'Laba setelah biaya tercatat', exact: true }).waitFor();

    await page.getByRole('button', { name: 'Ubah Listrik & air Pembayaran fixture' }).click();
    assert.equal(await page.getByLabel('Tanggal pembayaran (WIB)').inputValue(), '2026-10-01');
    assert.equal(await page.getByLabel('Nominal (Rp)').inputValue(), '123.45');
    await page.getByLabel('Nominal (Rp)').fill('124.56');
    await page.getByRole('button', { name: 'Simpan perubahan' }).click();
    await page.getByRole('dialog').waitFor({ state: 'hidden' });
    const edited = calls.find(c => c.method === 'PUT');
    assert.equal(edited.body.amount, '124.56'); assert.equal(edited.body.paid_at, '2026-09-30T23:30:00Z');
    console.log('PASS outlet selection, month navigation, decimals and WIB date preservation');

    await page.getByRole('button', { name: 'Catat pengeluaran', exact: true }).click();
    await page.getByLabel('Kategori', { exact: true }).selectOption('listrik_air');
    await page.getByLabel('Nominal (Rp)').fill('350000.25');
    await page.getByLabel('Metode pembayaran').selectOption('transfer');
    await page.getByLabel('Catatan (opsional)').fill('=HYPERLINK("https://example.invalid")');
    uncertainSave = true;
    await page.getByRole('button', { name: 'Catat pembayaran', exact: true }).click();
    await page.getByRole('dialog').getByRole('alert').waitFor();
    assert.equal(await page.getByLabel('Nominal (Rp)').isDisabled(), true);
    await page.getByRole('button', { name: 'Catat pembayaran', exact: true }).click();
    await page.getByRole('dialog').waitFor({ state: 'hidden' });
    const posted = calls.filter(c => c.method === 'POST' && c.path.endsWith('/finance/expenses'));
    assert.equal(posted.length, 2); assert.deepEqual(posted[0].body, posted[1].body); assert.equal(writes.size, 1);
    assert.equal(posted[0].body.cash_account_id, 'bank'); assert.equal(posted[0].body.amount, '350000.25');
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Unduh CSV' }).click();
    const download = await downloadPromise; await download.saveAs('/tmp/selaris-finance-export.csv');
    const csv = await fs.readFile('/tmp/selaris-finance-export.csv', 'utf8');
    assert(csv.includes('350000.25')); assert(csv.includes("'=")); assert(csv.includes('bukan saldo kas'));
    console.log('PASS uncertain save replay, explicit source account and CSV formula escaping');

    await page.getByRole('button', { name: 'Periksa sebelum mencatat' }).click();
    assert.match(await page.getByRole('dialog').innerText(), /pembayaran sudah dilakukan/);
    await page.getByRole('button', { name: 'Sudah dibayar, catat' }).click();
    await page.getByRole('dialog').waitFor({ state: 'hidden' });
    await page.getByRole('button', { name: 'Hapus Listrik & air Pembayaran fixture' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Hapus pengeluaran', exact: true }).click();
    await page.getByRole('dialog').waitFor({ state: 'hidden' });
    assert.equal(expenses.length, 1);

    loadFailure = true;
    await page.getByRole('button', { name: 'Muat ulang' }).click();
    await page.locator('.finance-workspace').getByRole('alert').waitFor();
    assert.equal(await page.locator('.f-amount').count(), 0);
    assert(!(await page.locator('.finance-workspace').innerText()).includes('SECRET'));
    loadFailure = false;
    await page.getByRole('button', { name: 'Coba lagi' }).click();
    await page.getByRole('heading', { name: 'Laba setelah biaya tercatat', exact: true }).waitFor();
    console.log('PASS recurring confirmation, deletion and failed report never shows zero financial result');

    for (const dark of [false, true]) {
      await page.evaluate(d => document.documentElement.classList.toggle('dark', d), dark);
      for (const width of [320, 375, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 950 });
        await appearance(page, `${width} ${dark ? 'dark' : 'light'}`);
        await page.getByRole('button', { name: 'Catat pengeluaran', exact: true }).click();
        await page.getByLabel('Nominal (Rp)').fill('9999999999.99');
        await appearance(page, `dialog ${width} ${dark ? 'dark' : 'light'}`);
        await page.keyboard.press('Escape');
        await page.getByRole('dialog').waitFor({ state: 'hidden' });
        await page.evaluate(() => document.documentElement.style.fontSize = '200%');
        await appearance(page, `200% ${width} ${dark ? 'dark' : 'light'}`);
        await page.evaluate(() => document.documentElement.style.fontSize = '');
      }
    }
    await page.screenshot({ path: '/tmp/selaris-finance-dark.png', fullPage: true });
    await page.evaluate(() => document.documentElement.classList.remove('dark'));
    await page.screenshot({ path: '/tmp/selaris-finance-light.png', fullPage: true });
    empty = true;
    await page.getByRole('button', { name: 'Muat ulang' }).click();
    await page.getByText(/Belum ada pengeluaran pada/).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS page and dialogs: 5 widths, 2 themes, 200% text, AA contrast, 44px controls, Escape and empty state');
    console.log('ALL FINANCE BROWSER CHECKS PASSED');
  } catch (error) {
    if (debugPage) { console.error((await debugPage.locator('.finance-workspace').innerText()).slice(-3000));
      await debugPage.screenshot({ path: '/tmp/selaris-finance-browser-failure.png', fullPage: true }); }
    throw error;
  } finally { await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(e => { console.error(e); process.exitCode = 1; });
