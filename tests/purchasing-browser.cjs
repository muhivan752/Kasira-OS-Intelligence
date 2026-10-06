// Synthetic HTTP fixtures only. No merchant writes or external OCR provider calls.
const http = require('node:http'), assert = require('node:assert/strict'), fs = require('node:fs/promises');
const { chromium } = require('playwright');
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:3195';
const a = '11111111-1111-4111-8111-111111111111', b = '22222222-2222-4222-8222-222222222222';
const supplier = {id:a,name:'Supplier fixture',is_active:true,row_version:0,payment_terms_days:7,purchase_count:1,purchase_total:'100.25',outstanding_total:'80.25'};
let suppliers=[supplier], failRead=false, uncertainReceipt=true, uncertainPay=true, paginated=false, empty=false;
const calls=[], receipts=new Map(), pays=new Map();
let purchases=[{id:a,outlet_id:b,po_number:'NB-FIXTURE-001',supplier_name:supplier.name,supplier_id:a,status:'received',
  total_amount:'100.25',paid_amount:'20.00',outstanding_amount:'80.25',received_at:'2026-09-30T18:00:00Z',due_at:'2026-10-01T16:59:59Z',row_version:0,
  items:[{id:a,ingredient_id:a,name:'Gula fixture',quantity:2,unit:'kg',base_unit:'gram',qty_base:2000,unit_price:'50.125',total_price:'100.25',cost_before:'0.01',cost_after:'0.01333333'}],payments:[{id:'p0',amount:'20.00',kind:'initial',paid_at:'2026-09-30T18:00:00Z'}]}];
