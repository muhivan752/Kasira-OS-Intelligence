// Every account write goes to the localhost fixture.
const http = require('node:http'), assert = require('node:assert/strict'), { randomUUID } = require('node:crypto');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3315';
const id = '11111111-1111-4111-8111-111111111111', uid = '22222222-2222-4222-8222-222222222222', role = '33333333-3333-4333-8333-333333333333';
let canAccounts = true, shop = 'fixture-coffee', failure = '', failRead = false;
const calls = [], saved = new Map();
const employees = [{ id, code: 'KRY-0001', name: 'Irfan fixture', position: 'Barista', outlet_id: id, user_id: uid, phone: '6285270782220', started_on: '2026-01-01', ended_on: null, is_active: true, notes: null, row_version: 1 }];
const permissions = () => ['hris.employees.manage', 'hris.self', ...(canAccounts ? ['hris.accounts.manage', 'access.manage'] : [])];
const fixture = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {}, path = new URL(req.url, 'http://fixture').pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body }); let data = [], status = 200;
  if (path.endsWith('/users/me')) data = { id, full_name: 'Fixture pengelola', subscription_tier: 'pro' };
  else if (path.endsWith('/auth/access')) data = { user_id: id, tenant_id: id, enforcement_mode: 'owner', scope: 'tenant', access_version: 'fixture', permissions: permissions(), outlets: [{ id, name: 'Outlet fixture', timezone: 'Asia/Jakarta' }] };
  else if (path.endsWith('/hris/setup')) {
    if (failRead) status = 500;
    data = { is_manager: true, permissions: permissions(), self_employee: null, open_attendance: null, workspace_key: 'staff-fixture',
      outlets: [{ id, name: 'Outlet fixture', timezone: 'Asia/Jakarta' }], account_admin: canAccounts, shop_username: shop,
      roles: [{ id: role, name: 'Kasir fixture', scope: 'outlet', outlet_ids: [id] }],
      accounts: canAccounts ? [{ id: uid, name: 'Irfan fixture', username: 'irfan', row_version: 2, role_id: role, password_enabled: true, employee_id: id }] : [] };
  } else if (path.endsWith('/hris/workspace')) data = { items: employees, total: employees.length, skip: 0, limit: 50, timezone: 'Asia/Jakarta', generated_at: '2026-10-06T10:00:00Z', summary: { active_employees: employees.length, scheduled: null, present: null, leave: null, open: null, unrecorded_started: null } };
  else if (path.includes('/hris/requests/')) data = saved.has(path.split('/').at(-1)) ? { state: 'saved', result: saved.get(path.split('/').at(-1)) } : { state: 'unknown' };
  else if (path.includes('/hris/employees') && ['POST', 'PUT'].includes(req.method)) {
    const stored = saved.get(body.client_request_id);
    data = stored || { id: req.method === 'PUT' ? path.split('/').at(-1) : randomUUID(), row_version: (body.row_version || 0) + 1, account_configured: Boolean(body.account) };
    if (failure !== 'drop' && !stored) {
      saved.set(body.client_request_id, data);
      const employee = { ...body, ...data, code: 'KRY-0002', user_id: body.user_id || (body.account ? randomUUID() : null) };
      if (req.method === 'PUT') Object.assign(employees.find(e => e.id === data.id), employee); else employees.push(employee);
    }
    if (failure) { status = 500; failure = ''; }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(status === 500 ? { detail: 'PRIVATE SERVER DETAIL' } : { success: true, data }));
});

