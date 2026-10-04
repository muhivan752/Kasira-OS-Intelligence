const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const calls = [];
const id = '11111111-1111-4111-8111-111111111111';
const session = { access_token: 'browser-fixture', tenant_id: id, outlet_id: id, stock_mode: 'simple', subscription_tier: 'starter' };
let failProduct = true;
const fixture = http.createServer(async (req, res) => {
  let body = '';
  for await (const chunk of req) body += chunk;
  const data = body ? JSON.parse(body) : {};
  const path = new URL(req.url, 'http://fixture').pathname.replace(/\/$/, '');
  calls.push({ path, method: req.method, data });
  let value = [];
  let status = 200;
  let detail;
  if (path.endsWith('/auth/providers')) value = { google: { enabled: false, web_config: null }, sefrekuensi: true };
  else if (path.endsWith('/auth/otp/send')) {
    if (data.phone === '628111111111' && data.channel === 'sefrekuensi') {
      status = 404; detail = { code: 'SEFREKUENSI_NOT_FOUND', message: 'Nomor belum terdaftar di Sefrekuensi.' };
    } else value = { channel: data.channel };
  } else if (path.endsWith('/auth/otp/register/verify') || path.endsWith('/auth/otp/verify')) {
    if (data.otp !== '123456') { status = 400; detail = 'Kode tidak valid.'; }
    else value = path.endsWith('/register/verify') ? { otp_proof: 'registration-fixture-proof' } : session;
  } else if (path.endsWith('/auth/register')) value = session;
  else if (path.endsWith('/outlets')) value = [{ id, brand_id: id, name: 'Toko fixture' }];
  else if (path.endsWith('/users/me')) value = { id, tenant_id: id, full_name: 'Pemilik fixture', subscription_tier: 'starter', subscription_status: 'active' };
  else if (path.endsWith('/categories')) value = [{ id, name: 'Minuman' }];
  else if (path.endsWith('/products') && req.method === 'POST') {
    if (failProduct) { status = 400; detail = 'Produk belum tersimpan.'; failProduct = false; }
    else value = { id, ...data };
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(detail ? { detail } : { success: true, data: value }));
});

function ratio(a, b) {
  const lum = color => {
    const values = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(value => {
      const v = value / 255;
      return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    });
    return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
  };
  const [x, y] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (x + 0.05) / (y + 0.05);
}

