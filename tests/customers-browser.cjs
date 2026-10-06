// Customer fixtures only. The real backend is never called by this suite.
const http=require('node:http'),assert=require('node:assert/strict'),fs=require('node:fs/promises');
const {chromium}=require('playwright');
const base=process.env.BROWSER_BASE_URL||'http://127.0.0.1:3295';
const a='11111111-1111-4111-8111-111111111111';
let failRead=false,failDetail=false,failCreate=true,failEdit=true,failNote=true,empty=false,paginated=false,workspaceKey='fixture-a';
const calls=[],writes=new Map();
let people=[{id:a,name:'=Fixture pelanggan',phone:'6281234567890',email:'qa@example.com',notes:'Preferensi fixture',birthday:'1995-01-01',wa_marketing_consent:true,consent_given_at:'2026-09-30T18:00:00Z',row_version:1,total_visits:22,total_spent:'225.50',avg_spent:'10.25',first_visit_at:'2026-09-01T00:00:00Z',last_visit_at:'2026-09-30T18:00:00Z'}];
let timeline=[];
const fixture=http.createServer(async(req,res)=>{
  const url=new URL(req.url,'http://fixture'),path=url.pathname.replace(/\/+$/,'');let raw='';for await(const chunk of req)raw+=chunk;
  const body=raw?JSON.parse(raw):{};calls.push({path,method:req.method,params:Object.fromEntries(url.searchParams),body});let data={},status=200;
  if (path.endsWith('/auth/access')) data = { enforcement_mode: 'owner', permissions: [], scope: 'tenant', outlets: [], access_version: 'owner-fixture' };
  else if(path.endsWith('/users/me'))data={id:a,subscription_tier:'pro'};
  else if(path.endsWith('/outlets'))data=[{id:a,name:'Outlet fixture',brand_id:a}];
  else if(path.endsWith('/customers/workspace')&&req.method==='GET'){
    if(failRead)status=500;
    let items=empty?[]:people;
    if(paginated)items=Array.from({length:51},(_,i)=>({...people[0],id:`page-${i}`,name:`Fixture halaman ${i}`}));
    const search=url.searchParams.get('search'),segment=url.searchParams.get('segment');
    if(search==='absent'||segment==='lapse')items=[];
    if(search==='slow')await new Promise(r=>setTimeout(r,1000));
    if(search==='latest')items=items.map(c=>({...c,name:'Fixture latest'}));
    const total=items.length,skip=Number(url.searchParams.get('skip')||0);
    data={items:items.slice(skip,skip+50),total,skip,limit:50,summary:{total:empty?0:people.length,repeat:empty?0:1,spent:empty?'0.00':'225.50',consented:empty?0:1},generated_at:'2026-09-30T18:00:00Z',scope:'tenant_all_outlets',timezone:'Asia/Jakarta',basis:'paid_orders_gross',history_note:'Nilai nota berstatus lunas, sebelum pengurangan refund. Satu nota dihitung satu transaksi.',workspace_key:workspaceKey};
  }else if(path.endsWith('/notes')&&req.method==='POST'){
    if(writes.has(body.client_request_id))data=writes.get(body.client_request_id);
    else{data={id:body.client_request_id};writes.set(body.client_request_id,data);timeline.unshift({...body,id:data.id,created_at:'2026-09-30T18:00:00Z'});}
    if(failNote){failNote=false;status=500;}
  }else if(path.includes('/customers/workspace')&&['POST','PUT'].includes(req.method)){
    if(writes.has(body.client_request_id))data=writes.get(body.client_request_id);
    else{const id=req.method==='PUT'?path.split('/').pop():'new-fixture';data={id,row_version:2};writes.set(body.client_request_id,data);
      const profile={...people[0],...body,...data};people=req.method==='PUT'?people.map(c=>c.id===id?profile:c):[...people,profile];}
    if(req.method==='POST'&&failCreate){failCreate=false;status=500;}else if(req.method==='PUT'&&failEdit){failEdit=false;status=500;}
  }else if(path.includes('/customers/workspace/')){
    if(failDetail)status=500;
    const c=people.find(c=>c.id===path.split('/').pop())||people[0],skip=Number(url.searchParams.get('skip')||0);
    data={...c,orders:Array.from({length:22},(_,i)=>({id:`order-${i}`,order_number:`FIXTURE-${i}`,created_at:'2026-09-30T18:00:00Z',total_amount:'10.25',items:[{name:'Kopi fixture',qty:2}]})).slice(skip,skip+20),history_skip:skip,history_limit:20,favourites:[{id:a,name:'Kopi fixture',qty:44}],timeline,timeline_limit:100};
  }
  res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(status>=400?{detail:'SERVER INTERNAL SECRET'}:{success:true,data,message:'Data fixture disimpan'}));
});

