const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3188';
const id = '11111111-1111-4111-8111-111111111111';
const eid = '22222222-2222-4222-8222-222222222222';
const calls = [];
let passwordEnabled = false;
let failLogout = false;
let failSetup = false, failAccount = false;
const roles = [], accounts = [];
const employee = { id: eid, name: 'QA staf', user_id: null, outlet_id: id, row_version: 1, is_active: true };
const manifest = staff => ({ user_id: staff ? eid : id, tenant_id: id, enforcement_mode: staff ? 'managed' : 'owner', scope: staff ? 'outlet' : 'tenant', permissions: staff ? ['hris.self'] : ['hris.self', 'hris.employees.manage', 'hris.schedules.manage', 'hris.attendance.manage', 'access.manage'], outlets: [{ id, name: 'QA outlet', timezone: 'Asia/Jakarta' }] });
const session = staff => ({ access_token: staff ? 'fixture-staff' : 'fixture-owner', user_id: staff ? eid : id, tenant_id: id, outlet_id: id, subscription_tier: 'starter', stock_mode: 'simple', access: manifest(staff) });
const fixture = http.createServer(async (req, res) => {
  let text = ''; for await (const chunk of req) text += chunk;
  const body = text ? JSON.parse(text) : {};
  const url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, body });
  const staff = req.headers.authorization?.includes('fixture-staff');
  let data = [], status = 200, detail;
  if (path.endsWith('/auth/password/login')) { if (body.password === 'wrong') { status = 401; detail = 'Password tidak sesuai'; } else data = session(body.username === 'staff'); }
  else if (path.endsWith('/auth/password/register') || path.endsWith('/auth/password/claim')) {
    if (body.shop_username.includes(' ')) { status = 422; detail = [{ loc: ['body', 'shop_username'], msg: 'Value error, Gunakan 3 sampai 64 huruf, angka, tanda hubung atau garis bawah' }]; }
    else { passwordEnabled = true; data = { ...session(false), recovery_code: 'a'.repeat(64) }; }
  }
  else if (path.endsWith('/auth/password/challenge')) { if (body.code === '0'.repeat(64)) { status = 401; detail = 'Kode tidak sesuai'; } else data = { ...session(body.purpose === 'activation'), ...(body.purpose === 'recovery' ? { recovery_code: 'c'.repeat(64) } : {}) }; }
  else if (path.endsWith('/auth/providers')) data = { google: { enabled: false, web_config: null }, sefrekuensi: true };
  else if (path.endsWith('/auth/otp/send')) data = { channel: body.channel };
  else if (path.endsWith('/auth/otp/verify')) data = session(false);
  else if (path.endsWith('/auth/access')) data = manifest(staff);
  else if (path.endsWith('/auth/account')) { if (failAccount) { status = 503; detail = 'QA account unavailable'; } else data = { shop_username: passwordEnabled ? 'qa-shop' : null, username: passwordEnabled ? 'owner' : null, password_enabled: passwordEnabled }; }
  else if (path.endsWith('/auth/sessions')) data = [{ id, current: true, created_at: '2026-10-06T10:00:00Z' }];
  else if (path.endsWith('/users/me')) data = { id, full_name: 'QA owner', subscription_tier: 'starter', subscription_status: 'active' };
  else if (path.endsWith('/superadmin/stats')) data = { total_tenants: 0, active_tenants: 0, total_users: 0, new_tenants_7d: 0, starter_count: 0, pro_count: 0, business_count: 0 };
  else if (path.endsWith('/auth/logout')) { if (failLogout) { status = 503; detail = 'QA retry'; } else data = { ok: true }; }
  else if (path.endsWith('/auth/sessions/revoke-all')) data = { ok: true };
  else if (path.endsWith('/hris/access/setup')) { if (failSetup) { status = 503; detail = 'QA setup unavailable'; } else data = { shop_username: passwordEnabled ? 'qa-shop' : null, roles, accounts, employees: [employee], outlets: manifest(false).outlets }; }
  else if (path.endsWith('/hris/access/roles')) { data = { ...body, row_version: body.row_version + 1, editable: true, policy: { outlet_ids: body.outlet_ids, permissions: body.permissions } }; const index = roles.findIndex(role => role.id === body.id); if (index < 0) roles.push(data); else roles[index] = data; }
  else if (path.endsWith(`/hris/employees/${eid}/account`)) { data = { id: eid, full_name: 'QA staf', username: body.username, is_active: body.is_active, is_owner: false, role_id: body.role_id, row_version: (body.user_row_version || 0) + 1 }; const index = accounts.findIndex(account => account.id === eid); if (index < 0) accounts.push(data); else accounts[index] = data; employee.user_id = eid; employee.row_version += 1; }
  else if (path.endsWith(`/hris/employees/${eid}/activation`)) data = { code: 'b'.repeat(64), shop_username: 'qa-shop', username: 'staff', expires_at: '2026-10-07T10:00:00Z' };
  else if (path.endsWith('/hris/setup')) data = { workspace_key: `${id}:${staff ? eid : id}`, is_manager: !staff, permissions: manifest(staff).permissions, outlets: manifest(staff).outlets, accounts: [], self_employee: null, open_attendance: null };
  else if (path.endsWith('/hris/workspace')) data = { items: [], total: 0, skip: 0, limit: 50, timezone: 'Asia/Jakarta', generated_at: '2026-10-06T10:00:00Z', summary: { active_employees: staff ? null : 0, scheduled: 0, present: 0, leave: 0, open: 0, unrecorded_started: 0 } };
  res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(detail ? { detail } : { success: true, data }));
});

