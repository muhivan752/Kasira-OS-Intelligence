'use client';

import { useEffect, useState } from 'react';
import { InventoryDialog } from '@/components/inventory-dialog';
import { getPurchaseTargets, getPurchaseDetail, createPurchase, payPurchase, createSupplier,
  updateSupplier } from '@/app/actions/api';
import type { Purchase, PurchaseSetup, PurchaseTarget, Supplier } from '@/lib/purchasing';
import { purchaseDate, quantityLabel, unitCost } from '@/lib/purchasing';
import { jakartaDate, money } from '@/lib/finance';

type Payload = Record<string, unknown>;
const pendingKey = (kind: string, id: string) => `purchasing:${kind}:${id}`;
function storePending(key: string, payload: Payload | null) {
  try { if (payload) sessionStorage.setItem(key, JSON.stringify(payload)); else sessionStorage.removeItem(key); } catch { /* Saving still works when browser storage is blocked. */ }
}
function readPending(key: string): Payload | null {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null'); } catch { return null; }
}
const numeric = (value: string) => /^\d+(\.\d{1,2})?$/.test(value) && Number(value) < 1e10;
interface DraftLine { key: string; target: string; name: string; quantity: string; unit: string; price: string; total: string; base: string; sell: string; raw?: string }
const blankLine = (): DraftLine => ({key:crypto.randomUUID(),target:'',name:'',quantity:'1',unit:'',price:'',total:'',base:'',sell:''});
const amountOf = (line: DraftLine) => line.total !== '' ? Number(line.total) : Math.round(Number(line.quantity) * Number(line.price) * 100) / 100;

