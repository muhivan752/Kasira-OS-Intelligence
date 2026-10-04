// Run against Next.js with BACKEND_INTERNAL_URL=http://127.0.0.1:8185/api/v1.
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3105';
const id = '11111111-1111-4111-8111-111111111111';
const calls = [];
let mode = 'simple';
let stockAttempt = 0;
const outlet = {
  id, brand_id: id, name: 'Toko fixture', slug: 'fixture', is_open: true,
  accepting_orders: true, is_pro: true, subscription_tier: 'pro',
  whatsapp: '628111111111', online_orders_enabled: true,
  payment_methods: ['cash', 'qris', 'transfer'], qris_channel: 'manual',
  reservation_enabled: true, reservation_deposit_amount: 50000,
  address: 'Alamat fixture',
};
const products = [
  { id: 'coffee', name: 'Kopi fixture', price: 18000, is_available: true, category_id: 'drinks', variants: [] },
  { id: 'tea', name: 'Teh fixture', price: 12000, is_available: true, category_id: 'drinks', variants: [{ id: 'iced', name: 'Dingin', price: 13000 }] },
  { id: 'sold', name: 'Produk habis', price: 10000, is_available: false, category_id: 'drinks', variants: [] },
];
const fixture = http.createServer(async (req, res) => {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {};
  const path = new URL(req.url, 'http://fixture').pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body });
  let data = [], status = 200, detail;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Pemilik fixture', subscription_tier: 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = [{ ...outlet, stock_mode: mode }];
  else if (path.endsWith('/stock-mode')) {
    stockAttempt++;
    if (stockAttempt === 1) {
      status = 400;
      detail = 'Belum punya resep: Egg Tart, Kopi susu. Lengkapi resep dulu sebelum beralih ke mode Resep.';
    } else if (stockAttempt === 2) {
      status = 500; detail = 'INTERNAL DATABASE SECRET';
    } else if (stockAttempt === 3) {
      status = 422; detail = [{ msg: 'Mode stok tidak valid' }];
    } else if (stockAttempt === 6) {
      status = 401; detail = 'Unauthorized';
    } else { mode = body.stock_mode; data = { ...outlet, stock_mode: mode }; }
  } else if (path.endsWith('/connect/fixture')) data = { outlet, categories: [{ id: 'drinks', name: 'Minuman' }], products };
  else if (path.endsWith('/tables')) data = { is_pro: true, tables: [{ id: 'table', name: 'Meja 1', capacity: 4, status: 'available' }] };
  else if (path.includes('/reservation/slots')) data = { slots: [{ time: '10:00', available: true, remaining_capacity: 4, tables_available: 1 }] };
  else if (path.includes('/connect/orders/')) {
    const phase = path.split('/').pop();
    data = {
      id: phase, status: ['awaiting_payment', 'payment_failed', 'awaiting_confirm'].includes(phase) ? 'pending' : phase,
      display_number: 7, order_type: 'pickup', customer_name: 'Pelanggan fixture',
      total_amount: 18000, created_at: new Date().toISOString(), outlet,
      items: [{ name: 'Kopi fixture', product_name: 'Kopi fixture', quantity: 1, unit_price: 18000, subtotal: 18000 }],
      payment: { method: 'qris', channel: phase === 'awaiting_confirm' ? 'manual' : 'gateway', status: phase === 'payment_failed' ? 'failed' : ['awaiting_payment', 'awaiting_confirm'].includes(phase) ? 'pending' : 'paid', amount: 18000 },
    };
  } else if (path.includes('/connect/reservations/')) {
    const phase = path.split('/').pop();
    data = {
      id: phase, status: phase === 'awaiting_deposit' ? 'pending' : phase,
      customer_name: 'Pelanggan fixture', reservation_date: '2026-10-05', start_time: '10:00', guest_count: 2, outlet,
      deposit: { amount: 50000, status: phase === 'awaiting_deposit' ? 'pending' : 'paid', method: 'transfer' },
    };
  } else if (path.includes('/connect/bookings/')) data = { id, status: 'confirmed', customer_name: 'Pelanggan fixture', guest_count: 2, reservation_time: '2026-10-05T10:00:00Z', outlet };
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status >= 400 ? { detail } : { success: true, data }));
});