async function appearance(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, label + ' overflow');
  const issues = await page.getByRole('dialog').evaluate(root => {
    const lum = value => value.match(/[\d.]+/g).slice(0, 3).map(Number).map(x => x / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4).reduce((s, x, i) => s + x * [.2126, .7152, .0722][i], 0);
    const issues = [];
    for (const el of root.querySelectorAll('*')) {
      const style = getComputedStyle(el), box = el.getBoundingClientRect();
      if (!box.width || !box.height || el.tagName === 'OPTION' || style.visibility === 'hidden' || el.closest(':disabled') || el.type === 'hidden') continue;
      if (['BUTTON', 'SELECT', 'INPUT'].includes(el.tagName) && (box.width < 43 || box.height < 43)) issues.push('target ' + el.textContent);
      if (!Array.from(el.childNodes).some(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())) continue;
      let bg = el; while (bg.parentElement && ['transparent', 'rgba(0, 0, 0, 0)'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
      const a = lum(style.color), b = lum(getComputedStyle(bg).backgroundColor);
      if ((Math.max(a, b) + .05) / (Math.min(a, b) + .05) < 4.5) issues.push('contrast ' + el.textContent.trim().slice(0, 30));
    }
    return issues;
  });
  assert.deepEqual(issues, [], label);
}

(async () => {
  await new Promise(resolve => fixture.listen(Number(process.env.FIXTURE_PORT || 8189), '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] }); let page;
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await context.tracing.start({ screenshots: true, snapshots: true });
    await context.route(/https?:\/\/(?!127\.0\.0\.1|localhost)/, route => route.abort());
    await context.addCookies(Object.entries({ token: 'fixture-token', tenant_id: id, outlet_id: id }).map(([name, value]) => ({ name, value, url: base })));
    page = await context.newPage(); const errors = []; page.on('pageerror', e => errors.push(e.message));
    const ready = () => page.locator('.hr-summary').waitFor(), dialog = () => page.getByRole('dialog');
    const close = async () => { await page.keyboard.press('Escape'); await dialog().waitFor({ state: 'hidden' }); };
    const openNew = async () => { await page.getByRole('button', { name: 'Tambah karyawan', exact: true }).click(); await dialog().waitFor(); };
    const fill = async name => { await page.getByLabel('Nama karyawan', { exact: true }).fill(name); await page.getByLabel('Jabatan / tugas').fill('Barista'); await page.getByLabel('Nomor HP', { exact: true }).fill('085270782220'); await page.getByLabel('Password awal', { exact: true }).fill('qa-secret-staff'); await page.getByLabel('Ulangi password awal', { exact: true }).fill('qa-secret-staff'); };
    const retryButton = () => page.locator('.hris-workspace > .f-notice').getByRole('button', { name: 'Periksa penyimpanan', exact: true });
    await page.goto(base + '/dashboard/hris'); await ready();
    await page.getByRole('button', { name: 'Edit karyawan Irfan fixture' }).click();
    assert.equal(await page.getByLabel('Hubungkan akun kasir').inputValue(), uid);
    assert.equal(await page.getByLabel('Password awal', { exact: true }).count(), 0);
    await page.getByLabel('Pengaturan login').selectOption('configure'); await page.getByLabel('Masuk menggunakan').selectOption('username');
    assert.equal(await page.getByLabel('Username akun', { exact: true }).inputValue(), 'irfan');
    assert.equal(await page.getByLabel('Hak akses', { exact: true }).inputValue(), '');
    await dialog().getByLabel('Password', { exact: true }).selectOption('reset'); await fill('Irfan fixture');
    await dialog().getByRole('button', { name: 'Simpan', exact: true }).click(); await dialog().waitFor({ state: 'hidden' }); await ready();
    const reused = calls.find(c => c.method === 'PUT'); assert.equal(reused.body.user_id, uid); assert.equal(reused.body.account.user_row_version, 2); assert.equal(reused.body.account.role_id, null);
    console.log('PASS existing Irfan account reuse, explicit login/reset, old account version and role preserved in submission');
    await openNew(); assert.equal(await page.getByLabel('Akun karyawan', { exact: true }).inputValue(), 'new');
    await fill('Fixture akun baru'); await page.getByLabel('Hak akses', { exact: true }).selectOption(role);
    for (const label of ['Password awal', 'Ulangi password awal']) {
      const input = page.getByLabel(label, { exact: true }), before = calls.filter(c => c.method !== 'GET').length;
      const show = page.getByRole('button', { name: 'Tampilkan ' + label.toLowerCase(), exact: true });
      assert.equal(await show.getAttribute('type'), 'button'); await show.click(); assert.equal(await input.getAttribute('type'), 'text');
      await page.getByRole('button', { name: 'Sembunyikan ' + label.toLowerCase(), exact: true }).press('Space');
      assert.equal(await input.getAttribute('type'), 'password'); assert.equal(await input.inputValue(), 'qa-secret-staff'); assert.equal(calls.filter(c => c.method !== 'GET').length, before);
    }
    await page.getByLabel('Ulangi password awal', { exact: true }).fill('qa-different'); await dialog().getByRole('button', { name: 'Simpan', exact: true }).click(); await dialog().getByRole('alert').filter({ hasText: 'Ulangi password harus sama' }).waitFor();
    await page.getByLabel('Ulangi password awal', { exact: true }).fill('qa-secret-staff');
    await page.getByLabel('Masuk menggunakan').selectOption('username'); await page.getByLabel('Username akun', { exact: true }).fill('Irfan Coffee'); assert.equal(await page.getByLabel('Username akun', { exact: true }).evaluate(el => el.checkValidity()), false);
    await page.getByLabel('Username akun', { exact: true }).fill('irfan2'); await page.getByLabel('Masuk menggunakan').selectOption('phone');
    failure = 'saved'; await dialog().getByRole('button', { name: 'Simpan', exact: true }).click(); await dialog().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).waitFor();
    assert(!await page.locator('body').innerText().then(t => t.includes('PRIVATE SERVER DETAIL')));
    assert.equal(await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage))).includes('qa-secret-staff')), false);
    const writeCount = calls.filter(c => c.method === 'POST' && c.path.endsWith('/hris/employees')).length;
    await close(); await page.reload(); await ready(); await retryButton().click(); await retryButton().waitFor({ state: 'hidden' }); await ready();
    assert.equal(calls.filter(c => c.method === 'POST' && c.path.endsWith('/hris/employees')).length, writeCount);
    console.log('PASS phone/username choices, role selection, password confirmation/visibility and validation; reload confirms saved receipt without storing/re-sending password');
    await openNew(); await fill('Fixture koneksi putus'); await page.getByLabel('Masuk menggunakan').selectOption('username'); await page.getByLabel('Username akun', { exact: true }).fill('new-staff');
    failure = 'drop'; await dialog().getByRole('button', { name: 'Simpan', exact: true }).click(); await dialog().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).waitFor();
    const interrupted = calls.filter(c => c.method === 'POST' && c.path.endsWith('/hris/employees')).at(-1).body.client_request_id;
    await close(); await page.reload(); await ready(); await retryButton().click(); await page.getByLabel('Password awal untuk melanjutkan', { exact: true }).waitFor();
    await page.getByLabel('Password awal untuk melanjutkan', { exact: true }).fill('qa-secret-staff'); await retryButton().click(); await retryButton().waitFor({ state: 'hidden' }); await ready();
    const resumed = calls.filter(c => c.method === 'POST' && c.path.endsWith('/hris/employees')).at(-1).body;
    assert.equal(resumed.client_request_id, interrupted); assert.equal(resumed.account.password, 'qa-secret-staff');
    assert.equal(await page.evaluate(() => sessionStorage.length), 0);
    console.log('PASS unsaved request after reload asks for password again and resumes same UUID; secret and pending state cleared after success');
    for (const theme of ['light', 'dark']) for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 }); await page.evaluate(t => document.documentElement.classList.toggle('dark', t === 'dark'), theme);
      await openNew(); await appearance(page, `${theme} ${width}`); await page.getByLabel('Masuk menggunakan').selectOption('username'); await appearance(page, `${theme} ${width} username`);
      await page.evaluate(() => document.documentElement.style.fontSize = '200%'); await appearance(page, `${theme} ${width} 200%`); await page.evaluate(() => document.documentElement.style.fontSize = '');
      await page.getByLabel('Akun karyawan', { exact: true }).selectOption('profile'); await appearance(page, `${theme} ${width} profile`); await close();
    }
    await page.setViewportSize({ width: 375, height: 900 }); await page.evaluate(() => document.documentElement.classList.remove('dark')); await openNew(); await page.screenshot({ path: '/tmp/selaris-staff-mobile.png', fullPage: true });
    await page.getByLabel('Nama karyawan', { exact: true }).focus(); await page.keyboard.press('Shift+Tab'); assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Tutup'); assert.equal(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle === 'none'), false); await close();
    console.log('PASS four widths/two themes, phone/username/profile modes, 200% text, AA contrast, 44px targets, visible keyboard focus and Escape');
    await openNew(); await page.getByLabel('Akun karyawan', { exact: true }).selectOption('profile'); await page.getByLabel('Nama karyawan', { exact: true }).fill('Fixture profil saja'); await page.getByLabel('Jabatan / tugas').fill('Barista'); await dialog().getByRole('button', { name: 'Simpan', exact: true }).click(); await dialog().waitFor({ state: 'hidden' }); await ready();
    assert.equal(calls.filter(c => c.method === 'POST' && c.path.endsWith('/hris/employees')).at(-1).body.account, undefined);
    shop = null; await page.reload(); await ready(); await openNew(); await dialog().getByRole('link', { name: 'Akun saya', exact: true }).waitFor(); assert.equal(await page.getByLabel('Password awal', { exact: true }).count(), 0); await close();
    canAccounts = false; await page.reload(); await ready(); await openNew(); assert.equal(await page.getByLabel('Akun karyawan', { exact: true }).count(), 0); assert.match(await dialog().innerText(), /memerlukan izin dari pemilik/); await close();
    failRead = true; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await page.locator('.hris-workspace [role=alert]').waitFor(); failRead = false; await page.getByRole('button', { name: 'Coba lagi', exact: true }).click(); await ready();
    assert.deepEqual(errors, []); await context.tracing.stop({ path: '/tmp/selaris-staff-browser-trace.zip' });
    console.log('PASS profile-only saves, shop prerequisite, restricted manager controls, read error/retry; no page errors');
  } catch (error) { if (page) await page.screenshot({ path: '/tmp/selaris-staff-browser-failure.png', fullPage: true }); throw error; }
  finally { await browser.close(); fixture.close(); }
})();