export function PurchaseForm({outlet,isPro,suppliers,onClose,onSaved,managed=false,canScan=true,canReceive=true,canCreateIngredient=true}:{outlet:PurchaseSetup['outlets'][number];isPro:boolean;suppliers:Supplier[];onClose:()=>void;onSaved:(p:Purchase)=>void;managed?:boolean;canScan?:boolean;canReceive?:boolean;canCreateIngredient?:boolean}) {
  const [targets,setTargets] = useState<PurchaseTarget[] | null>(null), [targetError,setTargetError] = useState(''), [reload,setReload] = useState(0);
  const [lines,setLines] = useState<DraftLine[]>(() => [blankLine()]);
  const [fields,setFields] = useState({supplier:'',supplierName:'',date:jakartaDate(),invoice:'',notes:'',mode:'paid',paid:'0',due:''});
  const [photo,setPhoto] = useState<string | null>(null), [scanNote,setScanNote] = useState(''), [busy,setBusy] = useState(false), [scanning,setScanning] = useState(false), [error,setError] = useState('');
  const [pending,setPending] = useState<Payload | null>(null), key = pendingKey('receive',outlet.id);
  useEffect(() => { setPending(readPending(key)); }, [key]);
  useEffect(() => { let active=true; setTargetError(''); setTargets(null); void getPurchaseTargets(outlet.id,outlet.brand_id,isPro).then(result => { if (active) { if (result.success) setTargets(result.data); else setTargetError(result.message); } }); return () => { active=false; }; }, [outlet.id,outlet.brand_id,isPro,reload]);
  const total = lines.reduce((sum,line) => sum + amountOf(line),0), locked = busy || scanning || !!pending;
  const update = (key:string,patch:Partial<DraftLine>) => setLines(old => old.map(line => line.key === key ? {...line,...patch} : line));
  const field = (name:keyof typeof fields,value:string) => setFields(old => ({...old,[name]:value}));
  const scan = async (file:File) => {
    if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) { setError('Pilih foto JPG, PNG, atau WebP maksimal 8 MB.'); return; }
    if (lines.some(l => l.target || l.price || l.raw) && !window.confirm('Ganti baris yang sedang diisi dengan hasil foto?')) return;
    setScanning(true); setError(''); setScanNote('');
    try {
      const scanFile = new FormData(); scanFile.append('file',file);
      const scanResponse = await fetch(`/api/upload/invoice?outlet_id=${encodeURIComponent(outlet.id)}`, {method:'POST',body:scanFile});
      const result = await scanResponse.json();
      if (!result.success || !result.data) { setError(result.message); return; }
      const extracted = result.data, rawLines = extracted.items || [];
      if (!rawLines.length || rawLines.length > 100) { setError('Jumlah baris foto tidak valid. Isi manual atau gunakan foto yang lebih jelas.'); return; }
      setPhoto(null);
      if (extracted.invoice_number) setFields(old => ({...old,invoice:old.invoice || String(extracted.invoice_number)}));
      setLines(rawLines.map((item:any) => {
        const target = targets?.find(t => t.kind === 'ingredient' && t.id === item.matched_ingredient_id)
          || targets?.find(t => t.kind === 'product' && t.name.toLowerCase() === String(item.name).toLowerCase());
        return {...blankLine(),target:target?.key || '',name:String(item.name || ''),raw:String(item.name || ''),quantity:String(item.quantity ?? ''),unit:String(item.unit || target?.unit || ''),price:String(item.unit_price ?? ''),total:item.total_price == null ? '' : String(item.total_price)};
      }));
      if (extracted.supplier_name && !fields.supplier) {
        const existing = suppliers.find(s => s.is_active && s.name.toLowerCase() === String(extracted.supplier_name).toLowerCase());
        setFields(old => ({...old,supplier:existing?.id || '__new',supplierName:String(extracted.supplier_name),invoice:old.invoice || String(extracted.invoice_number || '')}));
      }
      setScanNote(`Hasil foto perlu diperiksa. Total yang terbaca: ${extracted.grand_total == null ? 'belum terbaca' : money(extracted.grand_total)}. Baris dan pembayaran belum disimpan.`);
      const uploadFile = new FormData(); uploadFile.append('file',file);
      const uploadResponse = await fetch('/api/upload', {method:'POST',body:uploadFile}); const uploaded = await uploadResponse.json();
      if (uploadResponse.ok && uploaded.url) setPhoto(uploaded.url); else setScanNote(note => note + ' Foto belum tersimpan; baris tetap bisa diperiksa.');
    } catch { setError('Foto belum bisa diproses. Isi manual atau coba lagi.'); }
    finally { setScanning(false); }
  };
  const submit = async (event:React.FormEvent) => {
    event.preventDefault(); if (busy || scanning) return; setError(''); let payload=pending;
    if (!payload) {
      if (!targets) return;
      if (!fields.date || fields.date > jakartaDate()) { setError('Pilih tanggal barang sudah diterima.'); return; }
      if (fields.supplier === '__new' && !fields.supplierName.trim()) { setError('Isi nama supplier baru.'); return; }
      if (!lines.length || !Number.isFinite(total) || total >= 1e10) { setError('Periksa jumlah dan total nota.'); return; }
      const items:Payload[]=[];
      for (const [index,line] of lines.entries()) {
        const target=targets.find(t => t.key === line.target), qty=Number(line.quantity);
        if (!line.target || !Number.isFinite(qty) || qty <= 0 || qty > 1e9 || !numeric(line.price) || line.total !== '' && !numeric(line.total)) { setError(`Periksa barang, jumlah, dan harga pada baris ${index + 1}. Semua baris harus lengkap.`); return; }
        if ((line.target === '__product' || target?.kind === 'product') && (!Number.isInteger(qty) || line.unit !== 'pcs')) { setError(`Baris ${index + 1}: produk jadi dicatat per pcs dengan jumlah bulat.`); return; }
        if (!target && !line.name.trim()) { setError(`Isi nama pada baris ${index + 1}.`); return; }
        if (line.target === '__product' && !numeric(line.sell)) { setError(`Isi harga jual produk pada baris ${index + 1}.`); return; }
        const base:Payload={quantity:qty,unit:line.unit || null,unit_price:line.price,total_price:amountOf(line).toFixed(2)};
        if (target) base[target.kind === 'ingredient' ? 'ingredient_id' : 'product_id']=target.id;
        else if (line.target === '__ingredient') base.new_ingredient={name:line.name.trim(),base_unit:line.base || null};
        else if (line.target === '__product') base.new_product={name:line.name.trim(),sell_price:line.sell};
        else base.name=line.name.trim();
        items.push(base);
      }
      if (fields.mode === 'debt' && (!numeric(fields.paid) || Number(fields.paid) >= total || fields.due && fields.due < fields.date)) { setError('Pembayaran awal harus di bawah total, dan jatuh tempo tidak sebelum penerimaan.'); return; }
      payload={client_request_id:crypto.randomUUID(),outlet_id:outlet.id,supplier_id:fields.supplier && fields.supplier !== '__new' ? fields.supplier : null,
        supplier_name:fields.supplier === '__new' ? fields.supplierName.trim() : null,invoice_no:fields.invoice.trim() || null,photo_url:photo,notes:fields.notes.trim() || null,
        received_at:fields.date === jakartaDate() ? new Date().toISOString() : `${fields.date}T12:00:00+07:00`,
        paid_amount:fields.mode === 'paid' ? null : fields.paid,due_at:fields.mode === 'debt' && fields.due ? `${fields.due}T23:59:59+07:00` : null,items};
    }
    setBusy(true); setPending(payload); storePending(key,payload); const result=await createPurchase(payload); setBusy(false);
    if (result.success) { storePending(key,null); onSaved(result.data); }
    else { setError(result.message); if (!result.uncertain) { setPending(null); storePending(key,null); } }
  };
  return <InventoryDialog title={`Catat nota · ${outlet.name}`} busy={busy || scanning} onClose={onClose}><form className="finance-form p-form" onSubmit={submit}>
    <p>Pastikan barang sudah diterima. Bahan dan produk dengan pencatatan stok menambah stok; baris Biaya hanya mencatat pengeluaran.</p>
    {pending ? <div className="f-notice"><h3>Periksa penyimpanan nota sebelumnya</h3><p>Permintaan yang sama akan diperiksa ulang supaya stok dan utang tidak tercatat dua kali. Jangan membuat nota baru untuk penerimaan ini sebelum hasilnya diketahui.</p><p>{String((pending.items as unknown[])?.length || 0)} baris · tanggal {purchaseDate(String(pending.received_at))}</p></div> : <>
      {!targets && !targetError && <p role="status">Memuat daftar barang…</p>}
      {targetError && <div className="f-notice f-error" role="alert"><p>{targetError}</p><button className="f-button" type="button" onClick={() => setReload(n => n + 1)}>Coba muat barang lagi</button></div>}
      <fieldset disabled={locked || !targets} className="p-fields">
        {canScan && <label className="p-upload">Foto nota (opsional)<input aria-label="Foto nota" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={e => { const file=e.target.files?.[0]; if (file) void scan(file); e.target.value=''; }} /><span>JPG, PNG, WebP; maksimal 8 MB. Foto mengisi draf untuk Anda periksa.</span></label>}
        {scanning && <p role="status">Membaca foto nota…</p>}{scanNote && <p className="f-notice" role="status">{scanNote}</p>}
        <div className="f-field-grid"><label>Supplier<select aria-label="Supplier" value={fields.supplier} onChange={e => field('supplier',e.target.value)}><option value="">Tanpa supplier</option>{suppliers.filter(s => s.is_active).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}<option value="__new">Supplier baru</option></select></label>
          <label>Tanggal barang diterima<input aria-label="Tanggal barang diterima" type="date" max={jakartaDate()} required value={fields.date} onChange={e => field('date',e.target.value)} /></label>
          {fields.supplier === '__new' && <label>Nama supplier baru<input aria-label="Nama supplier baru" maxLength={120} required value={fields.supplierName} onChange={e => field('supplierName',e.target.value)} /></label>}
          <label>Nomor nota supplier (opsional)<input aria-label="Nomor nota supplier" maxLength={80} value={fields.invoice} onChange={e => field('invoice',e.target.value)} /></label></div>
        <h3>Barang dan biaya</h3>
        {lines.map((line,index) => { const target=targets?.find(t => t.key === line.target), product=target?.kind === 'product' || line.target === '__product'; return <fieldset className="p-line" key={line.key}><legend>Baris {index + 1}</legend>
          {line.raw && <p className="f-explanation">Terbaca di foto: {line.raw}. Periksa barang, satuan, dan harga.</p>}
          <label>Barang atau biaya<select aria-label={`Barang baris ${index + 1}`} required value={line.target} onChange={e => { const next=targets?.find(t => t.key === e.target.value); update(line.key,{target:e.target.value,unit:next?.unit || (e.target.value === '__product' ? 'pcs' : '')}); }}><option value="">Pilih barang atau biaya</option>
            {canReceive && <optgroup label="Bahan baku">{targets?.filter(t => t.kind === 'ingredient').map(t => <option key={t.key} value={t.key}>{t.name} · stok {t.unit}</option>)}</optgroup>}
            {canReceive && <optgroup label="Produk jadi">{targets?.filter(t => t.kind === 'product').map(t => <option key={t.key} value={t.key}>{t.name}{!t.stockEnabled ? ' · stok tidak dicatat' : ''}</option>)}</optgroup>}
            <optgroup label="Catatan baru">{isPro && canReceive && canCreateIngredient && <option value="__ingredient">Bahan baku baru</option>}{!managed && <option value="__product">Produk jadi baru</option>}<option value="__other">Biaya, tanpa stok</option></optgroup></select></label>
          {line.target.startsWith('__') && <label>Nama<input aria-label={`Nama baris ${index + 1}`} required maxLength={120} value={line.name} onChange={e => update(line.key,{name:e.target.value})} /></label>}
          <div className="p-line-grid"><label>Jumlah<input aria-label={`Jumlah baris ${index + 1}`} required type="number" min="0.00000001" max="1000000000" step={product ? '1' : 'any'} value={line.quantity} onChange={e => update(line.key,{quantity:e.target.value})} /></label>
            <label>Satuan<select aria-label={`Satuan baris ${index + 1}`} value={line.unit} onChange={e => update(line.key,{unit:e.target.value})}><option value="">Ikut satuan stok</option>{(product ? ['pcs'] : Array.from(new Set([target?.unit || '', 'gram','kg','ons','ml','liter','galon','pcs','butir','botol','lembar','dus','lusin','tray','bungkus','sachet','pak']))).filter(Boolean).map(u => <option key={u} value={u}>{u}</option>)}</select></label>
            <label>Harga per satuan<input aria-label={`Harga baris ${index + 1}`} required type="number" min="0" step="0.01" value={line.price} onChange={e => update(line.key,{price:e.target.value})} /></label>
            <label>Total baris (opsional)<input aria-label={`Total baris ${index + 1}`} type="number" min="0" step="0.01" value={line.total} placeholder="Jumlah × harga" onChange={e => update(line.key,{total:e.target.value})} /></label></div>
          {line.target === '__ingredient' && <label>Satuan stok bahan baru<select aria-label={`Satuan stok baris ${index + 1}`} value={line.base} onChange={e => update(line.key,{base:e.target.value})}><option value="">Ikut satuan nota</option>{['gram','ml','pcs','bungkus'].map(u => <option key={u}>{u}</option>)}</select></label>}
          {line.target === '__product' && <label>Harga jual produk<input aria-label={`Harga jual baris ${index + 1}`} required type="number" min="0" step="0.01" value={line.sell} onChange={e => update(line.key,{sell:e.target.value})} /></label>}
          <div className="p-line-end"><p>Total: <strong>{Number.isFinite(amountOf(line)) ? money(amountOf(line)) : 'Periksa nominal'}</strong></p><button className="f-button f-delete" type="button" aria-label={`Hapus baris ${index + 1}`} disabled={lines.length === 1} onClick={() => setLines(old => old.filter(l => l.key !== line.key))}>Hapus baris</button></div>
          {target?.kind === 'ingredient' && <p className="f-explanation">Stok dicatat dalam {target.unit}. Satuan nota harus bisa dikonversi ke satuan ini.</p>}
          {target?.kind === 'product' && !target.stockEnabled && <p className="f-explanation">Produk ini belum mencatat stok. Nota memperbarui harga beli; jumlah stok tidak bertambah.</p>}
          {line.target === '__other' && <p className="f-explanation">Baris ini menjadi biaya operasional dan tidak menambah stok.</p>}
        </fieldset>; })}
        <button className="f-button" type="button" disabled={lines.length >= 100} onClick={() => setLines(old => [...old,blankLine()])}>Tambah baris</button>
        <div className="f-notice"><h3>Total nota</h3><p className="f-secondary-amount">{Number.isFinite(total) ? money(total) : 'Periksa nominal'}</p><p>Total yang Anda isi menggantikan jumlah × harga pada baris itu, termasuk untuk harga modal.</p></div>
        <label>Pembayaran awal<select aria-label="Pembayaran awal" value={fields.mode} onChange={e => field('mode',e.target.value)}><option value="paid">Sudah dibayar lunas</option><option value="debt">Belum lunas atau dibayar sebagian</option></select></label>
        {fields.mode === 'debt' && <div className="f-field-grid"><label>Sudah dibayar<input aria-label="Sudah dibayar" required type="number" min="0" step="0.01" value={fields.paid} onChange={e => field('paid',e.target.value)} /></label><label>Jatuh tempo (opsional)<input aria-label="Jatuh tempo" type="date" min={fields.date} value={fields.due} onChange={e => field('due',e.target.value)} /></label><p className="f-explanation">Kosong memakai tempo supplier. Tempo 0 atau tanpa supplier memakai 7 hari untuk nota utang.</p><p>Sisa utang: {money(Math.max(total - Number(fields.paid),0))}</p></div>}
        <label>Catatan (opsional)<input aria-label="Catatan nota" maxLength={1000} value={fields.notes} onChange={e => field('notes',e.target.value)} /></label>
      </fieldset>
    </>}
    {error && <p className="f-notice f-error" role="alert">{error}</p>}
    <div className="f-form-actions"><button className="f-button" type="button" disabled={busy || scanning} onClick={onClose}>Tutup</button><button className="f-button f-primary" disabled={busy || scanning || !pending && !targets} type="submit">{busy ? 'Memeriksa…' : pending ? 'Periksa penyimpanan nota' : 'Barang diterima, simpan nota'}</button></div>
  </form></InventoryDialog>;
}