async function checkLayout(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${label}: overflow`);
}

async function contrast(locator, label) {
  const ratio = await locator.first().evaluate(el => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d');
    const rgb = color => {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 1, 1);
      return Array.from(ctx.getImageData(0, 0, 1, 1).data).slice(0, 3);
    };
    const luminance = color => rgb(color).map(x => x / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4).reduce((n, x, i) => n + x * [.2126, .7152, .0722][i], 0);
    let bg = el;
    while (bg.parentElement && getComputedStyle(bg).backgroundImage === 'none' && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
    const ink = luminance(getComputedStyle(el).color);
    const style = getComputedStyle(bg);
    const colors = style.backgroundImage.match(/rgba?\([^)]+\)/g) || [style.backgroundColor];
    return Math.min(...colors.map(color => {
      const paper = luminance(color);
      return (Math.max(ink, paper) + .05) / (Math.min(ink, paper) + .05);
    }));
  });
  assert(ratio >= 4.5, `${label}: ${ratio.toFixed(2)}:1`);
}

(async () => {
  await new Promise(resolve => fixture.listen(8185, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 320, height: 800 } });
    await context.addCookies(['token', 'tenant_id', 'outlet_id'].map(name => ({ name, value: name === 'token' ? 'fixture-token' : id, url: base })));
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/dashboard/settings`, { waitUntil: 'networkidle' });
    await page.getByText('Pilih cara mengelola stok produk Anda.').waitFor();
    const simple = page.locator('input[name="stock_mode"][value="simple"]');
    const recipe = page.locator('input[name="stock_mode"][value="recipe"]');
    const switchTo = async input => { await input.click(); await page.getByRole('button', { name: 'Ya, Beralih' }).click(); };
    await switchTo(recipe);
    await page.getByRole('alert').filter({ hasText: 'Egg Tart, Kopi susu' }).waitFor();
    assert(await simple.isChecked());
    assert.equal(await page.getByRole('alert').getByRole('link', { name: 'Bahan Baku' }).getAttribute('href'), '/dashboard/bahan-baku');
    assert.equal(await page.getByRole('alert').getByRole('link', { name: 'Menu', exact: true }).getAttribute('href'), '/dashboard/menu');
    await switchTo(recipe);
    await page.getByRole('alert').filter({ hasText: 'Coba lagi beberapa saat' }).waitFor();
    assert(!(await page.locator('body').innerText()).includes('INTERNAL DATABASE SECRET'));
    await switchTo(recipe);
    await page.getByRole('alert').filter({ hasText: 'Mode stok tidak valid' }).waitFor();
    await switchTo(recipe);
    await page.getByText('Mode Resep & HPP aktif!', { exact: false }).waitFor();
    assert(await recipe.isChecked());
    await switchTo(simple);
    await page.getByText('Mode Stok Sederhana aktif.', { exact: false }).waitFor();
    assert(await simple.isChecked());
    await switchTo(recipe);
    await page.getByRole('alert').filter({ hasText: 'Sesi login sudah berakhir' }).waitFor();
    assert(await simple.isChecked());
    console.log('PASS stock mode: readable 400, safe 500, structured 422, retry, successful switch both ways, expired session; mode unchanged on failure.');
    for (const theme of ['light', 'dark']) {
      await page.addInitScript(theme => localStorage.setItem('selaris-theme', theme), theme);
      for (const width of [320, 768, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(`${base}/fixture`, { waitUntil: 'networkidle' });
        await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
        await page.getByText('Kopi fixture', { exact: true }).first().waitFor();
        await checkLayout(page, `menu ${theme} ${width}`);
        await contrast(page.getByRole('button', { name: 'Semua', exact: true }), `category ${theme}`);
        const coffee = page.locator('article').filter({ hasText: 'Kopi fixture' });
        if (await coffee.getByRole('button', { name: '+', exact: true }).count()) await coffee.getByRole('button', { name: '+', exact: true }).click();
        const increase = coffee.getByRole('button', { name: 'Tambah', exact: true });
        await increase.click();
        assert(await increase.evaluate(el => {
          const button = el.getBoundingClientRect();
          const card = el.closest('article').getBoundingClientRect();
          return button.left >= card.left && button.right <= card.right;
        }), 'Quantity controls must remain inside their product card');
        await coffee.getByRole('button', { name: 'Kurangi', exact: true }).click();
        const tea = page.locator('article').filter({ hasText: 'Teh fixture' });
        await tea.getByRole('button', { name: 'Pilih', exact: true }).click();
        await page.getByRole('dialog').waitFor();
        await checkLayout(page, `variants ${theme} ${width}`);
        await page.keyboard.press('Escape');
        await page.screenshot({ path: `/tmp/selaris-storefront-${theme}-${width}.png`, fullPage: true });
        await page.goto(`${base}/fixture/cart`, { waitUntil: 'networkidle' });
        await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
        const name = page.getByPlaceholder('Nama Anda', { exact: true });
        await name.fill('Pelanggan fixture');
        await name.focus();
        await contrast(name, `focused input ${theme}`);
        await page.getByRole('button', { name: 'Makan di tempat', exact: false }).click();
        await page.getByRole('button', { name: 'Meja 1', exact: false }).click();
        await contrast(page.getByRole('button', { name: 'Meja 1', exact: false }), `selected table ${theme}`);
        await checkLayout(page, `cart ${theme} ${width}`);
      }
      await page.setViewportSize({ width: 320, height: 900 });
      for (const phase of ['awaiting_payment', 'payment_failed', 'awaiting_confirm', 'preparing', 'ready', 'completed', 'cancelled']) {
        await page.goto(`${base}/fixture/order/${phase}`, { waitUntil: 'networkidle' });
        await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
        await page.locator('h1').waitFor();
        await contrast(page.locator('h1'), `order ${phase} ${theme}`);
        await checkLayout(page, `order ${phase} ${theme}`);
      }
      for (const phase of ['awaiting_deposit', 'confirmed', 'cancelled']) {
        await page.goto(`${base}/fixture/reservation/${phase}`, { waitUntil: 'networkidle' });
        await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
        await page.locator('h1').waitFor();
        await contrast(page.locator('h1'), `reservation ${phase} ${theme}`);
        await checkLayout(page, `reservation ${phase} ${theme}`);
      }
      await page.goto(`${base}/fixture/booking`, { waitUntil: 'networkidle' });
      await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
      await page.getByRole('button', { name: 'Pilih Jam' }).click();
      await page.getByRole('button', { name: '10:00', exact: false }).click();
      await page.getByRole('button', { name: 'Lanjut Isi Data' }).click();
      const bookingName = page.getByPlaceholder('Masukkan nama Anda');
      await bookingName.fill('Pelanggan fixture');
      await bookingName.focus();
      await contrast(bookingName, `booking focused input ${theme}`);
      await page.getByPlaceholder('0812xxxxxxxx').fill('081111111111');
      await page.getByRole('button', { name: 'Lihat Ringkasan', exact: false }).click();
      await checkLayout(page, `booking confirmation ${theme}`);
      await page.screenshot({ path: `/tmp/selaris-booking-${theme}.png`, fullPage: true });
      await page.goto(`${base}/fixture/booking/${id}`, { waitUntil: 'networkidle' });
      await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
      await page.getByText('Status Reservasi', { exact: true }).waitFor();
      await checkLayout(page, `booking status ${theme}`);
      await page.route('**/api/antar/fixture/task?k=fixture', route => route.fulfill({
        json: { data: {
          id: 'task', display_number: 7, status: 'ready', delivery_status: 'dispatched', outlet,
          customer_name: 'Pelanggan fixture', customer_phone: '628111111111', delivery_address: 'Alamat fixture',
          notes: 'Titip di depan', items: [{ product_name: 'Kopi fixture', quantity: 1 }],
          total_amount: 18000, delivery_fee: 2000, grand_total: 20000, cod_pending: true,
        } },
      }));
      await page.goto(`${base}/fixture/antar/task?k=fixture`, { waitUntil: 'networkidle' });
      await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.dataset.theme = theme; }, theme);
      await page.getByText('Titip di depan', { exact: false }).waitFor();
      await contrast(page.getByText(/^Rp\s?20\.000$/), `COD ${theme}`);
      await page.getByRole('button', { name: 'Gagal antar', exact: true }).click();
      const reason = page.getByRole('button', { name: 'Alamat tidak ditemukan', exact: true });
      await reason.click();
      await contrast(reason, `failure reason ${theme}`);
      await checkLayout(page, `courier ${theme}`);
    }
    assert.deepEqual(errors, []);
    assert(!calls.some(call => call.method === 'POST' && call.path.startsWith('/api/v1/connect/')), 'No real order, reservation or messages should be submitted');
    console.log('PASS storefront: light/dark at 320/768/1440; add/increase/decrease, variants/Escape, cart/table, focused inputs, seven order states, three reservation states, booking wizard/status, courier COD/failure; AA contrast on affected controls; no overflow or page errors.');
    await context.close();
  } finally {
    await browser.close();
    await new Promise(resolve => fixture.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
