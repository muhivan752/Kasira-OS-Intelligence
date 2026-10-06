// All writes in this suite go to the localhost fixture, never to the merchant API.
const http = require('node:http'), assert = require('node:assert/strict'), { randomUUID } = require('node:crypto');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3296';
const a = '11111111-1111-4111-8111-111111111111', b = '22222222-2222-4222-8222-222222222222';
let manager = true, linked = false, failRead = false, empty = false, paginated = false, noOutlets = false, failWorkspace = false, choicesPaged = false, failChoices = false, workspace = 'fixture-a';
const writes = new Map(), calls = [], failed = new Set();
let employees = [{ id: a, code: 'KRY-0001', name: 'Fixture karyawan', position: 'Kasir', outlet_id: a, user_id: b, phone: '6281234567890', started_on: '2025-01-01', ended_on: null, is_active: true, notes: 'Catatan fixture', row_version: 1 }], schedules = [], attendance = [];
const fixture = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://fixture'), path = url.pathname.replace(/\/+$/, ''); let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {}; calls.push({ path, method: req.method, body, params: Object.fromEntries(url.searchParams) }); let data = {}, status = 200;
  if (path.endsWith('/users/me')) data = { id: b, full_name: 'Akun fixture', subscription_tier: 'pro', is_superuser: manager };
  else if (path.endsWith('/outlets')) data = [{ id: a, name: 'Outlet fixture', brand_id: a }];
  else if (path.endsWith('/hris/setup')) {
    if (failRead) status = 500;
    data = { is_manager: manager, self_employee: linked ? employees[0] : null, open_attendance: attendance.find(r => r.employee_id === a && r.status === 'hadir' && !r.clock_out) || null, workspace_key: workspace, outlets: noOutlets ? [] : [{ id: a, name: 'Outlet fixture', timezone: 'Asia/Jayapura' }], accounts: manager ? [{ id: b, name: 'Akun fixture' }] : [] };
  } else if (path.endsWith('/hris/workspace')) {
    if (failRead || failWorkspace) status = 500;
    const kind = url.searchParams.get('kind'); let items = empty ? [] : kind === 'employees' ? employees : kind === 'schedules' ? schedules : attendance;
    if (!manager) items = items.filter(r => kind === 'employees' ? r.id === a : r.employee_id === a);
    if (paginated && kind === 'employees') items = Array.from({ length: 51 }, (_, i) => ({ ...employees[0], id: `page-${i}`, name: `Fixture halaman ${i}` }));
    if (url.searchParams.get('search') === 'absent') items = [];
    const total = items.length, skip = Number(url.searchParams.get('skip') || 0);
    data = { items: items.slice(skip, skip + 50), total, skip, limit: 50, timezone: 'Asia/Jayapura', generated_at: '2026-10-06T16:00:00Z', scope: manager ? 'outlet_period' : 'self_outlet_period', summary: { active_employees: employees.length, scheduled: schedules.length, present: attendance.filter(r => r.status === 'hadir').length, leave: attendance.filter(r => r.status !== 'hadir').length, open: attendance.filter(r => r.status === 'hadir' && !r.clock_out).length, unrecorded_started: 0 } };
  } else if (path.endsWith('/hris/employee-choices')) {
    if (failChoices) status = 500;
    let items = choicesPaged ? Array.from({ length: 51 }, (_, i) => ({ id: i === 0 ? a : `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`, name: `Pilihan fixture ${i}`, code: `KRY-${i}` })) : employees.map(r => ({ id: r.id, name: r.name, code: r.code }));
    if (url.searchParams.get('search') === 'absent') items = []; const skip = Number(url.searchParams.get('skip') || 0); data = { items: items.slice(skip, skip + 50), total: items.length };
  }
  else if (path.includes('/hris/') && ['POST', 'PUT'].includes(req.method)) {
    const action = path.split('/hris/')[1].split('/')[0], isVoid = path.endsWith('/void');
    if (writes.has(body.client_request_id)) data = writes.get(body.client_request_id);
    else {
      const id = req.method === 'PUT' || isVoid ? path.split('/')[isVoid ? path.split('/').length - 2 : path.split('/').length - 1] : randomUUID();
      data = { id, row_version: (body.row_version || 0) + 1 }; writes.set(body.client_request_id, data);
      const collection = action === 'employees' ? employees : action === 'schedules' ? schedules : attendance;
      if (action === 'punch') {
        if (body.action === 'in') attendance.push({ ...data, employee_id: a, employee_name: employees[0].name, outlet_id: a, work_date: '2026-10-07', status: 'hadir', clock_in: '2026-10-06T16:00:00Z', clock_out: null, source: 'self', minutes: null });
        else { const open = attendance.find(r => r.employee_id === a && r.status === 'hadir' && !r.clock_out); open.clock_out = '2026-10-07T00:00:00Z'; open.minutes = 480; }
      } else if (isVoid) { collection.splice(collection.findIndex(r => r.id === id), 1); }
      else {
        const record = { ...body, ...data, employee_name: employees.find(r => r.id === body.employee_id)?.name, code: 'KRY-0002', work_date: body.work_date || '2026-10-06', source: 'manual', minutes: body.clock_in && body.clock_out ? 480 : null };
        if (req.method === 'PUT') Object.assign(collection.find(r => r.id === id), record); else collection.push(record);
      }
    }
    const failureKey = `${action}:${req.method}:${isVoid ? 'void' : body.action || 'save'}`;
    if (!failed.has(failureKey)) { failed.add(failureKey); status = 500; }
  }
  res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(status >= 400 ? { detail: 'SERVER INTERNAL SECRET' } : { success: true, data, message: 'Data fixture disimpan' }));
});