export function PurchaseDetail({id,onClose,onSaved,canPay=true}:{id:string;onClose:()=>void;onSaved:()=>void;canPay?:boolean}) {
  const [purchase,setPurchase] = useState<Purchase | null>(null), [error,setError] = useState(''), [loading,setLoading] = useState(true), [busy,setBusy] = useState(false), [refresh,setRefresh] = useState(0);
  const [amount,setAmount] = useState(''), [pending,setPending] = useState<Payload | null>(null), key=pendingKey('pay',id);
  useEffect(() => { setPending(readPending(key)); }, [key]);
  useEffect(() => { let active=true; setLoading(true); setError(''); void getPurchaseDetail(id).then(result => { if (!active) return; if (result.success) { setPurchase(result.data); setAmount(result.data.outstanding_amount); } else setError(result.message); setLoading(false); }); return () => { active=false; }; }, [id,refresh]);
  const submit = async (e:React.FormEvent) => {
    e.preventDefault(); if (!purchase || busy) return;
    if (!pending && (!numeric(amount) || Number(amount) <= 0 || Number(amount) > Number(purchase.outstanding_amount))) { setError('Isi pembayaran lebih dari nol dan tidak melebihi sisa utang.'); return; }
    const payload=pending || {client_request_id:crypto.randomUUID(),amount,row_version:purchase.row_version};
    setBusy(true); setError(''); setPending(payload); storePending(key,payload); const result=await payPurchase(id,payload); setBusy(false);
    if (result.success) { storePending(key,null); setPending(null); setPurchase(result.data); setAmount(result.data.outstanding_amount); onSaved(); }
    else { setError(result.message); if (!result.uncertain) { storePending(key,null); setPending(null); } }
  };
  return <InventoryDialog title={purchase?.po_number || 'Detail nota'} busy={busy} onClose={onClose}><div className="finance-form p-form">
    {loading ? <p role="status">Memuat detail nota…</p> : purchase && <><div><h3>{purchase.supplier_name || 'Tanpa supplier'}</h3><p>Barang diterima {purchaseDate(purchase.received_at)}{purchase.invoice_no ? ` · ${purchase.invoice_no}` : ''}</p>{purchase.notes && <p>{purchase.notes}</p>}{purchase.photo_url && <a href={purchase.photo_url} target="_blank" rel="noreferrer">Lihat foto nota</a>}</div>
      <ul className="p-detail-lines">{purchase.items.map(i => <li key={i.id}><div><strong>{i.name}</strong><p>{quantityLabel(i.quantity)} {i.unit || ''} × {money(i.unit_price)}</p>{i.qty_base != null && i.qty_base !== i.quantity && <p>Jumlah stok masuk: {quantityLabel(i.qty_base)} dalam satuan stok</p>}{i.is_other && <p>Biaya operasional, tanpa stok</p>}
        {i.cost_before != null && i.cost_after != null && <p>Harga modal per {i.base_unit || 'satuan stok'} saat nota: {unitCost(i.cost_before)} menjadi {unitCost(i.cost_after)}</p>}</div><strong>{money(i.total_price)}</strong></li>)}</ul>
      <dl className="f-calculation"><div><dt>Total nota</dt><dd>{money(purchase.total_amount)}</dd></div><div><dt>Sudah dibayar</dt><dd>{money(purchase.paid_amount)}</dd></div><div className="f-total"><dt>Sisa utang</dt><dd>{money(purchase.outstanding_amount)}</dd></div>{Number(purchase.outstanding_amount) > 0 && <div><dt>Jatuh tempo</dt><dd>{purchaseDate(purchase.due_at)}</dd></div>}</dl>
      <section><h3>Riwayat pembayaran</h3>{purchase.paid_amount == null ? <p>Nominal dan riwayat pembayaran tidak diizinkan untuk akun ini.</p> : purchase.payments?.length ? <ul className="p-payments">{purchase.payments.map(p => <li key={p.id}><span>{purchaseDate(p.paid_at)} · {p.kind === 'initial' ? 'Pembayaran awal' : 'Cicilan'}</span><strong>{money(p.amount)}</strong></li>)}</ul> : <p>Belum ada riwayat pembayaran.</p>}
        {purchase.paid_amount != null && (purchase.payment_history_incomplete || Math.abs((purchase.payments || []).reduce((sum,p) => sum + Number(p.amount),0) - Number(purchase.paid_amount)) > .009) && <p className="f-notice">Riwayat lama belum lengkap. Total pembayaran di atas tetap mengikuti catatan nota.</p>}</section>
      {canPay && (Number(purchase.outstanding_amount) > 0 || pending) && <form className="finance-form p-payment" onSubmit={submit}><h3>Catat pembayaran utang</h3><p>Catat setelah supplier menerima pembayaran. Tombol ini menyimpan catatan pembayaran dan tidak mentransfer uang.</p>
        {pending ? <p className="f-notice">Periksa pembayaran {money(String(pending.amount))} dari permintaan sebelumnya supaya tidak tercatat dua kali.</p> : <label>Nominal pembayaran<input aria-label="Nominal pembayaran" required type="number" min="0.01" step="0.01" max={purchase.outstanding_amount} value={amount} onChange={e => setAmount(e.target.value)} disabled={busy} /></label>}
        <button className="f-button f-primary" type="submit" disabled={busy}>{busy ? 'Memeriksa…' : pending ? 'Periksa pembayaran sebelumnya' : 'Sudah dibayar, catat pembayaran'}</button></form>}
    </>}
    {error && <p className="f-notice f-error" role="alert">{error}</p>}
    <div className="f-form-actions"><button className="f-button" disabled={busy || loading || !!pending} onClick={() => setRefresh(n => n + 1)}>Muat ulang nota</button><button className="f-button" disabled={busy} onClick={onClose}>Tutup</button></div>
  </div></InventoryDialog>;
}

