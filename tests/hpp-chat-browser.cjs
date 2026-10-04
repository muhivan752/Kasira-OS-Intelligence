// Writes stay in this local fixture; the preview uses backend port 8188.
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3109';
const id = '11111111-1111-4111-8111-111111111111';
const chats = [], calls = [];
let failure = null, incomplete = false, processing = false, replacement = false;

function preview(mode, revision) {
  return { product_name: 'Nasi ayam fixture', product_id: null, new_product: true,
    replaces_recipe: replacement, servings: '10', servings_source: 'user', servings_evidence: '10 porsi',
    is_estimated: mode === 'estimate', ready: !incomplete, missing: incomplete ? ['Ayam: isi jumlah pembelian.'] : [],
    total_cost: incomplete ? null : '9876.54', fingerprint: String(revision).padStart(64, '0'), notes: '',
    lines: [{ name: 'Ayam fixture', ingredient_id: null, action: 'create', quantity: '150', unit: 'gram',
      input_quantity: '1.5', input_unit: 'kg', basis: 'batch', buy_price: '40000', buy_qty: '1000',
      unit_cost: '40.00000001', old_unit_cost: null, line_cost: '6000.0000015',
      quantity_source: mode === 'estimate' ? 'estimate' : 'user', price_source: 'user',
      quantity_evidence: 'ayam 1,5 kg untuk 10 porsi', price_evidence: 'beli 1 kg 40000',
      affected_products: [], is_estimated: mode === 'estimate', is_optional: false, notes: 'Takaran daging mentah.' },
      { name: 'Bahan toko fixture', ingredient_id: 'existing', action: 'update_price', quantity: '0.2', unit: 'kg',
        input_quantity: '200', input_unit: 'gram', basis: 'portion', buy_price: '20000', buy_qty: '1',
        unit_cost: '20000', old_unit_cost: '18000', line_cost: '3876.5399985',
        quantity_source: 'user', price_source: 'user', quantity_evidence: '', price_evidence: 'ubah harga beli 1 kg 20000',
        affected_products: ['Menu lama fixture'], is_estimated: false, is_optional: false, notes: '' }] };
}
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {}, url = new URL(req.url, 'http://fixture');
  const path = url.pathname.replace(/\/$/, '');
  calls.push({ method: req.method, path, body });
  let data = [], status = 200, detail;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Pemilik fixture', subscription_tier: 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = [{ id, brand_id: id, name: 'Toko fixture', stock_mode: 'simple' }];
  else if (path.endsWith('/sessions') && req.method === 'GET') data = chats.map(c => ({ id: c.id, name: c.preview?.product_name || 'Resep baru', status: c.status, updated_at: new Date().toISOString() }));
  else if (path.endsWith('/sessions') && req.method === 'POST') {
    data = { id: 'chat-' + (chats.length + 1), outlet_id: id, mode: body.mode, status: 'draft',
      revision: 0, preview: null, result: null, error: null, pending: false, retry_allowed: false, turns: [] };
    chats.push(data);
  } else if (path.includes('/sessions/')) {
    data = chats.find(c => c.id === path.split('/sessions/')[1].split('/')[0]);
    if (!data) { status = 404; detail = 'Percakapan tidak ditemukan'; }
    else if (req.method === 'POST' && path.endsWith('/messages')) {
      if (!data.turns.some(turn => turn.id === body.request_id && turn.reply)) {
        let turn = data.turns.find(turn => turn.id === body.request_id);
        if (!turn) { turn = { id: body.request_id, mode: body.mode, message: body.message, reply: null }; data.turns.push(turn); }
        data.mode = body.mode; data.error = null; data.pending = processing; data.retry_allowed = false;
        if (!processing) {
          turn.reply = incomplete ? 'Ayamnya biasa beli berapa kilo?' : 'Oke, takarannya sudah aku sesuaikan. Ada bahan lain yang mau ditambah?';
          data.revision++; data.preview = preview(body.mode, data.revision);
        }
      }
    } else if (req.method === 'POST' && path.endsWith('/approve')) {
      if (failure?.status === 409) { data.revision++; data.preview.fingerprint = String(data.revision).padStart(64, '0'); data.preview.total_cost = '10000.00'; }
      else if (data.status !== 'applied') {
        assert.equal(body.revision, data.revision); assert.equal(body.fingerprint, data.preview.fingerprint);
        assert.equal(body.outlet_id, id);
        if (data.preview.replaces_recipe) assert(body.replace_recipe);
        data.status = 'applied'; data.result = { product_id: 'new-product', recipe_id: 'saved', new_product: true,
          total_cost: data.preview.total_cost, is_estimated: data.preview.is_estimated };
      }
    }
    if (failure && req.method === 'POST') { ({ status, detail } = failure); failure = null; }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(status >= 400 ? { detail } : { data }));
});

