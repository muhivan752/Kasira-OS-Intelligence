// Synthetic fixtures exercise UI capabilities; HTTP/JWT authorization has a separate PostgreSQL suite.
const http = require('node:http'), assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3312';
const id = '11111111-1111-4111-8111-111111111111', other = '22222222-2222-4222-8222-222222222222';
let permissions = ['finance.view', 'purchasing.view', 'customers.view', 'hpp.view'];
let malformedManifest = false;
const calls = [], allowed = p => permissions.includes(p);
const outlets = [{ id, brand_id: id, name: 'Outlet A fixture' }, { id: other, brand_id: other, name: 'Outlet B fixture' }];
const purchase = { id, outlet_id: other, po_number: 'NB-SCOPED', supplier_name: 'Supplier fixture', status: 'received',
  received_at: '2026-10-01T00:00:00Z', total_amount: null, paid_amount: null, outstanding_amount: null,
  photo_url: null, notes: null, items: [{ id, name: 'Gula fixture', quantity: 2, unit: 'kg', unit_price: null, total_price: null }], payments: [], row_version: 1 };
const person = { id, name: 'Pelanggan fixture', phone: null, row_version: 1, total_spent: '100.00', total_visits: 1,
  avg_spent: '100.00', first_visit_at: '2026-10-01T00:00:00Z', last_visit_at: '2026-10-01T00:00:00Z' };
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/+$/, '');
  calls.push({ path, method: req.method, search: url.search });
  let data = {}, status = 200;
  if (path.endsWith('/auth/access')) data = { enforcement_mode: malformedManifest ? 'unknown' : 'managed', permissions, outlets, scope: 'outlet', access_version: permissions.join(',') };
  else if (path.endsWith('/users/me')) data = { id, subscription_tier: 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = outlets;
  else if (path.endsWith('/finance/accounts')) data = [{ id, name: 'Kas fixture', kind: 'cash_drawer', default_for: ['cash'], is_active: true }];
  else if (path.endsWith('/finance/categories')) data = [{ key: 'lainnya', label: 'Lainnya' }];
  else if (path.endsWith('/finance/expenses')) data = [{ id, category_label: 'Lainnya', category: 'lainnya', amount: '10.00', paid_at: '2026-10-01T00:00:00Z', payment_method: 'cash', note: 'Pengeluaran fixture', row_version: 1 }];
  else if (path.endsWith('/finance/summary')) data = { month: url.searchParams.get('month'), outlet_id: other,
    revenue: '100.00', refunds: '0.00', net_revenue: '100.00', cogs: '20.00', cogs_coverage: 1, gross_profit: '80.00',
    expenses_total: '10.00', net_profit: '70.00', net_margin_pct: 70, orders_count: 1, cash_in: '100.00', cash_out: '10.00', cash_net: '90.00',
    expenses_by_category: [], accounts: [], trend: [], recurring_pending: 1, generated_at: '2026-10-01T00:00:00Z',
    payables_outstanding: '30.00', payables_overdue: '0.00', purchases_paid: '20.00', delivery_fees: '0.00', petty_cash_out: '0.00' };
  else if (path.endsWith('/suppliers')) data = [{ id, name: 'Supplier fixture', is_active: true, payment_terms_days: 7, purchase_count: 1, purchase_total: null, outstanding_total: null }];
  else if (path.endsWith('/purchases/summary')) data = { month: url.searchParams.get('month'), month_total: null, month_count: 1, outstanding_total: null, outstanding_count: 1, overdue_total: null, overdue_count: 0 };
  else if (path.endsWith('/purchases')) data = [purchase];
  else if (path.includes('/purchases/')) data = purchase;
  else if (path.endsWith('/customers/workspace')) {
    if (url.searchParams.get('export') === 'true' && !allowed('customers.export')) status = 403;
    data = { items: [person], total: 1, skip: 0, limit: 50, summary: { total: 1, repeat: 0, spent: '100.00', consented: 0 },
      scope: 'allowed_outlets', timezone: 'Asia/Jakarta', workspace_key: 'scoped-fixture', generated_at: '2026-10-01T00:00:00Z',
      can_manage: allowed('customers.manage'), can_export: allowed('customers.export') };
  } else if (path.includes('/customers/workspace/')) data = { ...person, orders: [], favourites: [], timeline: [], history_skip: 0, history_limit: 20, can_manage: allowed('customers.manage'), can_export: allowed('customers.export') };
  else if (path.endsWith('/products')) data = [{ id: other, brand_id: other, name: 'Kopi fixture', base_price: 20000, stock_qty: 10 }];
  else if (path.endsWith('/ingredients')) data = [{ id, name: 'Gula fixture', base_unit: 'gram', cost_per_base_unit: 50, buy_price: 5000, buy_qty: 100, row_version: 1 }];
  else if (path.endsWith('/recipes')) data = [{ id, product_id: other, total_cost: 100, ingredients: [{ ingredient_id: id, ingredient_name: 'Gula fixture', quantity: 2, quantity_unit: 'gram' }] }];
  else if (path.includes('/ai/') || path.includes('/invoice-ocr/')) status = 403;
  res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(status >= 400 ? { detail: { code: 'PERMISSION_DENIED', message: 'Tidak diizinkan' } } : { success: true, data }));
});