async function appearance(page,label){
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${label} overflow`);
  const roots=page.locator('.customer-workspace,.inventory-dialog[open]');
  for(let i=0;i<await roots.count();i++){
    const issues=await roots.nth(i).evaluate(root=>{
      const rgb=v=>v.match(/[\d.]+/g).slice(0,3).map(Number),lum=v=>rgb(v).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0),issues=[];
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
}

(async()=>{
  await new Promise(resolve=>fixture.listen(Number(process.env.FIXTURE_PORT || 8395),'127.0.0.1',resolve));
  const browser=await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE, headless:true,args:['--no-sandbox']});let page;
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Los_Angeles'});
    await context.addCookies(Object.entries({token:'fixture-token',tenant_id:a,outlet_id:a}).map(([name,value])=>({name,value,url:base})));
    page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`${base}/dashboard/pelanggan`,{waitUntil:'domcontentloaded'});await page.locator('.c-summary').waitFor();
    assert.match(await page.locator('.c-list').innerText(),/225,50/);assert.match(await page.locator('.c-list').innerText(),/1 Okt 2026/);
    const downloadWait=page.waitForEvent('download');await page.getByRole('button',{name:'Ekspor halaman CSV'}).click();
    const csv=await fs.readFile(await(await downloadWait).path(),'utf8');assert(csv.includes("'=Fixture pelanggan")&&csv.includes('225.50')&&csv.includes('Halaman yang sedang ditampilkan'));
    await page.getByLabel('Urutkan').selectOption('spent');await page.locator('.c-summary').waitFor();
    await page.getByLabel('Kelompok pelanggan').selectOption('lapse');await page.getByRole('heading',{name:'Tidak ada pelanggan sesuai filter'}).waitFor();
    await page.getByRole('button',{name:'Reset filter'}).click();await page.locator('.c-summary').waitFor();
    await page.getByLabel('Cari pelanggan').fill('slow');await page.waitForTimeout(350);await page.getByLabel('Cari pelanggan').fill('latest');
    await page.getByRole('heading',{name:'Fixture latest'}).waitFor();await page.waitForTimeout(1200);assert.equal(await page.getByRole('heading',{name:'Fixture latest'}).count(),1);
    await page.getByLabel('Cari pelanggan').fill('');await page.getByRole('heading',{name:'=Fixture pelanggan',exact:true}).waitFor();
    paginated=true;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.getByRole('heading',{name:'Fixture halaman 0',exact:true}).waitFor();
    await page.getByRole('button',{name:'Berikutnya',exact:true}).click();await page.getByRole('heading',{name:'Fixture halaman 50',exact:true}).waitFor();
    await page.getByRole('button',{name:'Sebelumnya',exact:true}).click();await page.getByRole('heading',{name:'Fixture halaman 0',exact:true}).waitFor();
    paginated=false;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.getByRole('heading',{name:'=Fixture pelanggan',exact:true}).waitFor();
    console.log('PASS money precision/WIB, formula-safe explicitly paged CSV, sort/filters/reset, stale search responses and pagination');
    await page.getByRole('button',{name:'Tambah pelanggan',exact:true}).click();await page.getByLabel('Nama pelanggan').fill('Pelanggan baru fixture');
    await page.getByLabel('Nomor HP',{exact:true}).fill('081234567899');await page.getByLabel('Email',{exact:true}).fill('new@example.com');
    await page.getByLabel('Tanggal lahir',{exact:true}).fill('1990-01-01');await page.getByLabel('Preferensi / catatan profil').fill('Tanpa gula fixture');
    await page.getByLabel('Pelanggan sudah menyetujui').check();await page.getByRole('button',{name:'Simpan profil',exact:true}).click();
    await page.getByRole('button',{name:'Periksa penyimpanan profil'}).waitFor();await page.getByRole('button',{name:'Tutup',exact:true}).click();
    await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'Lanjutkan penyimpanan'}).waitFor();
    await page.getByRole('button',{name:'Lanjutkan penyimpanan'}).click();await page.getByRole('button',{name:'Periksa penyimpanan profil'}).click();await page.getByRole('dialog').waitFor({state:'hidden'});
    await page.getByRole('heading',{name:'Pelanggan baru fixture',exact:true}).waitFor();assert.equal(writes.size,1);
    failDetail=true;await page.getByRole('button',{name:'Buka profil =Fixture pelanggan'}).click();await page.getByRole('dialog').getByRole('alert').waitFor();
    assert(!await page.getByRole('dialog').innerText().then(t=>t.includes('SERVER INTERNAL SECRET')));
    failDetail=false;await page.getByRole('dialog').getByRole('button',{name:'Coba lagi'}).click();await page.getByRole('heading',{name:'Produk yang sering dibeli'}).waitFor();
    assert.match(await page.getByRole('dialog').innerText(),/Nilai nota berstatus lunas sebelum pengurangan refund/);
    await page.getByRole('button',{name:'Transaksi berikutnya'}).click();await page.getByText('FIXTURE-20',{exact:false}).waitFor();
    await page.getByRole('button',{name:'Transaksi sebelumnya'}).click();await page.getByText('FIXTURE-0 ·',{exact:false}).waitFor();
    await page.getByRole('button',{name:'Edit profil',exact:true}).click();await page.getByLabel('Nama pelanggan').fill('Pelanggan diperbarui fixture');
    await page.getByLabel('Nomor HP',{exact:true}).fill('081234567888');assert.equal(await page.getByLabel('Pelanggan sudah menyetujui').isChecked(),false);
    await page.getByRole('button',{name:'Simpan profil',exact:true}).click();await page.getByRole('button',{name:'Periksa penyimpanan profil'}).waitFor();
    await page.getByRole('button',{name:'Tutup',exact:true}).click();await page.getByRole('button',{name:'Lanjutkan penyimpanan'}).click();await page.getByRole('button',{name:'Periksa penyimpanan profil'}).click();
    await page.getByRole('heading',{name:'Produk yang sering dibeli'}).waitFor();assert.equal(writes.size,2);
    await page.getByLabel('Jenis catatan').selectOption('complaint');await page.getByLabel('Catatan baru').fill('Keluhan fixture');
    await page.getByRole('button',{name:'Simpan catatan',exact:true}).click();await page.getByRole('button',{name:'Periksa penyimpanan catatan'}).waitFor();await page.keyboard.press('Escape');
    await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'Lanjutkan penyimpanan'}).waitFor();await page.getByRole('button',{name:'Lanjutkan penyimpanan'}).click();
    await page.getByRole('button',{name:'Periksa penyimpanan catatan'}).click();await page.getByRole('button',{name:'Simpan catatan',exact:true}).waitFor();assert.equal(timeline.length,1);assert.equal(writes.size,3);
    await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
    console.log('PASS create/edit/note with uncertain result, close/reload retry same UUID, history pagination/detail retry, consent reset on phone change');
    for(const theme of ['light','dark'])for(const width of [320,375,768,1024,1440]){
      await page.setViewportSize({width,height:1000});await page.evaluate(theme=>document.documentElement.classList.toggle('dark',theme==='dark'),theme);
      await appearance(page,`${theme} ${width}`);
      await page.getByRole('button',{name:'Buka profil Pelanggan diperbarui fixture'}).click();await page.getByRole('heading',{name:'Produk yang sering dibeli'}).waitFor();await appearance(page,`${theme} ${width} profile`);
      await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
      await page.getByRole('button',{name:'Tambah pelanggan',exact:true}).click();await page.getByLabel('Nama pelanggan').waitFor();await appearance(page,`${theme} ${width} form`);
      await page.evaluate(()=>document.documentElement.style.fontSize='200%');await appearance(page,`${theme} ${width} form 200%`);
      await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});await appearance(page,`${theme} ${width} page 200%`);
      await page.evaluate(()=>document.documentElement.style.fontSize='');
    }
    await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.classList.remove('dark'));await page.screenshot({path:'/tmp/selaris-customers-light.png',fullPage:true});
    await page.evaluate(()=>document.documentElement.classList.add('dark'));await page.screenshot({path:'/tmp/selaris-customers-dark.png',fullPage:true});
    await page.getByRole('button',{name:'Tambah pelanggan',exact:true}).click();await page.getByLabel('Nama pelanggan').focus();await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(()=>document.activeElement?.textContent),'Tutup');await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(()=>document.activeElement?.textContent),'Tambah pelanggan');
    console.log('PASS five viewport sizes, two themes, 200% text, AA contrast, 44px controls, keyboard/focus/Escape');
    failRead=true;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.locator('.customer-workspace [role="alert"]').waitFor();
    assert.equal(await page.locator('.c-summary').count(),0);failRead=false;await page.getByRole('button',{name:'Coba lagi',exact:true}).click();await page.locator('.c-summary').waitFor();
    empty=true;await page.getByRole('button',{name:'Muat ulang',exact:true}).click();await page.getByRole('heading',{name:'Belum ada pelanggan tercatat'}).waitFor();
    assert.equal(errors.length,0,errors);
    assert(calls.some(c=>c.params.segment==='lapse')&&calls.some(c=>c.params.sort==='spent')&&calls.some(c=>c.params.skip==='50'));
    console.log('PASS explicit list error/retry and empty states, no masked-zero summary, no page errors');
    failCreate=true;await page.getByRole('button',{name:'Tambah pelanggan',exact:true}).click();await page.getByLabel('Nama pelanggan').fill('Private draft fixture');
    await page.getByRole('button',{name:'Simpan profil',exact:true}).click();await page.getByRole('button',{name:'Periksa penyimpanan profil'}).waitFor();await page.keyboard.press('Escape');
    workspaceKey='fixture-b';await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('heading',{name:'Belum ada pelanggan tercatat'}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Lanjutkan penyimpanan'}).count(),0);
    console.log('PASS pending contact data is scoped to the authenticated business/user instead of shared across accounts');
  }catch(error){if(page)await page.screenshot({path:'/tmp/selaris-customers-failure.png',fullPage:true});throw error;}
  finally{await browser.close();fixture.close();}
})();