const fixture=http.createServer(async(req,res)=>{
  const url=new URL(req.url,'http://fixture'), path=url.pathname.replace(/\/+$/,''); let raw=''; for await(const chunk of req) raw+=chunk;
  const body=raw && req.headers['content-type']?.includes('application/json') ? JSON.parse(raw) : {};
  calls.push({path,method:req.method,params:Object.fromEntries(url.searchParams),body}); let data={}, status=200;
  if (path.endsWith('/auth/access')) data = { enforcement_mode: 'owner', permissions: [], scope: 'tenant', outlets: [], access_version: 'owner-fixture' };
  else if(path.endsWith('/users/me')) data={id:a,subscription_tier:'pro'};
  else if(path.endsWith('/outlets')) data=[{id:a,brand_id:a,name:'Outlet A fixture'},{id:b,brand_id:b,name:'Outlet B fixture'}];
  else if(path.endsWith('/products')) data=[{id:a,name:'Produk fixture',stock_enabled:true}];
  else if(path.endsWith('/ingredients')) data=[{id:a,name:'Gula fixture',base_unit:'gram',ingredient_type:'recipe'}];
  else if(path.endsWith('/purchases/summary')) { if(failRead) status=500;
    data={month:url.searchParams.get('month'),month_total:'100.25',month_count:1,outstanding_total:'80.25',outstanding_count:1,overdue_total:'80.25',overdue_count:1,next_due_at:'2026-10-01T16:59:59Z',next_due_supplier:supplier.name,generated_at:new Date().toISOString()}; }
  else if(path.endsWith('/suppliers') && req.method==='GET') data=suppliers;
  else if(path.endsWith('/suppliers') && req.method==='POST') { data={...supplier,...body,id:b}; suppliers.push(data); }
  else if(path.includes('/suppliers/') && req.method==='PUT') { const old=suppliers.find(s=>s.id===path.split('/').pop()); data={...old,...body,row_version:old.row_version+1};suppliers=suppliers.map(s=>s.id===old.id?data:s); }
  else if(path.includes('/suppliers/') && req.method==='DELETE') { suppliers=suppliers.filter(s=>s.id!==path.split('/').pop());data={ok:true}; }
  else if(path.endsWith('/purchases') && req.method==='GET') {
    data=empty?[]:purchases;
    if(paginated) data=Array.from({length:51},(_,i)=>({...purchases[0],id:`page-${i}`,po_number:`NB-PAGE-${i}`})).slice(Number(url.searchParams.get('skip')||0),Number(url.searchParams.get('skip')||0)+51);
  } else if(path.endsWith('/purchases') && req.method==='POST') {
    if(receipts.has(body.client_request_id)) data=receipts.get(body.client_request_id);
    else { const total=body.items.reduce((sum,i)=>sum+Number(i.total_price),0),paid=body.paid_amount==null?total:Number(body.paid_amount);
      data={...body,id:b,po_number:'NB-FIXTURE-002',total_amount:total.toFixed(2),paid_amount:paid.toFixed(2),outstanding_amount:(total-paid).toFixed(2),row_version:0,status:'received',items:body.items.map((i,n)=>({...i,id:`item-${n}`,name:i.name||'Produk fixture'})),payments:[]}; receipts.set(body.client_request_id,data);purchases.push(data); }
    if(uncertainReceipt){uncertainReceipt=false;status=500;}
  } else if(path.endsWith('/pay')) {
    if(pays.has(body.client_request_id)) data=pays.get(body.client_request_id);
    else { const old=purchases.find(p=>p.id===path.split('/').at(-2)), paid=Number(old.paid_amount)+Number(body.amount);
      data={...old,paid_amount:paid.toFixed(2),outstanding_amount:(Number(old.total_amount)-paid).toFixed(2),row_version:old.row_version+1,payments:[...old.payments,{id:body.client_request_id,kind:'installment',amount:body.amount,paid_at:new Date().toISOString()}]};pays.set(body.client_request_id,data);purchases=purchases.map(p=>p.id===old.id?data:p); }
    if(uncertainPay){uncertainPay=false;status=500;}
  } else if(path.includes('/purchases/')) data=purchases.find(p=>p.id===path.split('/').pop());
  else if(path.endsWith('/invoice-ocr/scan')) data={supplier_name:supplier.name,grand_total:42.75,items:[{name:'Onbekend fixture',quantity:1,unit:'pcs',unit_price:42.75,total_price:42.75}]};
  else if(path.endsWith('/media/upload')) {res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({url:'http://fixture.invalid/photo.jpg'}));return;}
  res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(status>=400?{detail:'SERVER INTERNAL SECRET'}:{success:true,data,message:'Fixture opgeslagen'}));
});
async function appearance(page,label){
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${label} overflow`);
  const issues=await page.locator('.purchase-workspace').evaluate(root=>{
    const rgb=v=>v.match(/[\d.]+/g).slice(0,3).map(Number), lum=v=>rgb(v).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0), issues=[];
    for(const el of root.querySelectorAll('*')){const style=getComputedStyle(el),box=el.getBoundingClientRect();
      if(!box.width||!box.height||style.visibility==='hidden'||el.tagName==='OPTION'||el.closest(':disabled'))continue;
      if(['BUTTON','SELECT','A','INPUT'].includes(el.tagName)&&el.type!=='checkbox'&&(box.width<43||box.height<43))issues.push(`target ${el.textContent} ${box.width}x${box.height}`);
      if(!Array.from(el.childNodes).some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim()))continue;
      let bg=el;while(bg.parentElement&&['rgba(0, 0, 0, 0)','transparent'].includes(getComputedStyle(bg).backgroundColor))bg=bg.parentElement;
      const x=lum(style.color),y=lum(getComputedStyle(bg).backgroundColor),ratio=(Math.max(x,y)+.05)/(Math.min(x,y)+.05);
      if(ratio<4.5)issues.push(`contrast ${el.textContent.trim().slice(0,35)} ${ratio}`);
    }return issues;
  });assert.deepEqual(issues,[],label);
}
(async()=>{
  await new Promise(resolve=>fixture.listen(Number(process.env.FIXTURE_PORT || 8295),'127.0.0.1',resolve));
  const browser=await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE, headless:true,args:['--no-sandbox']});let page;
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Los_Angeles'});
    await context.addCookies(Object.entries({token:'fixture-token',tenant_id:a,outlet_id:b}).map(([name,value])=>({name,value,url:base})));
    page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`${base}/dashboard/pembelian`,{waitUntil:'domcontentloaded'});await page.locator('.p-summary').waitFor();
    assert.equal(await page.getByLabel('Outlet',{exact:true}).inputValue(),b);
    assert.match(await page.locator('.p-nota').first().innerText(),/100,25/);assert.match(await page.locator('.p-nota').first().innerText(),/1 Okt 2026/);
    await page.getByLabel('Bulan penerimaan').fill('2026-09');await page.locator('.p-summary').waitFor();
    await page.getByRole('button',{name:'Periksa nota belum lunas'}).click();await page.getByRole('heading',{name:'Nota belum lunas dari semua bulan'}).waitFor();
    assert(calls.some(c=>c.path.endsWith('/purchases')&&c.params.unpaid_only==='true'&&!c.params.month));
    await page.getByLabel('Cari nota').fill('NB');await page.getByRole('button',{name:'Cari',exact:true}).click();await page.locator('.p-summary').waitFor();
    assert(calls.some(c=>c.params.search==='NB'));
    await page.getByLabel('Outlet',{exact:true}).selectOption(a);await page.locator('.p-summary').waitFor();
    assert(calls.some(c=>c.path.endsWith('/suppliers')&&c.params.outlet_id===a));
    console.log('PASS cookie outlet, month, all-month debt, search and supplier scope; decimals and WIB under America timezone');
    await page.locator('.p-nota').first().click();await page.getByRole('heading',{name:'Riwayat pembayaran'}).waitFor();
    assert.match(await page.getByRole('dialog').innerText(),/0,01333333/);
    await page.getByLabel('Nominal pembayaran').fill('25.50');await page.getByRole('button',{name:'Sudah dibayar, catat pembayaran'}).click();
    await page.getByRole('button',{name:'Periksa pembayaran sebelumnya'}).waitFor();await page.getByRole('button',{name:'Tutup',exact:true}).click();
    await page.locator('.p-summary').waitFor();await page.locator('.p-nota').first().click();await page.getByRole('button',{name:'Periksa pembayaran sebelumnya'}).waitFor();
    await page.getByRole('button',{name:'Periksa pembayaran sebelumnya'}).click();await page.getByLabel('Nominal pembayaran').waitFor();
    assert.equal(pays.size,1);const payCalls=calls.filter(c=>c.path.endsWith('/pay'));assert.deepEqual(payCalls[0].body,payCalls[1].body);
    await page.keyboard.press('Escape');await page.locator('.p-summary').waitFor();
    await page.getByRole('button',{name:'Catat nota',exact:true}).click();await page.getByLabel('Barang baris 1').waitFor();
    await page.getByLabel('Barang baris 1').selectOption(`p:${a}`);await page.getByLabel('Jumlah baris 1').fill('2');await page.getByLabel('Harga baris 1').fill('50.25');await page.getByLabel('Total baris 1').fill('90.25');
    await page.getByRole('button',{name:'Tambah baris',exact:true}).click();await page.getByLabel('Barang baris 2').selectOption('__other');await page.getByLabel('Nama baris 2').fill('Gas fixture');await page.getByLabel('Harga baris 2').fill('10.25');
    await page.getByLabel('Tanggal barang diterima').fill('2026-09-01');await page.getByLabel('Pembayaran awal').selectOption('debt');await page.getByLabel('Sudah dibayar').fill('20.25');await page.getByLabel('Jatuh tempo',{exact:true}).fill('2026-09-08');
    await page.getByRole('button',{name:'Barang diterima, simpan nota'}).click();await page.getByRole('button',{name:'Periksa penyimpanan nota'}).waitFor();
    await page.getByRole('button',{name:'Tutup',exact:true}).click();await page.getByRole('button',{name:'Catat nota',exact:true}).click();await page.getByRole('button',{name:'Periksa penyimpanan nota'}).waitFor();
    await page.getByRole('button',{name:'Periksa penyimpanan nota'}).click();await page.getByRole('dialog').waitFor({state:'hidden'});await page.locator('.p-summary').waitFor();assert.equal(receipts.size,1);
    const receiveCalls=calls.filter(c=>c.path.endsWith('/purchases')&&c.method==='POST');assert.deepEqual(receiveCalls[0].body,receiveCalls[1].body);
    assert.equal(receiveCalls[0].body.received_at,'2026-09-01T12:00:00+07:00');assert.equal(receiveCalls[0].body.items[0].total_price,'90.25');
    assert.equal(receiveCalls[0].body.due_at,'2026-09-08T23:59:59+07:00');assert.equal(receiveCalls[0].body.items.length,2);
    console.log('PASS historical unit cost precision; uncertain payments and receipts resume after modal close with identical requests');
    await page.getByRole('button',{name:'Catat nota',exact:true}).click();await page.getByLabel('Barang baris 1').waitFor();
    await page.getByLabel('Foto nota').setInputFiles({name:'fixture.png',mimeType:'image/png',buffer:Buffer.alloc(2 * 1024 * 1024)});
    await page.getByText(/Terbaca di foto:/).waitFor();assert.equal(await page.getByLabel('Barang baris 1').inputValue(),'');
    assert.equal(receipts.size,1);assert(calls.some(c=>c.path.endsWith('/invoice-ocr/scan')&&c.params.outlet_id===a));
    await page.getByLabel('Barang baris 1').selectOption('__ingredient');await page.getByLabel('Nama baris 1').fill('Gula baru fixture');await page.getByLabel('Satuan stok baris 1').selectOption('gram');
    await page.getByLabel('Barang baris 1').selectOption('__product');await page.getByLabel('Harga jual baris 1').fill('100');
    await page.getByRole('button',{name:'Tambah baris',exact:true}).click();await page.getByRole('button',{name:'Hapus baris 2'}).click();
    await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Supplier',exact:true}).click();await page.getByRole('button',{name:'Tambah supplier',exact:true}).click();
    await page.getByLabel('Nama supplier',{exact:true}).fill('Supplier baru fixture');await page.getByLabel('Tempo pembayaran').fill('14');await page.getByRole('button',{name:'Simpan supplier'}).click();await page.locator('.p-summary').waitFor();
    await page.getByRole('button',{name:'Ubah supplier Supplier baru fixture'}).click();await page.getByLabel('Supplier aktif untuk pembelian baru').uncheck();await page.getByRole('button',{name:'Simpan supplier'}).click();await page.locator('.p-summary').waitFor();
    await page.getByRole('button',{name:'Hapus supplier Supplier baru fixture'}).click();await page.getByRole('dialog').getByRole('button',{name:'Hapus supplier',exact:true}).click();await page.getByRole('dialog').waitFor({state:'hidden'});await page.locator('.p-summary').waitFor();assert.equal(suppliers.length,1);
    console.log('PASS OCR only drafts unresolved lines in correct outlet; new item controls, supplier create/edit/deactivate/delete');
    await page.getByRole('button',{name:'Nota belanja'}).click();paginated=true;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.locator('.p-summary').waitFor();await page.getByRole('button',{name:'Berikutnya'}).click();await page.getByText('Halaman 2 · 1 nota ditampilkan').waitFor();await page.getByRole('button',{name:'Sebelumnya'}).click();await page.locator('.p-summary').waitFor();paginated=false;
    failRead=true;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.locator('.purchase-workspace [role="alert"]').waitFor();assert.equal(await page.locator('.p-summary').count(),0);assert(!await page.locator('.purchase-workspace').innerText().then(t=>t.includes('SERVER INTERNAL SECRET')));failRead=false;await page.getByRole('button',{name:'Coba lagi',exact:true}).click();await page.locator('.p-summary').waitFor();
    for(const dark of [false,true]){
      await page.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);
      for(const width of [320,375,768,1024,1440]){
        await page.setViewportSize({width,height:1100});await appearance(page,`${width} ${dark?'dark':'light'} page`);
        await page.getByRole('button',{name:'Catat nota',exact:true}).click();await page.getByLabel('Barang baris 1').waitFor();await appearance(page,`${width} form`);await page.keyboard.press('Escape');
        await page.evaluate(()=>document.documentElement.style.fontSize='200%');await appearance(page,`${width} 200%`);
        await page.getByRole('button',{name:'Catat nota',exact:true}).click();await page.getByLabel('Barang baris 1').waitFor();await appearance(page,`${width} 200% form`);await page.keyboard.press('Escape');await page.evaluate(()=>document.documentElement.style.fontSize='');
      }
      await page.screenshot({path:`/tmp/selaris-purchasing-${dark?'dark':'light'}.png`,fullPage:true});
    }
    empty=true;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.getByRole('heading',{name:'Tidak ada nota yang sesuai'}).waitFor();
    for(const route of ['settings','keuangan']) await fs.access(`app/dashboard/${route}/page.tsx`);
    assert.deepEqual(errors,[]);console.log('PASS pagination, explicit read error/retry/empty, routes, 5 widths × 2 themes × 200%, AA contrast and 44px controls; ALL PURCHASING BROWSER CHECKS PASSED');
  }catch(e){if(page)await page.screenshot({path:'/tmp/selaris-purchasing-failure.png',fullPage:true});throw e;}
  finally{await browser.close();await new Promise(resolve=>fixture.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
