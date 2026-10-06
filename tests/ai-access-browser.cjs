// Local synthetic backend only; authorization is covered by ai-access-isolated.py.
const http = require('node:http'), assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3313';
const a = '11111111-1111-4111-8111-111111111111', b = '22222222-2222-4222-8222-222222222222';
let permissions = ['ai.chat', 'hpp.view', 'hpp.manage', 'supplier.price.view'];
const outlets = [{ id: a, brand_id: a, name: 'Outlet A fixture' }, { id: b, brand_id: b, name: 'Outlet B fixture' }];
const calls = [], chats = [];
const preview = { product_name: 'Resep fixture', product_id: a, new_product: false, replaces_recipe: false,
  servings: '1', servings_source: 'estimate', servings_evidence: '', lines: [], is_estimated: true,
  ready: true, missing: [], total_cost: '100', fingerprint: '0'.repeat(64), notes: '' };
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw && !req.headers['content-type']?.startsWith('multipart') ? JSON.parse(raw) : {};
  const url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body, query: url.search });
  let data = [], status = 200;
  if (path.endsWith('/auth/access')) data = { user_id: a, tenant_id: a, enforcement_mode: 'managed', scope: 'outlet',
    permissions, outlets, access_version: permissions.join(',') };
  else if (path.endsWith('/users/me')) data = { id: a, full_name: 'Staf fixture', subscription_tier: 'pro', subscription_status: 'active' };
  else if (path.endsWith('/outlets')) data = outlets;
  else if (path.endsWith('/products')) data = [{ id: a, brand_id: url.searchParams.get('brand_id'), name: 'Menu fixture', is_active: true, base_price: 1000 }];
  else if (path.endsWith('/recipes')) data = [];
  else if (path.endsWith('/ai/chat')) {
    if (!permissions.includes('ai.chat')) status = 403;
    else { res.writeHead(200, { 'Content-Type': 'text/event-stream' }); res.end('data: ' + JSON.stringify({ type: 'chunk', content: 'Jawaban AI fixture untuk ' + body.outlet_id }) + '\n\ndata: ' + JSON.stringify({ type: 'done', conversation_id: body.conversation_id || a }) + '\n\n'); return; }
  } else if (path.endsWith('/sessions') && req.method === 'GET') data = chats.filter(c => c.outlet_id === url.searchParams.get('outlet_id'));
  else if (path.endsWith('/sessions') && req.method === 'POST') {
    data = { id: a, outlet_id: body.outlet_id, mode: body.mode, status: 'draft', revision: 0, preview: null,
      result: null, pending: false, error: null, retry_allowed: false, turns: [], can_approve: permissions.includes('hpp.approve') };
    chats.push(data);
  } else if (path.includes('/sessions/')) {
    data = chats[0];
    if (path.endsWith('/messages')) { data.preview = preview; data.revision++; data.turns.push({ id: body.request_id, mode: body.mode, message: body.message, reply: 'Draft fixture siap diperiksa.' }); }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(status >= 400 ? { detail: 'Tidak diizinkan' } : { data }));
});

async function appearance(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, label + ' overflow');
  const failures = await page.locator('main').evaluate(root => {
    const lum = color => { const x = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(v => (v /= 255) <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4); return x[0] * .2126 + x[1] * .7152 + x[2] * .0722; };
    const failures = [];
    for (const el of root.querySelectorAll('*')) {
      const s = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || el.tagName === 'OPTION' || el.closest(':disabled') || s.visibility === 'hidden') continue;
      if (el.matches('button,textarea,select,input,a[href]') && !el.closest('label') && (box.height < 43 || box.width < 43)) failures.push('target ' + el.textContent);
      if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      let bg = s.backgroundColor, node = el;
      while (bg === 'rgba(0, 0, 0, 0)' && node.parentElement) { node = node.parentElement; bg = getComputedStyle(node).backgroundColor; }
      if (bg === 'rgba(0, 0, 0, 0)') bg = 'rgb(255,255,255)';
      const values = [lum(s.color), lum(bg)].sort((a, b) => b - a);
      const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && parseInt(s.fontWeight) >= 700);
      if ((values[0] + .05) / (values[1] + .05) < (large ? 3 : 4.5) - .01) failures.push('contrast ' + el.textContent.slice(0, 50));
    }
    return failures;
  });
  assert.deepEqual(failures, [], label);
}