function ratio(a, b) {
  const lum = value => { const rgb = value.match(/[\d.]+/g).slice(0, 3).map(Number).map(v => (v /= 255) <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4); return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722; };
  const [x, y] = [lum(a), lum(b)].sort((a, b) => b - a); return (x + .05) / (y + .05);
}
async function layout(page, title) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${title}: overflow`);
  const samples = await page.evaluate(() => Array.from(document.querySelectorAll('.auth-content h1,.auth-content p,.auth-content label,.auth-content input,.auth-content textarea,.auth-content select,.auth-content button,.auth-content a,.finance-workspace h1,.finance-workspace h2,.finance-workspace p,.finance-workspace label,.finance-workspace button,.finance-workspace a')).flatMap(el => {
    if (el.disabled || !el.getClientRects().length) return [];
    const style = getComputedStyle(el); let current = el, bg = 'rgb(255,255,255)';
    while (current) { const value = getComputedStyle(current).backgroundColor; if (value.startsWith('rgb(')) { bg = value; break; } current = current.parentElement; }
    return [{ text: (el.textContent || el.value || '').slice(0, 40), color: style.color, bg, min: parseFloat(style.fontSize) >= 24 || parseFloat(style.fontSize) >= 18.67 && +style.fontWeight >= 700 ? 3 : 4.5 }];
  }));
  for (const sample of samples) assert(ratio(sample.color, sample.bg) >= sample.min, `${title}: contrast ${sample.text} ${ratio(sample.color, sample.bg)}`);
  console.log(`PASS ${title}: overflow and contrast`);
}

async function passwordVisibility(page, label) {
  const input = page.getByLabel(label, { exact: true });
  const original = await input.inputValue(), requestCount = calls.filter(c => c.method === 'POST').length;
  const show = page.getByRole('button', { name: `Tampilkan ${label.toLowerCase()}`, exact: true });
  assert.equal(await input.getAttribute('type'), 'password');
  assert.equal(await show.getAttribute('type'), 'button');
  await input.fill('qa-toggle-123'); await show.click();
  assert.equal(await input.getAttribute('type'), 'text');
  assert.equal(await input.inputValue(), 'qa-toggle-123');
  const hide = page.getByRole('button', { name: `Sembunyikan ${label.toLowerCase()}`, exact: true });
  assert.equal(await hide.getAttribute('aria-pressed'), 'true');
  const box = await hide.boundingBox(); assert(box.width >= 44 && box.height >= 44);
  await hide.focus(); await page.keyboard.press('Space');
  assert.equal(await input.getAttribute('type'), 'password');
  assert.equal(await input.inputValue(), 'qa-toggle-123');
  assert.equal(calls.filter(c => c.method === 'POST').length, requestCount, 'Visibility toggle must not submit the form');
  await input.fill(original);
}

(async () => {
  await new Promise(resolve => fixture.listen(Number(process.env.FIXTURE_PORT || 8188), '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'], ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
  let debugPage;
  try {
    const context = await browser.newContext({ viewport: { width: 320, height: 760 } }); const page = await context.newPage(); debugPage = page; const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    for (const width of process.env.QA_QUICK ? [320] : [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of ['login', 'register', 'activate', 'recover']) {
        await page.goto(`${base}/${route}`, { waitUntil: 'networkidle' }); await layout(page, `${route} ${width} light`);
        await passwordVisibility(page, route === 'login' ? 'Password' : 'Password baru');
        if (route !== 'login') await passwordVisibility(page, 'Ulangi password');
        await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await layout(page, `${route} ${width} dark`);
        await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
      }
    }
    await page.setViewportSize({ width: 320, height: 760 });
    await page.goto(`${base}/register`);
    assert.equal(await page.getByLabel('Password baru', { exact: true }).getAttribute('minlength'), '8');
    assert.equal(await page.getByLabel('Username toko', { exact: true }).getAttribute('minlength'), '3');
    await page.getByLabel('Username toko', { exact: true }).fill('qa-shop'); await page.getByLabel('Nama pemilik').fill('QA owner'); await page.getByLabel('Nama usaha').fill('QA shop');
    await page.getByLabel('Password baru', { exact: true }).fill('qa-short'); await page.getByLabel('Ulangi password', { exact: true }).fill('qa wrong password'); await page.getByRole('button', { name: 'Buat usaha', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Konfirmasi' }).waitFor();
    await page.getByLabel('Ulangi password', { exact: true }).fill('qa-short'); await page.getByRole('button', { name: 'Buat usaha', exact: true }).click();
    await page.getByLabel('Kode pemulihan', { exact: true }).waitFor(); await layout(page, 'Recovery code 320');
    assert(await page.getByRole('button', { name: 'Lanjut ke usaha' }).isDisabled()); await page.getByLabel('Saya sudah menyimpan kode ini').check(); await page.getByRole('button', { name: 'Lanjut ke usaha' }).click(); await page.waitForURL('**/onboarding');
    assert(calls.some(c => c.path.endsWith('/auth/password/register') && c.body.client_request_id));
    await context.clearCookies(); await page.goto(`${base}/login`);
    await page.getByLabel('Username toko', { exact: true }).fill('qa-shop'); await page.getByLabel('Password', { exact: true }).fill('wrong'); await page.getByRole('button', { name: 'Masuk ke usaha', exact: true }).click(); await page.getByRole('alert').filter({ hasText: 'Password tidak sesuai' }).waitFor();
    await page.getByLabel('Saya masuk sebagai karyawan').check(); await page.getByLabel('Username akun', { exact: true }).fill('staff'); await page.getByLabel('Password', { exact: true }).fill('qa strong password'); await page.getByRole('button', { name: 'Masuk ke usaha', exact: true }).click(); await page.waitForURL('**/dashboard/hris');
    await page.getByText('Tidak diizinkan', { exact: true }).waitFor(); await layout(page, 'Staff HRIS 320');
    assert(await page.getByRole('link', { name: 'Keuangan', exact: true }).count() === 0);
    await page.getByRole('button', { name: 'Buka menu', exact: true }).click(); await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('button', { name: 'Buka menu', exact: true }).getAttribute('aria-expanded'), 'false');
    await page.goto(`${base}/dashboard/keuangan`); await page.getByText('Fitur ini belum tersedia', { exact: false }).waitFor();
    console.log('PASS registration, recovery acknowledgement, failed login, individual staff landing and restricted navigation');

    await context.clearCookies(); passwordEnabled = false;
    await context.addCookies([{ name: 'token', value: 'fixture-owner', domain: '127.0.0.1', path: '/' }, { name: 'tenant_id', value: id, domain: '127.0.0.1', path: '/' }]);
    failSetup = true;
    await page.goto(`${base}/dashboard/hris/access`); await page.getByRole('button', { name: 'Muat ulang' }).waitFor();
    failSetup = false; failAccount = true;
    await page.getByRole('button', { name: 'Muat ulang' }).click(); await page.getByRole('button', { name: 'Coba lagi', exact: true }).waitFor();
    failAccount = false; await page.getByRole('button', { name: 'Coba lagi', exact: true }).click();
    await page.goto(`${base}/dashboard/hris/access`, { waitUntil: 'networkidle' }); await page.getByLabel('Username toko', { exact: true }).waitFor(); await layout(page, 'Access setup 320 light');
    await passwordVisibility(page, 'Password baru'); await passwordVisibility(page, 'Ulangi password');
    const claimCount = () => calls.filter(c => c.path.endsWith('/auth/password/claim')).length;
    const initialClaimCount = claimCount();
    await page.getByLabel('Username toko', { exact: true }).fill('Kasira Coffee'); await page.getByLabel('Password baru', { exact: true }).fill('qa strong password'); await page.getByLabel('Ulangi password', { exact: true }).fill('qa strong password');
    await page.getByRole('button', { name: 'Tetapkan username dan password' }).click();
    assert.equal(await page.getByLabel('Username toko', { exact: true }).evaluate(el => el.validity.patternMismatch), true);
    assert.equal(claimCount(), initialClaimCount, 'Username with spaces must be rejected before claiming the account');
    await page.getByText('Username untuk masuk, tanpa spasi.', { exact: false }).waitFor();
    await page.getByLabel('Username toko', { exact: true }).evaluate(el => el.form.noValidate = true);
    await page.getByRole('button', { name: 'Tetapkan username dan password' }).click();
    await page.getByRole('alert').filter({ hasText: 'Username toko: Gunakan 3 sampai 64' }).waitFor();
    assert.equal((await page.getByRole('alert').filter({ hasText: 'Username toko: Gunakan 3 sampai 64' }).innerText()).includes('Value error,'), false);
    for (const width of [320, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 }); await layout(page, `Migration username error ${width} light`);
      await passwordVisibility(page, 'Password baru'); await passwordVisibility(page, 'Ulangi password');
      if (width === 320) await page.screenshot({ path: '/tmp/selaris-username-error-mobile.png', fullPage: true });
      await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await layout(page, `Migration username error ${width} dark`);
      await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    }
    await page.setViewportSize({ width: 320, height: 900 });
    await page.evaluate(() => document.documentElement.style.fontSize = '200%'); await layout(page, 'Migration username error 200%'); await page.evaluate(() => document.documentElement.style.fontSize = '');
    await page.getByLabel('Username toko', { exact: true }).evaluate(el => el.form.noValidate = false);
    await page.getByLabel('Username toko', { exact: true }).fill('kasira_coffee'); await page.getByRole('button', { name: 'Tetapkan username dan password' }).click();
    assert.equal(calls.filter(c => c.path.endsWith('/auth/password/claim')).at(-1).body.shop_username, 'kasira_coffee');
    console.log('PASS migration username with spaces blocked locally; server error identifies username; corrected username succeeds');
    await page.getByLabel('Kode pemulihan baru').waitFor(); await page.getByRole('button', { name: 'Saya sudah menyimpan kode' }).click();
    await passwordVisibility(page, 'Password saat ini'); await passwordVisibility(page, 'Password baru'); await passwordVisibility(page, 'Ulangi password');
    await page.getByLabel('Password saat ini', { exact: true }).fill('qa strong password'); await page.getByLabel('Password baru', { exact: true }).fill('qa changed password'); await page.getByLabel('Ulangi password', { exact: true }).fill('qa changed password'); await page.getByRole('button', { name: 'Ganti password', exact: true }).click();
    await page.getByLabel('Kode pemulihan baru').waitFor(); await page.getByRole('button', { name: 'Saya sudah menyimpan kode' }).click();
    await page.getByLabel('Nama jabatan').fill('QA staf'); await page.getByLabel('QA outlet', { exact: true }).check(); await page.getByRole('button', { name: 'Simpan jabatan' }).click(); await page.getByRole('status').filter({ hasText: 'Perubahan tersimpan' }).waitFor();
    await page.getByLabel('Pilih jabatan').selectOption(roles[0].id);
    for (const label of ['Kelola profil karyawan', 'Kelola jadwal kerja', 'Kelola dan koreksi absensi', 'Buat pesanan dan terima pembayaran', 'Ajukan refund', 'Setujui atau tolak refund', 'Ubah harga transaksi dan diskon di atas 20%', 'Buka, jeda dan hitung sesi kas', 'Catat kas masuk dan keluar', 'Lihat pesanan dan ubah status dapur', 'Lihat riwayat seluruh kasir dan rincian penjualan', 'Lihat stok', 'Terima barang dan tambah stok', 'Catat hasil stok opname', 'Cari pelanggan untuk transaksi (nama dan nomor tersamar)', 'Lihat laporan keuangan outlet, termasuk ringkasan HPP dan laba', 'Catat, ubah dan hapus pengeluaran', 'Lihat nota dan supplier', 'Kelola supplier, catat nota dan pembayaran', 'Lihat harga pembelian dan nominal nota supplier', 'Lihat profil bersama bisnis dan riwayat belanja outlet yang diizinkan', 'Kelola profil dan catatan pelanggan bersama bisnis', 'Ekspor halaman pelanggan ke CSV', 'Lihat resep dan harga modal katalog bersama brand', 'Kelola bahan dan resep', 'Setujui penyimpanan langsung bahan dan resep']) { await page.getByLabel(label, { exact: true }).check(); await page.getByLabel(label, { exact: true }).uncheck(); }
    await page.getByLabel('Cakupan akses').selectOption('tenant');
    await page.getByLabel('Gunakan AI sesuai izin data akun', { exact: true }).check();
    await page.getByLabel('Gunakan AI sesuai izin data akun', { exact: true }).uncheck();
    await page.getByLabel('Nama jabatan').fill('QA staf updated'); await page.getByRole('button', { name: 'Simpan jabatan' }).click();
    await page.waitForFunction(() => document.querySelector('select')?.textContent.includes('QA staf updated'));
    assert.equal(roles[0].scope, 'tenant'); assert.deepEqual(roles[0].policy.outlet_ids, []);
    console.log('PASS eleven business permission controls and explicit tenant-scope role submission');
    await page.getByLabel('Pilih karyawan').selectOption(eid); await page.getByLabel('Username karyawan').fill('staff'); await page.getByLabel('Jabatan akses').selectOption(roles[0].id); await page.getByRole('button', { name: 'Buat akun karyawan' }).click();
    await page.getByRole('button', { name: 'Simpan akun karyawan' }).waitFor(); await page.getByLabel('Akun boleh masuk').uncheck(); await page.getByLabel('Akun boleh masuk').check(); await page.getByRole('button', { name: 'Simpan akun karyawan' }).click();
    await page.getByRole('button', { name: 'Buat kode aktivasi atau reset password' }).click(); await page.getByLabel('Kode aktivasi', { exact: true }).waitFor(); await layout(page, 'Activation result 320');
    await page.getByRole('button', { name: 'Tutup kode' }).click();
    await page.screenshot({ path: '/tmp/selaris-account-access-light.png', fullPage: true });
    await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await layout(page, 'Access setup 320 dark'); await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    await page.evaluate(() => document.documentElement.style.fontSize = '200%'); await layout(page, 'Access setup 200%'); await page.evaluate(() => document.documentElement.style.fontSize = '');
    await page.goto(`${base}/activate`); await page.getByLabel('Username toko', { exact: true }).fill('qa-shop'); await page.getByLabel('Username akun', { exact: true }).fill('staff'); await page.getByLabel('Kode aktivasi dari pemilik').fill('0'.repeat(64)); await page.getByLabel('Password baru', { exact: true }).fill('qa strong password'); await page.getByLabel('Ulangi password', { exact: true }).fill('qa strong password'); await page.getByRole('button', { name: 'Simpan password' }).click(); await page.getByRole('alert').filter({ hasText: 'Kode tidak sesuai' }).waitFor();
    await page.getByLabel('Kode aktivasi dari pemilik').fill('b'.repeat(64)); await page.getByRole('button', { name: 'Simpan password' }).click(); await page.waitForURL('**/dashboard/hris');
    failLogout = true;
    await page.getByRole('button', { name: 'Keluar', exact: true }).filter({ visible: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Logout belum terkonfirmasi' }).waitFor();
    assert((await context.cookies()).some(cookie => cookie.name === 'token'));
    failLogout = false;
    await page.getByRole('button', { name: 'Keluar', exact: true }).filter({ visible: true }).click();
    await page.waitForURL('**/login');
    assert(!(await context.cookies()).some(cookie => cookie.name === 'token'));
    await page.getByRole('link', { name: 'Lupa password', exact: true }).click(); await page.waitForURL('**/recover');
    await page.getByLabel('Username toko', { exact: true }).fill('qa-shop'); await page.getByLabel('Kode pemulihan', { exact: true }).fill('a'.repeat(64)); await page.getByLabel('Password baru', { exact: true }).fill('qa recovered password'); await page.getByLabel('Ulangi password', { exact: true }).fill('qa recovered password'); await page.getByRole('button', { name: 'Simpan password' }).click();
    await page.getByLabel('Saya sudah menyimpan kode ini').check(); await page.getByRole('button', { name: 'Lanjut ke usaha' }).click(); await page.waitForURL('**/dashboard');
    await context.clearCookies(); await page.goto(`${base}/login/legacy`); await page.getByRole('button', { name: 'Gunakan kode Sefrekuensi' }).click(); await page.getByLabel('Nomor HP', { exact: true }).fill('08111111111'); await page.getByRole('button', { name: 'Kirim kode ke Sefrekuensi' }).click(); await page.getByLabel('Kode verifikasi').fill('123456'); await page.getByRole('button', { name: 'Verifikasi dan lanjut' }).click(); await page.waitForURL('**/dashboard');
    await page.goto(`${base}/dashboard/account`); await page.getByRole('button', { name: 'Keluar semua perangkat' }).click(); await page.waitForURL('**/login');
    await context.addCookies([{ name: 'token', value: 'fixture-owner', domain: '127.0.0.1', path: '/' }, { name: 'tenant_id', value: id, domain: '127.0.0.1', path: '/' }]);
    await page.setViewportSize({ width: 1440, height: 900 }); await page.goto(`${base}/superadmin`);
    failLogout = true; await page.getByRole('button', { name: 'Keluar', exact: true }).click(); await page.getByRole('alert').filter({ hasText: 'Logout belum terkonfirmasi' }).waitFor();
    failLogout = false; await page.getByRole('button', { name: 'Keluar', exact: true }).click(); await page.waitForURL('**/login'); await page.setViewportSize({ width: 320, height: 760 });
    await page.getByLabel('Username toko', { exact: true }).focus(); await page.keyboard.press('Tab'); assert(await page.evaluate(() => document.activeElement.tagName) !== 'BODY');
    assert(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle !== 'none'));
    await page.screenshot({ path: '/tmp/selaris-account-login.png', fullPage: true });
    assert.deepEqual(errors, []);
    console.log('PASS owner migration, role and staff account writes, activation reset and retry errors, logout failure and retry, legacy login, logout all and keyboard');
  } catch (error) { console.error('Fixture calls:', calls.map(c => `${c.method} ${c.path}`)); console.error('Page:', debugPage?.url(), await debugPage?.locator('body').innerText()); await debugPage?.screenshot({ path: '/tmp/selaris-account-browser-failure.png', fullPage: true }); throw error; }
  finally { await browser.close(); await new Promise(resolve => fixture.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
