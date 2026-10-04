const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3105';

async function inspect(page, name) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${name}: horizontal overflow`);
  const samples = await page.evaluate(() => {
    const ctx = document.createElement('canvas').getContext('2d');
    const rgb = color => {
      ctx.fillStyle = color; ctx.fillRect(0, 0, 1, 1);
      return Array.from(ctx.getImageData(0, 0, 1, 1).data);
    };
    return Array.from(document.querySelectorAll('h1,h2,h3,p,a,button,summary,dt,dd,li,figcaption,span')).flatMap(el => {
      if (el.disabled || !el.getClientRects().length || !Array.from(el.childNodes).some(node => node.nodeType === 3 && node.textContent.trim())) return [];
      const style = getComputedStyle(el);
      if (style.visibility === 'hidden') return [];
      const ancestors = []; let node = el;
      while (node) { ancestors.push(node); node = node.parentElement; }
      let bg = [255, 255, 255];
      for (const ancestor of ancestors.reverse()) {
        const color = rgb(getComputedStyle(ancestor).backgroundColor);
        bg = bg.map((value, i) => color[i] * color[3] / 255 + value * (1 - color[3] / 255));
      }
      return [{ text: el.textContent.trim().slice(0, 45), fg: rgb(style.color).slice(0, 3), bg,
        threshold: parseFloat(style.fontSize) >= 24 || parseFloat(style.fontSize) >= 18.67 && Number(style.fontWeight) >= 700 ? 3 : 4.5 }];
    });
  });
  const lum = color => color.map(value => value / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
    .reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
  for (const sample of samples) {
    const values = [lum(sample.fg), lum(sample.bg)].sort((a, b) => b - a);
    const ratio = (values[0] + .05) / (values[1] + .05);
    assert(ratio >= sample.threshold, `${name}: contrast ${sample.text} ${ratio.toFixed(2)}:1`);
  }
  console.log(`PASS ${name}: no overflow; ${samples.length} text contrast pairs meet AA`);
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'], executablePath: process.env.CHROMIUM_EXECUTABLE });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://www.google-analytics.com/**', route => route.abort());
    for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const theme of ['light', 'dark']) {
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.evaluate(theme => {
          localStorage.setItem('selaris-theme', theme);
          document.documentElement.classList.toggle('dark', theme === 'dark');
          window.dispatchEvent(new Event('selaris-theme-change'));
        }, theme);
        await page.evaluate(() => document.fonts.ready);
        await inspect(page, `Home ${width} ${theme}`);
        const copy = await page.locator('main').innerText();
        assert(!copy.includes('Anda hanya memfoto notanya') && !copy.includes('Empat baris di atas'));
        assert(copy.includes('Unggah nota, periksa hasilnya, lalu simpan pembelian.'));
        assert.match(await page.locator('h1').evaluate(el => getComputedStyle(el).fontFamily), /Source[ _]Serif[ _]4/);
        assert.equal(await page.locator('h1').evaluate(el => getComputedStyle(el).fontWeight), '400');
        assert.match(await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily), /Source[ _]Sans[ _]3/);
        for (const image of await page.locator('main img').all()) {
          await image.scrollIntoViewIfNeeded();
          await image.evaluate(el => el.decode());
          assert(await image.evaluate(el => el.naturalWidth > 0));
        }
        for (const href of await page.locator('.public-nav a').evaluateAll(links => links.map(link => link.getAttribute('href')))) {
          if (href.startsWith('/#')) assert.equal(await page.locator(href.slice(1)).count(), 1, `Missing section ${href}`);
        }
        if (width < 1024) {
          await page.getByRole('button', { name: 'Buka menu', exact: true }).click();
          await page.locator('#public-menu').waitFor();
          await page.keyboard.press('Escape');
          assert.equal(await page.getByRole('button', { name: 'Buka menu', exact: true }).getAttribute('aria-expanded'), 'false');
          assert.equal(await page.evaluate(() => document.activeElement.getAttribute('aria-label')), 'Buka menu');
        }
        for (const summary of await page.locator('.faq-section summary').all()) {
          await summary.focus(); await page.keyboard.press('Enter');
          assert(await summary.evaluate(el => el.parentElement.open));
          await page.keyboard.press('Enter');
        }
        if ([320, 1440].includes(width)) {
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.screenshot({ path: `/tmp/selaris-web-after-${width}-${theme}.png`, fullPage: true });
        }
      }
    }
    await page.setViewportSize({ width: 320, height: 760 });
    for (const route of ['/download', '/terms', '/privacy', '/pulsa-agen', '/jelajah']) {
      for (const theme of ['light', 'dark']) {
        await page.evaluate(theme => localStorage.setItem('selaris-theme', theme), theme);
        const response = await page.goto(`${base}${route}`, { waitUntil: 'networkidle' });
        assert.equal(response.status(), 200);
        await inspect(page, `${route} 320 ${theme}`);
      }
    }
    assert.equal(await page.request.get(`${base}/app/web-overview.png`).then(response => response.status()), 200);
    await page.goto(`${base}/download`, { waitUntil: 'networkidle' });
    assert.equal(await page.getByRole('link', { name: 'Unduh APK POS', exact: true }).getAttribute('href'), '/api/download/pos');
    assert.equal(await page.getByRole('link', { name: 'Unduh APK Dapur', exact: true }).getAttribute('href'), '/api/download/dapur');
    assert((await page.locator('main').innerText()).includes('1.6.31'));
    await page.getByRole('link', { name: 'Daftarkan usaha', exact: true }).click();
    await page.waitForURL('**/register');
    await page.goto(base, { waitUntil: 'networkidle' });
    let chats = 0;
    await page.route('**/api/landing-chat', async route => {
      chats++;
      await new Promise(resolve => setTimeout(resolve, 150));
      await route.fulfill({ status: chats === 1 ? 503 : 200, contentType: 'application/json', body: JSON.stringify(chats === 1 ? { error: 'unavailable' } : { reply: 'Paket Pro mendukung resep dan bahan baku.' }) });
    });
    await page.getByRole('button', { name: 'Tanya Selaris', exact: true }).click();
    await page.getByRole('button', { name: 'Apa perbedaan Starter dan Pro?', exact: true }).click();
    await page.getByRole('alert').waitFor();
    await inspect(page, 'Chat error 320');
    await page.getByRole('button', { name: 'Kirim', exact: true }).click();
    await page.getByText('Paket Pro mendukung resep dan bahan baku.', { exact: true }).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#landing-chat').count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Tanya Selaris', exact: true }).getAttribute('aria-expanded'), 'false');
    await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.locator('html').evaluate(el => el.classList.contains('dark')), false);
    await page.setViewportSize({ width: 1440, height: 900 });
    for (const href of ['/#cara-kerja', '/#tampilan', '/#modul', '/#harga', '/jelajah', '/download', '/login']) {
      await page.goto(base, { waitUntil: 'networkidle' });
      await page.locator(`.public-nav a[href="${href}"]`).first().click();
      await page.waitForURL(url => url.pathname + url.hash === href);
    }
    for (const [label, target] of [['Daftar paket Starter', '/register'], ['Daftar paket Pro', '/register?tier=pro']]) {
      await page.goto(base, { waitUntil: 'networkidle' });
      await page.getByRole('link', { name: label, exact: true }).click();
      await page.waitForURL(url => url.pathname + url.search === target);
    }
    assert.deepEqual(errors, []);
    console.log('PASS public click-through: navigation targets, menu/Escape/focus, FAQ keyboard, downloads, register, chat loading/error/retry, persisted theme, real image assets and loaded fonts. No page errors or real chat messages.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