(async () => {
  await new Promise(resolve => fixture.listen(Number(process.env.FIXTURE_PORT || 8188), '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await context.tracing.start({ screenshots: true, snapshots: true });
    await context.route(/https?:\/\/(?!127\.0\.0\.1|localhost)/, route => route.abort());
    await context.addCookies(Object.entries({ token: 'synthetic-token', tenant_id: id, outlet_id: other }).map(([name, value]) => ({ name, value, url: base })));
    const page = await context.newPage(), errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/dashboard/keuangan');
    await page.getByRole('heading', { name: 'Laba setelah biaya tercatat', exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Catat pengeluaran', exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: /Catat pembayaran bulanan/ }).count(), 0);
    for (const label of ['Keuangan', 'Pembelian', 'Pelanggan', 'HPP']) assert(await page.locator('nav').getByRole('link', { name: label, exact: true }).count(), label);
    await page.locator('nav').getByRole('link', { name: 'Pembelian', exact: true }).click();
    await page.getByRole('heading', { name: 'Total nota bulan ini' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Catat nota', exact: true }).count(), 0);
    assert.match(await page.locator('.p-notas').innerText(), /Nominal tidak diizinkan/);
    await page.locator('.p-nota').click(); await page.getByRole('dialog').waitFor();
    assert.match(await page.getByRole('dialog').innerText(), /Nominal dan riwayat pembayaran tidak diizinkan/);
    assert.equal(await page.getByRole('dialog').getByRole('button', { name: /Catat pembayaran/ }).count(), 0);
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Supplier', exact: true }).click();
    assert.equal(await page.getByRole('button', { name: 'Tambah supplier' }).count(), 0);
    await page.locator('nav').getByRole('link', { name: 'Pelanggan', exact: true }).click();
    await page.locator('.c-summary').waitFor();
    assert.equal(await page.getByRole('button', { name: 'Tambah pelanggan' }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Ekspor halaman CSV' }).count(), 0);
    await page.getByRole('button', { name: 'Buka profil Pelanggan fixture' }).click();
    await page.getByRole('heading', { name: 'Produk yang sering dibeli' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Edit profil' }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Simpan catatan' }).count(), 0);
    await page.keyboard.press('Escape');
    await page.locator('nav').getByRole('link', { name: 'HPP', exact: true }).click();
    await page.getByLabel('Produk yang ingin dihitung').selectOption(other);
    await page.getByText('Akses baca. Penyimpanan langsung memerlukan hak kelola, persetujuan dan lihat harga pembelian.', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Outlet', { exact: true }).inputValue(), other);
    assert.equal(await page.getByRole('button', { name: 'Simpan resep dan HPP' }).count(), 0);
    assert.equal(await page.getByRole('link', { name: 'Atur lewat percakapan' }).count(), 0);
    assert(calls.some(call => call.path.endsWith('/products') && call.search.includes('outlet_id=' + other)));
    for (const width of [320, 375, 768, 1440]) for (const dark of [false, true]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(value => document.documentElement.classList.toggle('dark', value), dark);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'HPP overflow ' + width + '/' + dark);
    }
    await page.screenshot({ path: '/tmp/selaris-business-managed-hpp.png', fullPage: true });
    console.log('PASS managed view-only controls across Finance/Purchasing/CRM/HPP; truthful price denial and cookie-selected HPP outlet; four widths/themes');
    permissions.push('customers.export');
    await page.goto(base + '/dashboard/pelanggan'); await page.locator('.c-summary').waitFor();
    const download = page.waitForEvent('download'); await page.getByRole('button', { name: 'Ekspor halaman CSV' }).click(); await download;
    assert(calls.some(call => call.path.endsWith('/customers/workspace') && call.search.includes('export=true')));
    await page.goto(base + '/dashboard/hpp/chat');
    await page.getByText('Fitur ini belum tersedia untuk pengaturan akses akun Anda.', { exact: true }).waitFor();
    assert(!calls.some(call => call.path.includes('/ai/')));
    console.log('PASS separate CRM export revalidation and managed HPP chat blocked before provider calls');
    await page.goto(base + '/dashboard/keuangan'); await page.getByRole('heading', { name: 'Laba setelah biaya tercatat' }).waitFor();
    permissions = []; await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await page.getByText('Fitur ini belum tersedia untuk pengaturan akses akun Anda.', { exact: true }).waitFor();
    assert.equal(await page.locator('nav').getByRole('link', { name: 'Keuangan', exact: true }).count(), 0);
    assert.deepEqual(errors, []);
    console.log('PASS foreground revocation removes navigation and visible module; no page errors');
    malformedManifest = true; await page.reload(); await page.waitForURL('**/login');
    assert.equal(await page.locator('nav').getByRole('link', { name: 'Keuangan', exact: true }).count(), 0);
    console.log('PASS invalid access manifest fails closed instead of selecting owner navigation');
    await context.tracing.stop({ path: '/tmp/selaris-business-managed-trace.zip' });
  } finally { if (browser) await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
