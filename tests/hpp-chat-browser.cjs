// Preview frontend uses BACKEND_INTERNAL_URL=http://127.0.0.1:8188/api/v1.
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3109';
const id = '11111111-1111-4111-8111-111111111111';
const chats = [], calls = [];
let failure = null, incomplete = false, starter = false, processing = false;

function preview(mode, revision) {
  return { product_name: 'Nasi ayam fixture', product_id: null, new_product: true,
    replaces_recipe: false, servings: '10', servings_source: 'user', servings_evidence: '10 porsi',
    is_estimated: mode === 'estimate', ready: !incomplete, missing: incomplete ? ['Ayam: isi jumlah pembelian.'] : [],
    total_cost: incomplete ? null : '9876.54', fingerprint: String(revision).padStart(64, '0'),
    lines: [{ name: 'Ayam fixture', ingredient_id: null, action: 'create', quantity: '150', unit: 'gram',
      input_quantity: '1.5', input_unit: 'kg', basis: 'batch', buy_price: '40000', buy_qty: '1000',
      unit_cost: '40.00000001', old_unit_cost: null, line_cost: '6000.0000015',
      quantity_source: mode === 'estimate' ? 'estimate' : 'user', price_source: 'user',
      quantity_evidence: 'ayam 1,5 kg untuk 10 porsi', price_evidence: 'beli 1 kg 40000',
      affected_products: [], is_estimated: mode === 'estimate', is_optional: false, notes: 'Takaran daging mentah.' },
      { name: 'Bahan toko fixture', ingredient_id: 'existing', action: 'update_price', quantity: '0.2', unit: 'kg',
        input_quantity: '200', input_unit: 'gram', basis: 'portion', buy_price: '20000', buy_qty: '1', unit_cost: '20000', old_unit_cost: '18000',
        line_cost: '3876.5399985', quantity_source: 'user', price_source: 'user', quantity_evidence: '', price_evidence: 'ubah harga beli 1 kg 20000',
        affected_products: ['Menu lama fixture'], is_estimated: false, is_optional: false, notes: '' }] };
}

const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {};
  const url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/$/, '');
  calls.push({ method: req.method, path, body });
  let data = [], status = 200, detail;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Pemilik fixture', subscription_tier: starter ? 'starter' : 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = [{ id, brand_id: id, name: 'Toko fixture', slug: 'fixture', stock_mode: 'simple' }];
  else if (path.endsWith('/sessions') && req.method === 'GET') data = chats.map(c => ({ id: c.id, name: c.preview?.product_name || 'Resep baru', status: c.status, updated_at: new Date().toISOString() }));
  else if (path.endsWith('/sessions') && req.method === 'POST') {
    data = { id: `chat-${chats.length + 1}`, outlet_id: id, mode: body.mode, status: 'draft', revision: 0, preview: null, result: null, error: null, pending: false, retry_allowed: false, turns: [] };
    chats.push(data);
  } else if (path.includes('/sessions/')) {
    const chatId = path.split('/sessions/')[1].split('/')[0];
    data = chats.find(c => c.id === chatId);
    if (!data) { status = 404; detail = 'Percakapan tidak ditemukan'; }
    else if (req.method === 'POST' && path.endsWith('/messages')) {
      if (!data.turns.some(turn => turn.id === body.request_id && turn.reply)) {
        const turn = data.turns.find(turn => turn.id === body.request_id);
        if (!turn) data.turns.push({ id: body.request_id, mode: body.mode, message: body.message, reply: null });
        const latest = turn || data.turns.at(-1);
        data.mode = body.mode; data.error = null; data.pending = processing; data.retry_allowed = false;
        if (!processing) {
          latest.reply = 'Periksa takaran dan sumber harga pada draft. Ada yang ingin diubah?';
          data.revision++; data.preview = preview(body.mode, data.revision);
        }
      }
    } else if (req.method === 'POST' && path.endsWith('/approve')) {
      if (failure?.status === 409) { data.revision++; data.preview.fingerprint = String(data.revision).padStart(64, '0'); data.preview.total_cost = '10000.00'; }
      else if (data.status !== 'applied') {
        assert.equal(body.revision, data.revision); assert.equal(body.fingerprint, data.preview.fingerprint);
        assert.equal(body.outlet_id, id);
        data.status = 'applied'; data.result = { product_id: 'new-product', recipe_id: 'saved', new_product: true, total_cost: data.preview.total_cost, is_estimated: data.preview.is_estimated };
      }
    }
    if (failure && req.method === 'POST') { ({ status, detail } = failure); failure = null; }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status >= 400 ? { detail } : { data }));
});