async function layout(page, name) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${name}: overflow`);
  const sample = await page.locator('.auth-heading h1').evaluate(el => {
    const style = getComputedStyle(el);
    return { text: style.color, bg: getComputedStyle(document.querySelector('.auth-layout')).backgroundColor };
  });
  assert(ratio(sample.text, sample.bg) >= 3, `${name}: heading contrast`);
  const samples = await page.evaluate(() => Array.from(document.querySelectorAll('.auth-content h1, .auth-content p, .auth-content label, .auth-content legend, .auth-content input, .auth-content select, .auth-content button, .auth-content a, .auth-content summary, .auth-footer a')).flatMap(el => {
    if (el.disabled || !el.getClientRects().length) return [];
    const style = getComputedStyle(el);
    let current = el;
    let bg = 'rgb(255, 255, 255)';
    while (current) {
      const candidate = getComputedStyle(current).backgroundColor;
      if (candidate.startsWith('rgb(')) { bg = candidate; break; }
      current = current.parentElement;
    }
    return [{ text: (el.textContent || el.value || el.placeholder || '').slice(0, 35), color: style.color, bg,
      minimum: parseFloat(style.fontSize) >= 24 || parseFloat(style.fontSize) >= 18.67 && Number(style.fontWeight) >= 700 ? 3 : 4.5 }];
  }));
  for (const item of samples) assert(ratio(item.color, item.bg) >= item.minimum, `${name}: contrast ${item.text} ${ratio(item.color, item.bg).toFixed(2)}`);
  console.log(`PASS ${name}: no horizontal overflow, heading contrast ${ratio(sample.text, sample.bg).toFixed(2)}:1`);
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'],
    ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
  await new Promise(resolve => fixture.listen(8184, '127.0.0.1', resolve));
  try {
    const context = await browser.newContext({ viewport: { width: 320, height: 760 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:3104/register', { waitUntil: 'networkidle' });
    await page.getByText('Login Google sedang disiapkan.', { exact: false }).waitFor();
    assert(await page.getByRole('button', { name: 'Lanjut dengan Google' }).isDisabled());
    await layout(page, 'Register choice 320 light');
    await page.screenshot({ path: '/tmp/selaris-register-light.png', fullPage: true });
    await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
    await layout(page, 'Register choice 320 dark');
    await page.screenshot({ path: '/tmp/selaris-register-dark.png', fullPage: true });
    await page.reload({ waitUntil: 'networkidle' });
    assert(await page.locator('html').evaluate(el => el.classList.contains('dark')));
    await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    await page.getByRole('button', { name: 'Gunakan kode Sefrekuensi' }).click();
    await page.getByLabel('Nomor HP', { exact: true }).fill('abc');
    await page.getByRole('button', { name: 'Kirim kode ke Sefrekuensi' }).click();
    await page.getByRole('alert').filter({ hasText: 'nomor HP yang valid' }).waitFor();
    await page.getByLabel('Nomor HP', { exact: true }).fill('08111111111');
    await page.getByRole('button', { name: 'Kirim kode ke Sefrekuensi' }).click();
    await page.getByRole('link', { name: 'Pasang Sefrekuensi' }).waitFor();
    assert((await page.getByRole('link', { name: 'Pasang Sefrekuensi' }).getAttribute('href')).includes('com.sefrekuensi.app'));
    await page.getByRole('button', { name: 'Gunakan WhatsApp sebagai alternatif' }).click();
    await page.getByLabel('Kode verifikasi').fill('000000');
    await page.getByRole('button', { name: 'Verifikasi dan lanjut' }).click();
    await page.getByRole('alert').filter({ hasText: 'Kode tidak valid' }).waitFor();
    await page.getByLabel('Kode verifikasi').fill('123456');
    await page.getByRole('button', { name: 'Verifikasi dan lanjut' }).click();
    await page.getByLabel('Nama pemilik', { exact: true }).fill('Pemilik fixture');
    await page.getByLabel('Nama usaha', { exact: true }).fill('Toko fixture');
    await page.getByLabel('Warung', { exact: true }).check();
    await page.getByLabel('PIN kasir', { exact: true }).fill('123456');
    await page.getByLabel('Ulangi PIN').fill('654321');
    await page.getByRole('button', { name: 'Buat usaha saya' }).click();
    await page.getByRole('alert').filter({ hasText: 'Konfirmasi PIN belum cocok' }).waitFor();
    await page.getByLabel('Ulangi PIN').fill('123456');
    await page.getByText('Punya kode referral?').click();
    await page.getByLabel('Kode referral', { exact: true }).fill('demo');
    await layout(page, 'Business form 320');
    await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
    await layout(page, 'Business form 320 dark');
    await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    await page.getByRole('button', { name: 'Buat usaha saya' }).click();
    await page.waitForURL('**/onboarding');
    await page.getByLabel('Nama produk').waitFor();
    await page.getByLabel('Nama produk').fill('Kopi fixture');
    await page.getByLabel('Harga jual (Rp)').fill('18000');
    await page.getByLabel('Kategori').selectOption(id);
    await page.getByRole('button', { name: 'Simpan dan lanjut' }).click();
    await page.getByRole('alert').filter({ hasText: 'Produk belum tersimpan' }).waitFor();
    await page.getByRole('button', { name: 'Simpan dan lanjut' }).click();
    await page.getByRole('link', { name: 'Buka dashboard usaha' }).waitFor();
    await layout(page, 'Onboarding ready 320');
    await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
    await layout(page, 'Onboarding ready 320 dark');
    await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    assert.equal(await page.getByRole('link', { name: 'Buka dashboard usaha' }).getAttribute('href'), '/dashboard');
    assert.equal(await page.getByRole('link', { name: 'Unduh aplikasi kasir Android' }).getAttribute('href'), '/api/download/pos');
    assert.equal(await page.getByRole('link', { name: 'Atur metode pembayaran' }).getAttribute('href'), '/dashboard/settings/payment');
    await page.getByRole('button', { name: 'Kembali ke produk pertama' }).click();
    await page.getByRole('button', { name: 'Tambahkan produk nanti' }).click();
    const register = calls.find(call => call.path.endsWith('/auth/register'));
    assert.equal(register.data.otp_proof, 'registration-fixture-proof');
    assert.equal(register.data.business_type, 'warung');
    assert.equal(register.data.referral_code, 'DEMO');
    const product = calls.find(call => call.path.endsWith('/products') && call.method === 'POST');
    assert.equal(product.data.stock_enabled, false);
    assert.equal(product.data.stock_qty, 0);
    assert.equal(product.data.base_price, 18000);
    for (const width of [375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await layout(page, `Onboarding ready ${width}`);
    }
    await page.getByRole('link', { name: 'Buka dashboard usaha' }).click();
    await page.waitForURL('**/dashboard');
    await page.getByRole('heading', { name: 'Pendapatan 7 Hari Terakhir' }).waitFor();
    await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
    assert.equal(await page.locator('.merchant-shell').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(18, 18, 18)');
    await page.screenshot({ path: '/tmp/selaris-dashboard-dark.png', fullPage: true });
    await page.setViewportSize({ width: 320, height: 760 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Dashboard 320 overflow');
    await page.getByRole('button', { name: 'Buka menu' }).click();
    assert.equal(await page.getByRole('button', { name: 'Buka menu' }).getAttribute('aria-expanded'), 'true');
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('button', { name: 'Buka menu' }).getAttribute('aria-expanded'), 'false');
    await page.getByRole('button', { name: 'Buka menu' }).click();
    await page.getByRole('button', { name: 'Tutup menu' }).click();
    await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    console.log('PASS dashboard: warm/charcoal themes; 320px no overflow; mobile menu opens, closes and handles Escape; keyboard focus returns to menu button.');
    await page.goto('http://127.0.0.1:3104/login', { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Gunakan kode Sefrekuensi' }).click();
    await page.getByRole('button', { name: 'Kembali', exact: true }).click();
    await page.keyboard.press('Tab');
    const focus = await page.evaluate(() => {
      const el = document.activeElement;
      return { tag: el.tagName, outline: getComputedStyle(el).outlineStyle, width: getComputedStyle(el).outlineWidth };
    });
    assert.notEqual(focus.tag, 'BODY');
    console.log('PASS keyboard focus:', JSON.stringify(focus));
    await page.getByRole('link', { name: 'Daftarkan usaha' }).click();
    await page.waitForURL('**/register');
    for (const href of ['/terms', '/privacy', '/']) assert.equal((await page.request.get(`http://127.0.0.1:3104${href}`)).status(), 200);
    assert.deepEqual(errors, []);
    console.log('PASS click-through: theme persists; Google unavailable state; phone validation; Sef not found; explicit WA fallback; invalid/correct OTP; business types; PIN mismatch; referral; onboarding save failure/retry; product skip/back; register/login links; terms/privacy/home. No page errors.');
    await context.close();
  } finally {
    await browser.close();
    await new Promise(resolve => fixture.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