(async () => {
  await new Promise(resolve => fixture.listen(Number(process.env.FIXTURE_PORT || 8189), '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await context.tracing.start({ screenshots: true, snapshots: true });
    await context.addCookies(['token', 'tenant_id', 'outlet_id'].map(name => ({ name, value: name === 'token' ? 'fixture' : name === 'outlet_id' ? b : a, url: base })));
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/dashboard/ai', { waitUntil: 'networkidle' });
    await page.getByLabel('Pertanyaan Anda').waitFor();
    assert.equal(await page.getByLabel('Outlet AI').inputValue(), b);
    assert.equal(await page.getByRole('link', { name: 'Susun draft HPP' }).count(), 1);
    for (const width of [320, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 }); await appearance(page, 'AI light ' + width);
      if ([320, 1440].includes(width)) await page.screenshot({ path: `/tmp/selaris-ai-managed-light-${width}.png`, fullPage: true });
      await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await appearance(page, 'AI dark ' + width);
      if ([320, 1440].includes(width)) await page.screenshot({ path: `/tmp/selaris-ai-managed-dark-${width}.png`, fullPage: true });
      await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    }
    await page.getByLabel('Pertanyaan Anda').fill('Pertanyaan fixture pertama'); await page.getByLabel('Pertanyaan Anda').press('Enter');
    await page.getByRole('log').getByText('Jawaban AI fixture untuk ' + b).waitFor();
    await page.getByLabel('Pertanyaan Anda').fill('Pertanyaan fixture kedua'); await page.getByRole('button', { name: 'Kirim pertanyaan' }).click();
    await page.waitForFunction(() => document.querySelector('[role=log]')?.textContent.includes('fixture kedua'));
    await page.getByLabel('Pertanyaan Anda').waitFor(); await page.waitForTimeout(400);
    assert.equal(calls.filter(c => c.path.endsWith('/ai/chat')).at(-1).body.conversation_id, a);
    await page.getByLabel('Outlet AI').selectOption(a);
    assert.equal(await page.getByRole('log').getByText('Jawaban AI fixture untuk ' + b).count(), 0);
    await page.getByLabel('Pertanyaan Anda').fill('Outlet A fixture'); await page.getByRole('button', { name: 'Kirim pertanyaan' }).click();
    await page.getByRole('log').getByText('Jawaban AI fixture untuk ' + a).waitFor();
    assert.equal(calls.filter(c => c.path.endsWith('/ai/chat')).at(-1).body.conversation_id, undefined);
    await page.evaluate(() => document.documentElement.style.fontSize = '200%'); await appearance(page, 'AI 200%');
    await page.evaluate(() => document.documentElement.style.fontSize = '');
    console.log('PASS managed AI navigation, selected outlet, SSE, conversation reset, four widths, light/dark, AA, 44px and 200%');

    await page.goto(base + '/dashboard/hpp');
    await page.getByRole('link', { name: 'Atur lewat percakapan' }).waitFor();
    await page.getByLabel('Outlet', { exact: true }).selectOption(a);
    await page.waitForTimeout(350);
    await page.getByRole('link', { name: 'Atur lewat percakapan' }).click();
    await page.getByLabel('Tulis pesan', { exact: true }).waitFor();
    await page.getByLabel('Tulis pesan', { exact: true }).fill('Draft fixture tanpa persetujuan');
    await page.getByLabel('Kirim pesan', { exact: true }).click();
    await page.getByRole('button', { name: 'Lihat resep', exact: true }).click();
    await page.getByText('Draft belum tersimpan. Akun ini belum memiliki izin persetujuan resep.').waitFor();
    assert.equal(await page.getByRole('button', { name: /Approve dan/ }).count(), 0);
    assert.equal(calls.find(c => c.path.endsWith('/sessions') && c.method === 'POST').body.outlet_id, a);
    await appearance(page, 'HPP draft only');
    await page.getByLabel('Tutup panel').press('Escape');
    console.log('PASS selected HPP outlet survives link/server actions; draft-only review has no approval action; keyboard dialog');

    await page.goto(base + '/dashboard/ai'); await page.getByLabel('Pertanyaan Anda').waitFor();
    await page.getByLabel('Pertanyaan Anda').fill('Pembersihan versi akses'); await page.getByRole('button', { name: 'Kirim pertanyaan' }).click();
    await page.getByRole('log').getByText('Jawaban AI fixture untuk ' + b).waitFor();
    permissions = ['hpp.view']; await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await page.getByText('Fitur ini belum tersedia untuk pengaturan akses akun Anda.').waitFor();
    assert.equal(await page.getByRole('log').count(), 0);
    assert.equal(await page.getByRole('link', { name: 'AI Asisten', exact: true }).count(), 0);
    assert.deepEqual(errors, []);
    await context.tracing.stop({ path: '/tmp/selaris-ai-access-browser-trace.zip' });
    console.log('PASS foreground access revocation unmounts old AI conversation and hides navigation; no browser errors');
  } finally { await browser.close(); fixture.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; fixture.close(); });