async function appearance(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${label}: overflow`);
  assert(await page.getByLabel('Cerita atau koreksi Anda').evaluate(el => el.getBoundingClientRect().height >= 159), `${label}: long-story textarea`);
  const bad = await page.locator('.hpp-chat').evaluate(root => {
    const rgb = c => c.match(/[\d.]+/g)?.slice(0, 3).map(Number);
    const lum = c => rgb(c).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
    const failures = [];
    for (const el of root.querySelectorAll('*')) {
      const style = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || style.visibility === 'hidden' || el.tagName === 'OPTION' || el.closest(':disabled')) continue;
      if ((['BUTTON', 'SELECT', 'A', 'SUMMARY'].includes(el.tagName) || el.classList.contains('hpp-chat-choice')) && (box.width < 43 || box.height < 43)) failures.push(`target ${el.tagName}: ${box.width}x${box.height}`);
      if (!Array.from(el.childNodes).some(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())) continue;
      let bg = el;
      while (bg.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
      const a = lum(style.color), b = lum(getComputedStyle(bg).backgroundColor);
      if ((Math.max(a, b) + .05) / (Math.min(a, b) + .05) < 4.5) failures.push(`contrast ${el.textContent.slice(0, 50)}`);
    }
    return failures;
  });
  assert.deepEqual(bad, [], label);
}

(async () => {
  await new Promise(resolve => fixture.listen(8188, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await context.route(/(google-analytics|analytics.google|doubleclick|googletagmanager)/, route => route.abort());
    await context.addCookies(['token', 'tenant_id', 'outlet_id'].map(name => ({ name, value: name === 'token' ? 'fixture' : id, url: base })));
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/dashboard/hpp/chat`, { waitUntil: 'networkidle' });
    await page.getByLabel('Cerita atau koreksi Anda').waitFor();
    assert.equal(await page.getByLabel('Manual', { exact: false }).isChecked(), true);
    await page.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await page.getByRole('link', { name: 'Isi resep dengan form', exact: true }).click();
    await page.getByRole('heading', { name: 'Atur HPP', exact: true }).waitFor();
    await page.getByRole('link', { name: 'Atur lewat percakapan', exact: true }).click();
    await page.getByLabel('Cerita atau koreksi Anda').waitFor();
    assert.equal(calls.filter(c => c.method === 'POST').length, 0);
    const story = 'Resep 10 porsi ayam 1,5 kg untuk 10 porsi beli 1 kg 40000. ' + 'Cerita dapur panjang. '.repeat(2400);
    await page.getByLabel('Cerita atau koreksi Anda').fill(story);
    await page.getByRole('button', { name: 'Kirim cerita', exact: true }).click();
    await page.getByRole('button', { name: 'Kirim cerita', exact: true }).waitFor().catch(async error => {
      console.error('Fixture calls:', calls.map(c => ({ method: c.method, path: c.path, messageLength: c.body.message?.length })));
      console.error('Visible state:', (await page.locator('body').innerText()).slice(-2200));
      throw error;
    });
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    assert.equal(chats[0].turns[0].message, story);
    assert.equal(chats[0].status, 'draft');
    assert(await page.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await page.getByText('Lihat rumus HPP', { exact: true }).click();
    await page.getByText(/Biaya satuan = total harga beli/).waitFor();
    await page.getByText('Lihat sumber dari cerita', { exact: true }).first().click();
    assert((await page.locator('aside').innerText()).includes('Menu lama fixture'));
    assert((await page.locator('aside').innerText()).includes('Sebelumnya 18.000'));
    assert((await page.locator('aside').innerText()).includes('40,00000001'));
    await page.getByLabel(/Saya sudah memeriksa/).check();
    assert(await page.getByRole('button', { name: 'Approve dan simpan resep' }).isEnabled());
    await page.getByLabel('Cerita atau koreksi Anda').fill('Koreksi takaran ayam');
    assert(await page.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await page.getByLabel('Estimasi', { exact: false }).check();
    await page.getByRole('button', { name: 'Kirim cerita', exact: true }).click();
    await page.getByText('Estimasi HPP bahan per porsi', { exact: true }).waitFor();
    assert.equal(chats[0].revision, 2);
    assert(await page.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByText('Estimasi HPP bahan per porsi', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Percakapan tersimpan').inputValue(), chats[0].id);
    assert.equal(chats[0].turns.length, 2);
    for (const theme of ['light', 'dark']) for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.evaluate(t => { document.documentElement.classList.toggle('dark', t === 'dark'); document.documentElement.dataset.theme = t; }, theme);
      await appearance(page, `${theme}/${width}`);
      if (width === 320 || width === 1440) await page.screenshot({ path: `/tmp/selaris-hpp-chat-${theme}-${width}.png`, fullPage: true });
    }
    await page.setViewportSize({ width: 320, height: 420 });
    await page.getByLabel('Cerita atau koreksi Anda').fill('Koreksi untuk uji keyboard');
    await page.getByLabel('Cerita atau koreksi Anda').focus();
    await page.keyboard.press('Tab');
    assert(await page.getByRole('button', { name: 'Kirim cerita', exact: true }).evaluate(el => el === document.activeElement));
    assert.notEqual(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'none');
    await page.addStyleTag({ content: '.hpp-chat { font-size: 200%; } .hpp-chat .text-sm { font-size: 1.75rem; }' });
    await appearance(page, '200% text/short viewport');
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByLabel('Cerita atau koreksi Anda').fill('');

    failure = { status: 409, detail: 'Harga sudah berubah. Muat draft terbaru.' };
    await page.getByLabel(/Saya sudah memeriksa/).check();
    await page.getByRole('button', { name: 'Approve dan simpan resep' }).click();
    await page.getByRole('alert').filter({ hasText: 'Harga sudah berubah' }).waitFor();
    await page.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await page.getByTestId('hpp-chat-total').filter({ hasText: '10.000' }).waitFor();
    assert(!(await page.getByLabel(/Saya sudah memeriksa/).isChecked()));
    await page.getByLabel(/Saya sudah memeriksa/).check();
    failure = { status: 500, detail: 'INTERNAL SECRET' };
    const approvals = calls.filter(c => c.path.endsWith('/approve')).length;
    await page.getByRole('button', { name: 'Approve dan simpan resep' }).click();
    await page.getByRole('alert').filter({ hasText: 'Hasil belum dapat dipastikan' }).waitFor();
    assert(!(await page.locator('body').innerText()).includes('INTERNAL SECRET'));
    assert.equal(chats[0].status, 'applied');
    await page.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await page.getByText('Bahan dan resep sudah tersimpan.', { exact: true }).waitFor();
    assert.equal(calls.filter(c => c.path.endsWith('/approve')).length, approvals + 1);
    assert((await page.locator('body').innerText()).includes('Menu baru masih nonaktif'));

    await page.getByRole('button', { name: 'Resep baru', exact: true }).click();
    incomplete = true;
    await page.getByLabel('Cerita atau koreksi Anda').fill('Aku bingung jumlah pembelian.');
    await page.getByRole('button', { name: 'Kirim cerita', exact: true }).click();
    await page.getByText('Masih perlu dilengkapi', { exact: true }).waitFor();
    assert(await page.getByLabel(/Saya sudah memeriksa/).isDisabled());
    assert(await page.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    incomplete = false; processing = true;
    await page.getByLabel('Cerita atau koreksi Anda').fill('Bantu estimasikan.');
    await page.getByRole('button', { name: 'Kirim cerita', exact: true }).click();
    await page.getByText('Pesan sedang diproses.', { exact: false }).waitFor();
    assert(await page.getByLabel('Cerita atau koreksi Anda').isDisabled());
    const pending = chats.at(-1); pending.retry_allowed = true; processing = false;
    await page.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await page.getByRole('button', { name: 'Proses ulang pesan terakhir' }).click();
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    assert.equal(pending.turns.length, 2);
    await page.getByRole('button', { name: 'Resep baru', exact: true }).click();
    processing = true;
    await page.getByLabel('Cerita atau koreksi Anda').fill('Proses resep panjang di latar belakang.');
    const messageCount = calls.filter(c => c.path.endsWith('/messages')).length;
    await page.getByRole('button', { name: 'Kirim cerita', exact: true }).click();
    await page.getByText('Pesan sedang diproses.', { exact: false }).waitFor();
    await page.waitForFunction(() => document.querySelector('#hpp-chat-message')?.value === '');
    const automatic = chats.at(-1);
    automatic.pending = false; automatic.turns.at(-1).reply = 'Draft sudah siap diperiksa.';
    automatic.revision++; automatic.preview = preview(automatic.mode, automatic.revision);
    processing = false;
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    await page.getByText('Draft sudah siap diperiksa.', { exact: true }).waitFor();
    assert.equal(calls.filter(c => c.path.endsWith('/messages')).length, messageCount + 1, 'Polling only reads; it must not replay the model request');
    assert(!calls.some(c => /restock|stock-mode|apply-recipe/.test(c.path)), 'Dedicated setup must never call ordinary chat/restock or legacy apply');
    assert.deepEqual(errors, []);
    console.log('PASS HPP chat browser: manual/estimate, long story, server total, durable resume, provenance, approval/revision guards, 409/500 recovery without replay, incomplete/pending/retry, five widths/two themes, AA/44px/keyboard/200%/short viewport');
    await context.close();
  } finally { await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