async function appearance(page, label) {
  await page.waitForFunction(() => {
    const sidebar = document.querySelector('.merchant-shell > div[aria-hidden]');
    if (!sidebar) return true;
    const box = sidebar.getBoundingClientRect();
    return sidebar.getAttribute('aria-hidden') === 'true' ? box.right <= 1 : Math.abs(box.left) < 1;
  });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, label + ': overflow');
  const bad = await page.locator('.hpp-chat').evaluate(root => {
    const rgb = c => c.match(/[\d.]+/g)?.slice(0, 3).map(Number);
    const lum = c => rgb(c).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
    const failures = [];
    for (const el of root.querySelectorAll('*')) {
      const style = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || style.visibility === 'hidden' || el.closest(':disabled')) continue;
      if ((['BUTTON', 'SELECT', 'A', 'SUMMARY'].includes(el.tagName) || el.matches('.hpp-chat-choice,.hpp-chat-mode')) && (box.width < 43 || box.height < 43)) failures.push('target ' + el.tagName + ': ' + box.width + 'x' + box.height);
      if (!Array.from(el.childNodes).some(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())) continue;
      let bg = el;
      while (bg.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
      const a = lum(style.color), b = lum(getComputedStyle(bg).backgroundColor);
      if ((Math.max(a, b) + .05) / (Math.min(a, b) + .05) < 4.5) failures.push('contrast ' + el.textContent.slice(0, 50));
    }
    return failures;
  });
  assert.deepEqual(bad, [], label);
}
async function openRecipe(page) {
  await page.getByRole('button', { name: 'Lihat resep', exact: true }).click();
  await page.getByRole('dialog').waitFor();
  return page.getByRole('dialog');
}
async function closePanel(page) {
  await page.keyboard.press('Escape');
  await page.locator('dialog').waitFor({ state: 'hidden' });
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
    await page.goto(base + '/dashboard/hpp/chat', { waitUntil: 'networkidle' });
    await page.getByLabel('Tulis pesan', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Estimasi', { exact: true }).isChecked(), true);
    await page.getByLabel('Manual', { exact: true }).check();
    assert.equal(await page.locator('.hpp-chat aside').count(), 0);
    assert.equal(await page.getByTestId('hpp-chat-total').count(), 0);
    await page.getByRole('button', { name: 'Riwayat obrolan' }).click();
    await page.getByRole('dialog').getByText('Belum ada obrolan tersimpan.', { exact: false }).waitFor();
    await page.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await page.getByRole('link', { name: 'Isi resep dengan form', exact: true }).click();
    await page.getByRole('heading', { name: 'Atur HPP', exact: true }).waitFor();
    await page.getByRole('link', { name: 'Atur lewat percakapan', exact: true }).click();
    await page.getByLabel('Tulis pesan', { exact: true }).waitFor();
    await page.getByLabel('Manual', { exact: true }).check();
    assert.equal(calls.filter(c => c.method === 'POST').length, 0);
    const story = 'Resep 10 porsi ayam 1,5 kg untuk 10 porsi beli 1 kg 40000. ' + 'Cerita dapur panjang. '.repeat(2400);
    await page.getByLabel('Tulis pesan', { exact: true }).fill(story);
    assert(await page.getByLabel('Tulis pesan', { exact: true }).evaluate(el => el.getBoundingClientRect().height <= 161));
    await page.getByLabel('Tulis pesan', { exact: true }).press('Enter');
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    assert.equal(chats[0].turns[0].message, story);
    assert.equal(chats[0].status, 'draft');
    assert.equal(await page.getByRole('button', { name: 'Approve dan simpan resep' }).count(), 0, 'Approval stays in the explicit review panel');
    let panel = await openRecipe(page);
    assert(await panel.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await panel.getByText('Lihat rumus HPP', { exact: true }).click();
    await panel.getByText(/Biaya satuan = total harga beli/).waitFor();
    await panel.getByText('Lihat sumber dari cerita', { exact: true }).first().click();
    assert((await panel.innerText()).includes('Menu lama fixture'));
    assert((await panel.innerText()).includes('Sebelumnya 18.000'));
    assert((await panel.innerText()).includes('40,00000001'));
    await panel.getByLabel(/Bahan, harga, takaran/).check();
    assert(await panel.getByRole('button', { name: 'Approve dan simpan resep' }).isEnabled());
    await closePanel(page);
    assert(await page.getByRole('button', { name: 'Lihat resep', exact: true }).evaluate(el => el === document.activeElement));
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Koreksi takaran ayam');
    panel = await openRecipe(page);
    assert(await panel.getByLabel(/Bahan, harga, takaran/).isDisabled());
    assert(await panel.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await closePanel(page);
    await page.getByLabel('Estimasi', { exact: true }).check();
    const messagesBeforeNewline = calls.filter(c => c.path.endsWith('/messages')).length;
    await page.getByLabel('Tulis pesan', { exact: true }).press('Shift+Enter');
    assert.equal(calls.filter(c => c.path.endsWith('/messages')).length, messagesBeforeNewline);
    await page.getByLabel('Tulis pesan', { exact: true }).press('Enter');
    await page.getByText('Estimasi HPP per porsi', { exact: true }).waitFor();
    assert.equal(chats[0].revision, 2);
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByText('Estimasi HPP per porsi', { exact: true }).waitFor();
    assert.equal(chats[0].turns.length, 2);
    await page.getByRole('button', { name: 'Riwayat obrolan' }).click();
    assert.equal(await page.locator('.hpp-chat-session[aria-current="true"]').count(), 1);
    await page.getByRole('dialog').getByRole('button', { name: 'Nasi ayam fixture Draft' }).click();
    await page.locator('dialog').waitFor({ state: 'hidden' });

    for (const theme of ['light', 'dark']) for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.evaluate(t => { document.documentElement.classList.toggle('dark', t === 'dark'); document.documentElement.dataset.theme = t; }, theme);
      await appearance(page, theme + '/' + width);
      if (width === 320 || width === 1440) await page.screenshot({ path: '/tmp/selaris-hpp-modern-' + theme + '-' + width + '.png', fullPage: true });
      panel = await openRecipe(page);
      await appearance(page, 'review/' + theme + '/' + width);
      if (width === 320 || width === 1440) await page.screenshot({ path: '/tmp/selaris-hpp-modern-review-' + theme + '-' + width + '.png' });
      for (let i = 0; i < 18; i++) {
        await page.keyboard.press(i % 3 ? 'Tab' : 'Shift+Tab');
        assert(await page.evaluate(() => !!document.activeElement.closest('dialog')), 'Focus must stay in review');
      }
      await closePanel(page);
    }
    await page.setViewportSize({ width: 320, height: 420 });
    await page.addStyleTag({ content: 'html { font-size: 200%; }' });
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Koreksi untuk uji keyboard');
    await page.getByLabel('Tulis pesan', { exact: true }).focus();
    await page.getByLabel('Tulis pesan', { exact: true }).evaluate(el => el.scrollIntoView({ block: 'nearest' }));
    await appearance(page, '200% text/short viewport');
    await page.keyboard.press('Tab');
    assert.notEqual(await page.evaluate(() => getComputedStyle(document.activeElement.closest('label') || document.activeElement).outlineStyle), 'none');
    panel = await openRecipe(page);
    await appearance(page, 'review/200% text/short viewport');
    await closePanel(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByLabel('Tulis pesan', { exact: true }).fill('');

    panel = await openRecipe(page);
    failure = { status: 409, detail: 'Harga sudah berubah. Muat draft terbaru.' };
    await panel.getByLabel(/Bahan, harga, takaran/).check();
    await panel.getByRole('button', { name: 'Approve dan simpan resep' }).click();
    await panel.getByRole('alert').filter({ hasText: 'Harga sudah berubah' }).waitFor();
    assert(await panel.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await panel.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await panel.getByTestId('hpp-review-total').filter({ hasText: '10.000' }).waitFor();
    assert(!(await panel.getByLabel(/Bahan, harga, takaran/).isChecked()));
    await panel.getByLabel(/Bahan, harga, takaran/).check();
    failure = { status: 500, detail: 'INTERNAL SECRET' };
    const approvals = calls.filter(c => c.path.endsWith('/approve')).length;
    await panel.getByRole('button', { name: 'Approve dan simpan resep' }).click();
    await panel.getByRole('alert').filter({ hasText: 'Hasil belum dapat dipastikan' }).waitFor();
    assert(!(await page.locator('body').innerText()).includes('INTERNAL SECRET'));
    assert.equal(chats[0].status, 'applied');
    assert(await panel.getByRole('button', { name: 'Approve dan simpan resep' }).isDisabled());
    await panel.getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await panel.getByRole('button', { name: 'Approve dan simpan resep' }).waitFor({ state: 'hidden' });
    await closePanel(page);
    await page.getByText('Bahan dan resep sudah tersimpan.', { exact: true }).waitFor();
    assert.equal(calls.filter(c => c.path.endsWith('/approve')).length, approvals + 1);
    assert((await page.locator('body').innerText()).includes('Menu baru masih nonaktif'));

    await page.getByRole('button', { name: 'Resep baru', exact: true }).first().click();
    incomplete = true;
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Aku bingung jumlah pembelian.');
    await page.getByLabel('Tulis pesan', { exact: true }).press('Enter');
    await page.getByTestId('hpp-chat-total').filter({ hasText: 'Belum lengkap' }).waitFor();
    for (const theme of ['light', 'dark']) {
      await page.setViewportSize({ width: 320, height: 900 });
      await page.evaluate(t => { document.documentElement.classList.toggle('dark', t === 'dark'); }, theme);
      await appearance(page, 'incomplete assistance/' + theme + '/320');
    }
    panel = await openRecipe(page);
    await panel.getByText('Masih perlu dilengkapi', { exact: true }).waitFor();
    assert(await panel.getByLabel(/Bahan, harga, takaran/).isDisabled());
    await closePanel(page);
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Koreksi belum terkirim');
    assert(await page.getByRole('button', { name: 'Lengkapi estimasi', exact: true }).isDisabled());
    await page.getByLabel('Tulis pesan', { exact: true }).fill('');
    incomplete = false; processing = true;
    await page.getByRole('button', { name: 'Lengkapi estimasi', exact: true }).click();
    await page.getByText('Menyiapkan jawaban...', { exact: true }).waitFor();
    await page.waitForFunction(() => !document.querySelector('#hpp-chat-message').disabled);
    const pending = chats.at(-1);
    assert.equal(calls.filter(c => c.path.endsWith('/messages')).at(-1).body.mode, 'estimate');
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Koreksi berikutnya belum dikirim');
    assert(await page.getByRole('button', { name: 'Kirim pesan' }).isDisabled());
    pending.retry_allowed = true; processing = false;
    await page.getByRole('button', { name: 'Riwayat obrolan' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Periksa percakapan', exact: true }).click();
    await closePanel(page);
    await page.getByRole('button', { name: 'Proses ulang pesan terakhir' }).click();
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    assert.equal(pending.turns.length, 2);
    assert.equal(await page.getByLabel('Tulis pesan', { exact: true }).inputValue(), 'Koreksi berikutnya belum dikirim');
    await page.getByLabel('Tulis pesan', { exact: true }).fill('');

    replacement = true;
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Ganti resep aktif');
    await page.getByLabel('Tulis pesan', { exact: true }).press('Enter');
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    panel = await openRecipe(page);
    await panel.getByLabel(/Ganti resep aktif produk/).waitFor();
    await panel.getByLabel(/Bahan, harga, takaran/).check();
    assert(await panel.getByRole('button', { name: 'Approve dan ganti resep' }).isDisabled());
    await panel.getByLabel(/Ganti resep aktif produk/).check();
    assert(await panel.getByRole('button', { name: 'Approve dan ganti resep' }).isEnabled());
    await closePanel(page);
    replacement = false;
    await page.getByRole('button', { name: 'Resep baru', exact: true }).first().click();
    processing = true;
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Proses resep panjang di latar belakang.');
    const messageCount = calls.filter(c => c.path.endsWith('/messages')).length;
    await page.getByLabel('Tulis pesan', { exact: true }).press('Enter');
    await page.getByText('Menyiapkan jawaban...', { exact: true }).waitFor();
    await page.waitForFunction(() => document.querySelector('#hpp-chat-message')?.value === '');
    const automatic = chats.at(-1);
    automatic.pending = false; automatic.turns.at(-1).reply = 'Resepnya sudah siap. Kamu bisa cek lewat Lihat resep.';
    automatic.revision++; automatic.preview = preview(automatic.mode, automatic.revision); processing = false;
    await page.getByTestId('hpp-chat-total').filter({ hasText: '9.876,54' }).waitFor();
    await page.getByText('Resepnya sudah siap. Kamu bisa cek lewat Lihat resep.', { exact: true }).waitFor();
    assert.equal(calls.filter(c => c.path.endsWith('/messages')).length, messageCount + 1);
    assert(!calls.some(c => /restock|stock-mode|apply-recipe/.test(c.path)));
    assert.deepEqual(errors, []);
    console.log('PASS modern HPP chat: Enter/Shift+Enter, long input, compact server draft, review drawer, provenance/precision, history/resume/navigation, approval/replacement/unsent guards, 409/500 read-only recovery, pending polling and retry preserving typed correction; five widths/two themes AA/44px/dialog focus/Escape/200%/short viewport; fixture writes only.');
  } finally { await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