export function SupplierForm({initial,onClose,onSaved}:{initial:Partial<Supplier>;onClose:()=>void;onSaved:()=>void}) {
  const [fields,setFields] = useState({name:initial.name || '',phone:initial.phone || '',email:initial.email || '',address:initial.address || '',notes:initial.notes || '',payment_terms_days:String(initial.payment_terms_days || 0),is_active:initial.is_active ?? true});
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [pending,setPending] = useState<Payload | null>(null);
  const submit = async (e:React.FormEvent) => { e.preventDefault(); if (busy) return;
    if (!fields.name.trim() || !/^\d+$/.test(fields.payment_terms_days) || Number(fields.payment_terms_days) > 365) { setError('Isi nama dan tempo pembayaran 0 sampai 365 hari.'); return; }
    const body:Payload=pending || {...fields,name:fields.name.trim(),payment_terms_days:Number(fields.payment_terms_days),...(initial.id ? {row_version:initial.row_version} : {client_request_id:crypto.randomUUID()})};
    if (!initial.id) delete body.is_active;
    setBusy(true); setError(''); const result=initial.id ? await updateSupplier(initial.id,body) : await createSupplier(body); setBusy(false);
    if (result.success) onSaved(); else { setError(result.message); setPending(result.uncertain && !initial.id ? body : null); }
  };
  return <InventoryDialog title={initial.id ? 'Ubah supplier' : 'Tambah supplier'} busy={busy} onClose={onClose}><form className="finance-form p-form" onSubmit={submit}>
    <fieldset disabled={busy || !!pending} className="p-fields">{(['name','phone','email','address','notes'] as const).map((name,index) => <label key={name}>{['Nama supplier','Nomor HP atau WA','Email (opsional)','Alamat (opsional)','Catatan (opsional)'][index]}<input aria-label={['Nama supplier','Nomor HP atau WA','Email supplier','Alamat supplier','Catatan supplier'][index]} type={name === 'email' ? 'email' : 'text'} maxLength={name === 'name' ? 120 : 1000} required={name === 'name'} value={fields[name]} onChange={e => setFields(old => ({...old,[name]:e.target.value}))} /></label>)}
      <label>Tempo pembayaran (hari)<input aria-label="Tempo pembayaran" type="number" min="0" max="365" step="1" required value={fields.payment_terms_days} onChange={e => setFields(old => ({...old,payment_terms_days:e.target.value}))} /></label><p>Tempo dipakai untuk nota baru yang belum lunas. Jika 0, nota utang memakai 7 hari.</p>
      {initial.id && <label className="f-checkbox"><input type="checkbox" checked={fields.is_active} onChange={e => setFields(old => ({...old,is_active:e.target.checked}))} /> Supplier aktif untuk pembelian baru</label>}
    </fieldset>{pending && <p className="f-notice">Hasil sebelumnya belum pasti. Periksa penyimpanan supplier dengan permintaan yang sama.</p>}{error && <p className="f-notice f-error" role="alert">{error}</p>}
    <div className="f-form-actions"><button className="f-button" type="button" disabled={busy} onClick={onClose}>Tutup</button><button className="f-button f-primary" disabled={busy} type="submit">{busy ? 'Menyimpan…' : pending ? 'Periksa penyimpanan supplier' : 'Simpan supplier'}</button></div>
  </form></InventoryDialog>;
}