async function appearance(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${label} overflow`);
  const roots = page.locator('.hris-workspace,.inventory-dialog[open]');
  for (let i = 0; i < await roots.count(); i++) {
    const issues = await roots.nth(i).evaluate(root => {
      const rgb = v => v.match(/[\d.]+/g).slice(0, 3).map(Number), lum = v => rgb(v).map(x => x / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4).reduce((s, x, i) => s + x * [.2126, .7152, .0722][i], 0), issues = [];
      for (const el of root.querySelectorAll('*')) {
        const style = getComputedStyle(el), box = el.getBoundingClientRect();
        if (!box.width || !box.height || style.visibility === 'hidden' || el.tagName === 'OPTION' || el.closest(':disabled')) continue;
        if (['BUTTON', 'SELECT', 'A', 'INPUT'].includes(el.tagName) && el.type !== 'hidden' && (box.width < 43 || box.height < 43)) issues.push(`target ${el.textContent} ${box.width}x${box.height}`);
        if (['INPUT','SELECT','TEXTAREA'].includes(el.tagName) && style.borderTopStyle === 'solid') { const x = lum(style.borderTopColor), y = lum(style.backgroundColor); if ((Math.max(x,y)+.05)/(Math.min(x,y)+.05) < 3) issues.push(`control boundary ${el.getAttribute('name')}`); }
        if (!Array.from(el.childNodes).some(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())) continue;
        let bg = el; while (bg.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(bg).backgroundColor)) bg = bg.parentElement;
        const x = lum(style.color), y = lum(getComputedStyle(bg).backgroundColor), ratio = (Math.max(x, y) + .05) / (Math.min(x, y) + .05);
        if (ratio < 4.5) issues.push(`contrast ${el.textContent.trim().slice(0, 35)} ${ratio}`);
      } return issues;
    }); assert.deepEqual(issues, [], label);
  }
}

(async () => {
  await new Promise(resolve => fixture.listen(8396, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] }); let page;
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, timezoneId: 'America/Los_Angeles' });
    await context.addCookies(Object.entries({ token: 'fixture-token', tenant_id: a, outlet_id: a }).map(([name, value]) => ({ name, value, url: base })));
    page = await context.newPage(); const errors = []; page.on('pageerror', e => errors.push(e.message));
    const ready = () => page.locator('.hr-summary').waitFor(), modal = () => page.getByRole('dialog');
    const closeWait = () => modal().waitFor({ state: 'hidden' });
    const saveUncertain = async () => { await modal().getByRole('button', { name: 'Simpan', exact: true }).click(); await modal().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).waitFor(); assert(!await page.locator('body').innerText().then(t => t.includes('SERVER INTERNAL SECRET'))); await modal().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).click(); await closeWait(); await ready(); };
    await page.goto(`${base}/dashboard/hris`, { waitUntil: 'domcontentloaded', timeout: 60000 }); await ready();
    if (process.env.HRIS_CHOICES_ONLY) {
      choicesPaged = true; await page.getByRole('button', { name: 'Jadwal', exact: true }).click(); await ready(); await page.getByRole('button', { name: 'Atur jadwal', exact: true }).click();
      await page.getByLabel('Karyawan', { exact: true }).selectOption(a); await page.getByRole('button', { name: 'Pilihan berikutnya', exact: true }).click(); await page.getByRole('option', { name: 'Pilihan fixture 50 · KRY-50', exact: true }).waitFor({ state: 'attached' }); assert.equal(await page.getByLabel('Karyawan', { exact: true }).inputValue(), '');
      await page.getByRole('button', { name: 'Pilihan sebelumnya', exact: true }).click(); await page.getByRole('option', { name: 'Pilihan fixture 0 · KRY-0', exact: true }).waitFor({ state: 'attached' });
      await page.getByLabel('Cari karyawan aktif').fill('absent'); await page.getByText(/Belum ada karyawan aktif sesuai pencarian/).waitFor();
      failChoices = true; await page.getByLabel('Cari karyawan aktif').fill('retry'); await modal().getByRole('button', { name: 'Coba lagi', exact: true }).waitFor(); failChoices = false; await modal().getByRole('button', { name: 'Coba lagi', exact: true }).click(); await page.getByLabel('Karyawan', { exact: true }).waitFor();
      await page.keyboard.press('Escape'); await closeWait(); assert.equal(calls.filter(c => ['POST','PUT'].includes(c.method) && c.path.includes('/hris/')).length, 0); assert.deepEqual(errors, []);
      console.log('PASS employee chooser search, page forward/back, selection reset, empty/read error/retry and Escape; no writes'); return;
    }
    await page.getByLabel('Cari nama / kode').fill('absent'); await page.getByRole('heading', { name: 'Belum ada karyawan sesuai pilihan' }).waitFor();
    await page.getByRole('button', { name: 'Reset filter' }).click(); await page.getByRole('heading', { name: 'Fixture karyawan', exact: true }).waitFor();
    await page.getByLabel('Status karyawan').selectOption('active'); await ready(); await page.getByLabel('Dari tanggal').fill('2026-10-06'); await page.getByLabel('Sampai tanggal').fill('2026-10-12'); await ready();
    paginated = true; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await ready();
    await page.getByRole('button', { name: 'Berikutnya', exact: true }).click(); await page.getByRole('heading', { name: 'Fixture halaman 50' }).waitFor();
    await page.getByRole('button', { name: 'Sebelumnya', exact: true }).click(); await page.getByRole('heading', { name: 'Fixture halaman 0' }).waitFor();
    paginated = false; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await ready();
    await page.getByRole('button', { name: 'Tambah karyawan', exact: true }).click(); await page.getByLabel('Nama karyawan').fill('Karyawan baru fixture'); await page.getByLabel('Jabatan / tugas').fill('Barista'); await page.getByLabel('Outlet penempatan').selectOption(a); await page.getByLabel('Hubungkan akun kasir').selectOption(''); await page.getByLabel('Nomor HP').fill('081234567890'); await page.getByLabel('Tanggal mulai kerja').fill('2025-01-01'); await page.getByLabel('Tanggal selesai kerja').fill('2027-01-01'); await page.getByLabel('Tanggal selesai kerja').fill(''); await modal().getByLabel('Status karyawan').selectOption('false'); await modal().getByLabel('Status karyawan').selectOption('true'); await page.getByLabel('Catatan pengelola').fill('Catatan fixture baru');
    await modal().getByRole('button', { name: 'Simpan', exact: true }).click(); await modal().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).waitFor(); assert(await page.getByLabel('Nama karyawan').isDisabled());
    await page.keyboard.press('Escape'); await closeWait(); await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }); await ready();
    await page.getByRole('button', { name: 'Periksa penyimpanan', exact: true }).click(); await page.getByText(/Penyimpanan belum selesai:/).waitFor({ state: 'hidden' }); await ready(); await page.getByRole('heading', { name: 'Karyawan baru fixture' }).waitFor(); assert.equal(employees.length, 2);
    const createCalls = calls.filter(c => c.path.endsWith('/hris/employees') && c.method === 'POST'); assert.deepEqual(createCalls[0].body, createCalls[1].body);
    await page.getByRole('button', { name: 'Edit karyawan Fixture karyawan' }).click(); await page.getByLabel('Jabatan / tugas').fill('Senior kasir'); await saveUncertain();
    await page.getByRole('button', { name: 'Jadwal', exact: true }).click(); await ready(); await page.getByRole('button', { name: 'Atur jadwal', exact: true }).click();
    await page.getByLabel('Karyawan', { exact: true }).selectOption(a); await page.getByLabel('Mulai kerja').fill('2026-10-06T23:00'); await page.getByLabel('Selesai kerja').fill('2026-10-07T07:00'); await saveUncertain();
    const scheduleBody = calls.find(c => c.path.endsWith('/hris/schedules') && c.method === 'POST').body;
    assert.equal(scheduleBody.starts_at, '2026-10-06T14:00:00.000Z'); assert.equal(scheduleBody.ends_at, '2026-10-06T22:00:00.000Z');
    await page.getByRole('button', { name: 'Edit Jadwal Fixture karyawan' }).click(); await page.getByLabel('Catatan jadwal').fill('Catatan jadwal diperbarui'); await saveUncertain();
    await page.getByRole('button', { name: 'Absensi & izin', exact: true }).click(); await ready(); await page.getByRole('button', { name: 'Catat kehadiran', exact: true }).click();
    await page.getByLabel('Karyawan', { exact: true }).selectOption(a); await page.getByLabel('Tanggal kerja').fill('2026-10-06'); await page.getByLabel('Status kehadiran').selectOption('izin'); await page.getByLabel('Alasan', { exact: true }).fill('Dikonfirmasi fixture'); await saveUncertain();
    await page.getByRole('button', { name: 'Edit Absensi & izin Fixture karyawan' }).click(); await page.getByLabel('Status kehadiran').selectOption('hadir'); await page.getByLabel('Jam masuk').fill('2026-10-06T08:00'); await page.getByLabel('Jam pulang').fill('2026-10-06T16:00'); await page.getByLabel('Alasan koreksi').fill('Koreksi fixture'); await saveUncertain();
    assert.match(await page.locator('.hr-list').innerText(), /8 jam 0 menit/);
    await page.getByRole('button', { name: 'Batalkan', exact: true }).click(); await page.getByLabel('Alasan pembatalan').fill('Salah karyawan fixture'); await saveUncertain(); assert.equal(attendance.length, 0);
    await page.getByRole('button', { name: 'Jadwal', exact: true }).click(); await ready(); await page.getByRole('button', { name: 'Batalkan', exact: true }).click(); await page.getByLabel('Alasan pembatalan').fill('Jadwal dibatalkan fixture'); await saveUncertain(); assert.equal(schedules.length, 0);
    console.log('PASS roster/search/pagination, create recovery after reload, profile edit, overnight WIT conversion, attendance correction and cancellation with same-UUID retry');
    await page.getByRole('button', { name: 'Karyawan', exact: true }).click(); await ready();
    for (const theme of ['light', 'dark']) for (const width of [320, 375, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 }); await page.evaluate(t => document.documentElement.classList.toggle('dark', t === 'dark'), theme); await appearance(page, `${theme} ${width}`);
      for (const kind of ['employees', 'schedules', 'attendance']) {
        await page.getByRole('button', { name: { employees: 'Karyawan', schedules: 'Jadwal', attendance: 'Absensi & izin' }[kind], exact: true }).click(); await ready();
        await page.getByRole('button', { name: { employees: 'Tambah karyawan', schedules: 'Atur jadwal', attendance: 'Catat kehadiran' }[kind], exact: true }).click(); await modal().waitFor();
        if (kind !== 'employees') await page.getByLabel('Karyawan', { exact: true }).waitFor(); await appearance(page, `${theme} ${width} ${kind}`);
        await page.evaluate(() => document.documentElement.style.fontSize = '200%'); await appearance(page, `${theme} ${width} ${kind} 200%`);
        await page.keyboard.press('Escape'); await closeWait(); await appearance(page, `${theme} ${width} page 200%`); await page.evaluate(() => document.documentElement.style.fontSize = '');
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 }); await page.getByRole('button', { name: 'Karyawan', exact: true }).click(); await ready();
    await page.evaluate(() => document.documentElement.classList.remove('dark')); await page.screenshot({ path: '/tmp/selaris-hris-light.png', fullPage: true }); await page.evaluate(() => document.documentElement.classList.add('dark')); await page.screenshot({ path: '/tmp/selaris-hris-dark.png', fullPage: true });
    await page.getByRole('button', { name: 'Tambah karyawan', exact: true }).click(); await page.getByLabel('Nama karyawan').focus(); await page.keyboard.press('Shift+Tab'); assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Tutup'); await page.keyboard.press('Escape'); await closeWait(); assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Tambah karyawan');
    console.log('PASS five viewport sizes, two themes, 200% text for all forms, AA contrast, 44px controls, keyboard/focus/Escape');
    failRead = true; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await page.locator('.hris-workspace [role="alert"]').waitFor(); assert.equal(await page.locator('.hr-summary').count(), 0);
    failRead = false; await page.getByRole('button', { name: 'Coba lagi', exact: true }).click(); await ready();
    failWorkspace = true; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await page.locator('.hris-workspace [role="alert"]').waitFor(); assert.equal(await page.locator('.hr-summary').count(), 0); failWorkspace = false; await page.getByRole('button', { name: 'Coba lagi', exact: true }).click(); await ready();
    noOutlets = true; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await page.getByRole('heading', { name: 'Belum ada outlet aktif' }).waitFor(); assert.equal(await page.getByRole('link', { name: 'Buka pengaturan', exact: true }).getAttribute('href'), '/dashboard/settings'); assert.equal(await page.locator('.hr-summary').count(), 0); assert(!await page.locator('.hris-workspace').innerText().then(t => t.includes('Memuat tim'))); noOutlets = false; await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }); await ready();
    console.log('PASS workspace read error and no active outlet show explicit states, correct settings link, and no stale summary');
    empty = true; await page.getByRole('button', { name: 'Muat ulang', exact: true }).click(); await page.getByRole('heading', { name: 'Belum ada karyawan sesuai pilihan' }).waitFor(); empty = false;
    linked = true; manager = false; await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }); await ready(); assert.equal(await page.getByRole('button', { name: 'Tambah karyawan', exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Catat masuk sekarang', exact: true }).click(); await saveUncertain(); assert.equal(attendance.length, 1); await page.getByRole('button', { name: 'Catat pulang sekarang', exact: true }).click(); await saveUncertain(); assert(attendance[0].clock_out);
    await page.getByRole('button', { name: 'Absensi & izin', exact: true }).click(); await ready(); await appearance(page, 'self attendance'); assert.equal(await page.getByRole('button', { name: 'Koreksi', exact: true }).count(), 0);
    linked = false; await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }); await ready(); assert.match(await page.locator('.hris-workspace').innerText(), /Akun ini belum terhubung/);
    manager = true; await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }); await ready(); await page.getByRole('button', { name: 'Karyawan', exact: true }).click(); await ready();
    let abortWrite = true; await page.route('**/dashboard/hris', route => { if (abortWrite && route.request().method() === 'POST' && (route.request().postData() || '').includes('Transport fixture')) { abortWrite = false; return route.abort('failed'); } return route.continue(); });
    await page.getByRole('button', { name: 'Tambah karyawan', exact: true }).click(); await page.getByLabel('Nama karyawan').fill('Transport fixture'); await page.getByLabel('Jabatan / tugas').fill('Kasir'); await modal().getByRole('button', { name: 'Simpan', exact: true }).click(); await modal().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).waitFor(); assert.equal(abortWrite, false); await modal().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).click(); await closeWait(); await ready(); await page.unroute('**/dashboard/hris');
    console.log('PASS browser-to-server transport interruption releases busy state and keeps the identical request retryable');
    failed.delete('employees:POST:save'); await page.getByRole('button', { name: 'Tambah karyawan', exact: true }).click(); await page.getByLabel('Nama karyawan').fill('Private draft fixture'); await page.getByLabel('Jabatan / tugas').fill('Kasir'); await modal().getByRole('button', { name: 'Simpan', exact: true }).click(); await modal().getByRole('button', { name: 'Periksa penyimpanan', exact: true }).waitFor(); await page.keyboard.press('Escape'); await closeWait();
    workspace = 'fixture-b'; const writesBeforeSwitch = writes.size; await page.getByRole('button', { name: 'Periksa penyimpanan', exact: true }).click(); await page.getByText('Akun atau bisnis sudah berubah. Muat ulang sebelum menyimpan.').waitFor(); assert.equal(writes.size, writesBeforeSwitch); assert.equal(await page.getByRole('button', { name: 'Periksa penyimpanan', exact: true }).count(), 1); await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }); await ready(); assert.equal(await page.getByRole('button', { name: 'Periksa penyimpanan', exact: true }).count(), 0); assert.equal(errors.length, 0, errors);
    console.log('PASS explicit error/retry/empty, self punch and restricted controls, unlinked account guidance, pending request isolated per business/user; no page errors');
  } catch (error) { if (page) await page.screenshot({ path: '/tmp/selaris-hris-failure.png', fullPage: true }); throw error; }
  finally { await browser.close(); fixture.close(); }
})();
