'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { getAccountAccess } from '@/app/actions/accounts';
import { getOperationalStock, recordOperationalStock } from '@/app/actions/pos';
import '../keuangan/finance.css';
import { POS_WORKSPACE_PERMISSIONS } from '@/lib/pos-access';

export default function OperationalPage() {
  const [access, setAccess] = useState<any>(null), [outletId, setOutletId] = useState(''), [data, setData] = useState<any>(null);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [edit, setEdit] = useState<{ kind: 'product' | 'ingredient'; row: any; action: 'receive' | 'count' } | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const generation = useRef(0), form = useRef<HTMLFormElement>(null);
  const allows = (permission: string) => access?.permissions.includes(permission);

  async function load(selected = outletId) {
    const current = ++generation.current;
    setLoading(true); setError(''); setData(null); setEdit(null);
    const result = await getAccountAccess();
    if (current !== generation.current) return;
    if (!result.success) { setError(result.message); setLoading(false); return; }
    setAccess(result.data);
    const id = result.data.outlets.some((o: any) => o.id === selected) ? selected : result.data.outlets[0]?.id || '';
    setOutletId(id);
    if (id && result.data.permissions.includes('stock.view')) {
      const stock = await getOperationalStock(id);
      if (current !== generation.current) return;
      if (stock.success) { setData(stock.data); setUncertain(false); } else setError(stock.message);
    }
    setLoading(false);
  }
  useEffect(() => { void load(); return () => { generation.current++; }; }, []);
  useEffect(() => { if (edit) form.current?.querySelector<HTMLInputElement>('input')?.focus(); }, [edit]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!edit || busy || uncertain) return;
    const quantity = Number(new FormData(event.currentTarget).get('quantity'));
    const target = edit;
    setBusy(true); setError(''); setNotice('');
    const result = await recordOperationalStock(target.kind, target.row.id, outletId, target.action, quantity);
    if (result.success) { setEdit(null); setNotice('Stok tersimpan'); await load(); }
    else { setError(result.message); setUncertain(result.uncertain); }
    setBusy(false);
  }
  function open(kind: 'product' | 'ingredient', row: any, action: 'receive' | 'count') { if (uncertain) return; setError(''); setEdit({ kind, row, action }); }

  return <div className="finance-workspace">
    <div className="finance-heading"><div><h1>Operasional toko</h1><p>Gunakan outlet dan tindakan yang diizinkan untuk akun Anda.</p></div><button className="f-button" disabled={busy || loading} onClick={() => { setEdit(null); void load(); }}>Muat ulang akses dan stok</button></div>
    {error && <p className="f-notice f-error" role="alert">{error}</p>}{notice && <p className="f-notice" role="status">{notice}</p>}
    {loading ? <p role="status">Memuat operasional…</p> : !access ? <p>Akses belum dapat dimuat. Gunakan tombol muat ulang.</p> : <>
      <label className="finance-form">Outlet<select aria-label="Outlet" value={outletId} disabled={busy} onChange={e => { setEdit(null); setNotice(''); void load(e.target.value); }}>{access.outlets.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      {!access.outlets.length && <p>Belum ada outlet aktif dalam akses akun ini. Hubungi pemilik.</p>}
      {access.permissions.some((p: string) => POS_WORKSPACE_PERMISSIONS.includes(p) && !p.startsWith('stock.')) && <section className="f-panel"><h2>Aplikasi POS</h2><p>Gunakan kasir, riwayat, sesi kas, refund atau dapur sesuai izin akun melalui aplikasi POS. Akun staf dengan izin baru perlu koneksi internet. Antrean transaksi lama tetap disimpan jika izin berubah.</p><Link className="f-button" href="/download">Unduh aplikasi POS</Link></section>}
      {allows('stock.view') && data && <section className="f-panel"><h2>Stok {data.outlet.name}</h2><p>{data.outlet.stock_mode === 'recipe' ? 'Jumlah menu dihitung dari bahan resep. Terima bahan dalam satuan yang tercatat.' : 'Stok produk dipakai bersama oleh outlet satu brand. Tambah saat barang diterima; opname mencatat jumlah fisik dan selisihnya.'}</p>
        {!data.products.length && !data.ingredients.length && <p>Belum ada barang untuk outlet ini.</p>}
        {[{ kind: 'product' as const, title: 'Menu', rows: data.products }, { kind: 'ingredient' as const, title: 'Bahan resep', rows: data.ingredients }].filter(group => group.rows.length).map(group => <div key={group.kind}><h3>{group.title}</h3><ul className="pos-stock-list">{group.rows.map((row: any) => <li key={row.id}>
          <div><strong>{row.name}</strong><p>{group.kind === 'ingredient' ? row.current_stock == null ? 'Stok belum dicatat' : `${row.current_stock.toLocaleString('id-ID')} ${row.base_unit}` : row.stock_enabled ? `${row.stock_qty.toLocaleString('id-ID')} ${data.outlet.stock_mode === 'recipe' ? 'porsi' : 'pcs'}` : 'Stok tidak dilacak'}</p></div>
          <div className="pos-stock-actions">{allows('stock.receive') && (group.kind === 'ingredient' || row.stock_enabled && data.outlet.stock_mode === 'simple') && <button className="f-button" disabled={busy || uncertain} onClick={() => open(group.kind, row, 'receive')}>Terima barang<span className="sr-only"> {row.name}</span></button>}{allows('stock.adjust') && group.kind === 'product' && row.stock_enabled && data.outlet.stock_mode === 'simple' && <button className="f-button" disabled={busy || uncertain} onClick={() => open(group.kind, row, 'count')}>Stok opname<span className="sr-only"> {row.name}</span></button>}</div>
        </li>)}</ul></div>)}
      </section>}
      {!allows('stock.view') && <p>Izin melihat stok belum diberikan untuk akun ini.</p>}
      {edit && <section className="f-panel"><h2>{edit.action === 'receive' ? 'Terima barang' : 'Stok opname'}: {edit.row.name}</h2><p>{edit.action === 'receive' ? 'Isi jumlah barang yang baru diterima.' : 'Isi jumlah fisik saat ini. Selisih stok tercatat sebagai hasil opname.'}</p>
        <form ref={form} className="finance-form" onSubmit={submit} aria-busy={busy}><label>Jumlah ({edit.kind === 'ingredient' ? edit.row.base_unit : 'pcs'})<input name="quantity" type="number" min={edit.action === 'receive' ? edit.kind === 'ingredient' ? '0.001' : '1' : '0'} step={edit.kind === 'ingredient' ? 'any' : '1'} required disabled={busy || uncertain} /></label>
          {uncertain ? <p>Permintaan belum terkonfirmasi. Muat ulang akses dan stok, lalu periksa jumlah sebelum membuat catatan baru.</p> : <button className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan…' : 'Simpan stok'}</button>}
          <button type="button" className="f-button" disabled={busy} onClick={() => setEdit(null)}>Tutup</button>
        </form>
      </section>}
    </>}
    <style jsx>{`.finance-workspace{grid-template-columns:minmax(0,1fr)}.finance-heading>div{min-width:0}h1,h2,h3{overflow-wrap:anywhere}.pos-stock-list{list-style:none;padding:0}.pos-stock-list li{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;border-bottom:1px solid var(--border,#d5cdc4)}.pos-stock-list p{margin:4px 0}.pos-stock-actions{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:600px){.pos-stock-list li{align-items:flex-start;flex-direction:column}.pos-stock-actions{width:100%}}`}</style>
  </div>;
}
