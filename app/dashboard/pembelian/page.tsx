'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Plus, RefreshCw } from 'lucide-react';
import { InventoryDialog } from '@/components/inventory-dialog';
import { PurchaseForm, PurchaseDetail, SupplierForm } from '@/components/purchase-forms';
import { getPurchasingSetup, getPurchasingData, deleteSupplier } from '@/app/actions/api';
import type { PurchaseData, PurchaseSetup, Supplier } from '@/lib/purchasing';
import { purchaseDate } from '@/lib/purchasing';
import { jakartaDate, money, monthName } from '@/lib/finance';
import '../keuangan/finance.css';
import './purchasing.css';

export default function PembelianPage() {
  const [setup, setSetup] = useState<PurchaseSetup | null>(null), [outletId, setOutletId] = useState('');
  const [month, setMonth] = useState(() => jakartaDate().slice(0, 7)), [unpaid, setUnpaid] = useState(false);
  const [search, setSearch] = useState(''), [query, setQuery] = useState(''), [page, setPage] = useState(0);
  const [tab, setTab] = useState<'nota' | 'supplier'>('nota'), [data, setData] = useState<PurchaseData | null>(null);
  const [loading, setLoading] = useState(true), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0), [boot, setBoot] = useState(0), request = useRef(0);
  const [nota, setNota] = useState(false), [detail, setDetail] = useState<string | null>(null);
  const [supplierForm, setSupplierForm] = useState<Partial<Supplier> | null>(null), [removing, setRemoving] = useState<Supplier | null>(null);
  const [busy, setBusy] = useState(false), [removeError, setRemoveError] = useState('');
  useEffect(() => {
    let active = true; setLoading(true); setError('');
    void getPurchasingSetup().then(result => {
      if (!active) return;
      if (!result.success) { setError(result.message); setLoading(false); return; }
      setSetup(result.data);
      setOutletId(result.data.outlets.find(o => o.id === result.data.selectedOutletId)?.id || result.data.outlets[0]?.id || '');
      if (!result.data.outlets.length) setLoading(false);
    });
    return () => { active = false; };
  }, [boot]);
  useEffect(() => {
    if (!outletId) return;
    const current = ++request.current; setLoading(true); setError(''); setData(null);
    void getPurchasingData(outletId, month, { month: unpaid ? undefined : month, unpaidOnly: unpaid, search: query, skip: page * 50 }).then(result => {
      if (request.current !== current) return;
      if (result.success) setData(result.data); else setError(result.message);
      setLoading(false);
    });
    return () => { request.current++; };
  }, [outletId, month, unpaid, query, page, refresh]);
  const outlet = setup?.outlets.find(o => o.id === outletId);
  const saved = (message: string) => { setNotice(message); setRefresh(n => n + 1); };
  const retry = () => { if (!setup) setBoot(n => n + 1); else setRefresh(n => n + 1); };
  return <div className="finance-workspace purchase-workspace">
    <div className="finance-heading"><div><h1>Pembelian</h1><p>Catat barang yang sudah diterima, periksa nota, dan pantau utang supplier.</p></div>
      <button className="f-button f-primary" data-inventory-add disabled={!data || loading} onClick={() => setNota(true)}><Plus size={18} aria-hidden="true" /> Catat nota</button></div>
    {notice && <p className="f-notice" role="status">{notice}</p>}
    {setup && setup.outlets.length > 0 && <div className="finance-toolbar">
      <label>Outlet<select aria-label="Outlet" value={outletId} onChange={e => { setOutletId(e.target.value); setPage(0); setNotice(''); }}>
        {setup.outlets.map(o => <option value={o.id} key={o.id}>{o.name}</option>)}</select></label>
      <label>Bulan penerimaan<input aria-label="Bulan penerimaan" type="month" min="2000-01" max={jakartaDate().slice(0, 7)} value={month} onChange={e => {
        if (/^(20\d\d|[3-9]\d{3})-(0[1-9]|1[0-2])$/.test(e.target.value) && e.target.value <= jakartaDate().slice(0, 7)) { setMonth(e.target.value); setPage(0); }
      }} /></label>
      <button className="f-button" disabled={loading} data-inventory-retry onClick={retry}><RefreshCw size={18} aria-hidden="true" /> Muat ulang</button>
    </div>}
    {loading && <p role="status" className="f-panel">Memuat pembelian…</p>}
    {!loading && error && <div role="alert" className="f-notice f-error"><p>{error}</p><button className="f-button" onClick={retry}>Coba lagi</button></div>}
    {!loading && setup?.outlets.length === 0 && <div className="f-panel"><h2>Belum ada outlet</h2><p>Lengkapi outlet sebelum mencatat pembelian.</p><Link href="/dashboard/settings">Buka pengaturan</Link></div>}
    {!loading && data && outlet && <>
      <div className="p-summary f-panel"><div><p className="f-eyebrow">Barang diterima · {monthName(month)}</p><h2>Total nota bulan ini</h2><p className="f-secondary-amount">{money(data.summary.month_total)}</p><p>{data.summary.month_count} nota di {outlet.name}. Nilai belanja ini berbeda dari pembayaran bulan ini.</p></div>
        <div><h2>Utang supplier saat ini</h2><p className="f-secondary-amount">{money(data.summary.outstanding_total)}</p><p>{data.summary.outstanding_count} nota belum lunas, dari semua bulan.</p>
          <p>{data.summary.overdue_count} nota lewat jatuh tempo · <strong>{money(data.summary.overdue_total)}</strong></p>
          {data.summary.next_due_at && <p>Tempo terdekat: {purchaseDate(data.summary.next_due_at)} · {data.summary.next_due_supplier || 'Tanpa supplier'}</p>}
          <button className="f-button" onClick={() => { setUnpaid(true); setTab('nota'); setPage(0); setSearch(''); setQuery(''); }}>Periksa nota belum lunas</button></div></div>
      <div className="p-tabs" aria-label="Bagian pembelian"><button className="f-button" aria-pressed={tab === 'nota'} onClick={() => setTab('nota')}>Nota belanja</button><button className="f-button" aria-pressed={tab === 'supplier'} onClick={() => setTab('supplier')}>Supplier</button></div>
      {tab === 'nota' ? <section className="f-panel"><h2>{unpaid ? 'Nota belum lunas dari semua bulan' : `Nota diterima ${monthName(month)}`}</h2>
        <form className="finance-toolbar p-filter" onSubmit={e => { e.preventDefault(); setQuery(search.trim()); setPage(0); }}>
          <label>Cari nota<input aria-label="Cari nota" maxLength={120} value={search} onChange={e => setSearch(e.target.value)} placeholder="Nomor nota atau supplier" /></label>
          <label>Tampilkan<select aria-label="Tampilkan" value={unpaid ? 'unpaid' : 'month'} onChange={e => { setUnpaid(e.target.value === 'unpaid'); setPage(0); }}><option value="month">Semua nota bulan terpilih</option><option value="unpaid">Belum lunas, semua bulan</option></select></label>
          <button className="f-button" type="submit">Cari</button>
        </form>
        {!data.purchases.length ? <div className="f-empty"><h3>{query || unpaid ? 'Tidak ada nota yang sesuai' : 'Belum ada nota pada bulan ini'}</h3><p>{query || unpaid ? 'Ubah pencarian atau pilihan nota untuk melihat catatan lainnya.' : 'Catat nota setelah barang tiba. Rencana pembelian belum menambah stok.'}</p></div>
          : <ul className="p-notas">{data.purchases.map(p => <li key={p.id}><button className="p-nota" onClick={() => setDetail(p.id)}>
            <div><strong>{p.supplier_name || 'Tanpa supplier'}</strong><p>{p.po_number}{p.invoice_no ? ` · ${p.invoice_no}` : ''}</p><p>{purchaseDate(p.received_at)} · {p.items.length} baris · {p.items.slice(0, 3).map(i => i.name).join(', ')}</p></div>
            <div className="p-nota-money"><strong>{money(p.total_amount)}</strong><p className={Number(p.outstanding_amount) > 0 ? 'p-debt' : ''}>{Number(p.outstanding_amount) > 0 ? `Sisa ${money(p.outstanding_amount)}` : 'Lunas'}</p>
              {Number(p.outstanding_amount) > 0 && p.due_at && <p>{new Date(p.due_at) < new Date() ? 'Lewat tempo' : 'Tempo'} {purchaseDate(p.due_at)}</p>}</div>
          </button></li>)}</ul>}
        <div className="p-pagination"><p>Halaman {page + 1} · {data.purchases.length} nota ditampilkan</p><div className="f-form-actions"><button className="f-button" disabled={page === 0} onClick={() => setPage(n => n - 1)}>Sebelumnya</button><button className="f-button" disabled={!data.hasNext} onClick={() => setPage(n => n + 1)}>Berikutnya</button></div></div>
      </section> : <section className="f-panel"><div className="f-report-title"><div><h2>Supplier bisnis</h2><p>Daftar supplier dipakai bersama. Total belanja dan utang di bawah khusus {outlet.name}, dari semua bulan.</p></div><button className="f-button" onClick={() => setSupplierForm({})}>Tambah supplier</button></div>
        {!data.suppliers.length ? <p className="f-empty">Belum ada supplier. Nota juga bisa dicatat tanpa supplier.</p> : <ul className="p-suppliers">{data.suppliers.map(s => <li key={s.id}><div><h3>{s.name}{!s.is_active && ' (nonaktif)'}</h3><p>{s.phone || 'Nomor belum diisi'} · tempo {s.payment_terms_days} hari</p><p>{s.purchase_count} nota · belanja {money(s.purchase_total)} · utang {money(s.outstanding_total)}</p></div>
          <div className="f-form-actions"><button className="f-button" aria-label={`Ubah supplier ${s.name}`} onClick={() => setSupplierForm(s)}>Ubah</button><button className="f-button f-delete" aria-label={`Hapus supplier ${s.name}`} onClick={() => { setRemoveError(''); setRemoving(s); }}>Hapus</button></div></li>)}</ul>}
      </section>}
      <p className="f-footnote">Tanggal memakai WIB. Pembayaran nota tercermin di <Link href="/dashboard/keuangan">Keuangan</Link>. Belanja stok menjadi HPP saat barang terjual; baris biaya di nota menjadi pengeluaran.</p>
    </>}
    {nota && outlet && setup && data && <PurchaseForm outlet={outlet} isPro={setup.isPro} suppliers={data.suppliers} onClose={() => setNota(false)} onSaved={p => { setNota(false); saved(`Nota ${p.po_number} dan penerimaan barang sudah dicatat.`); }} />}
    {detail && <PurchaseDetail id={detail} onClose={() => setDetail(null)} onSaved={() => saved('Pembayaran utang dicatat. Stok tidak bertambah dari pembayaran.')} />}
    {supplierForm && <SupplierForm initial={supplierForm} onClose={() => setSupplierForm(null)} onSaved={() => { setSupplierForm(null); saved('Supplier disimpan.'); }} />}
    {removing && <InventoryDialog title="Hapus supplier" busy={busy} onClose={() => setRemoving(null)}><div className="finance-form"><p>Hapus {removing.name} dari daftar? Nota dan utang yang sudah tercatat tetap tersimpan. Untuk menghentikan pembelian sementara, Anda bisa menonaktifkannya lewat Ubah.</p>
      {removeError && <p role="alert" className="f-notice f-error">{removeError}</p>}<div className="f-form-actions"><button className="f-button" disabled={busy} onClick={() => setRemoving(null)}>Batal</button><button className="f-button f-delete" disabled={busy} onClick={async () => { setBusy(true); const result = await deleteSupplier(removing.id); setBusy(false); if (result.success) { setRemoving(null); saved('Supplier dihapus dari daftar.'); } else setRemoveError(result.message); }}>Hapus supplier</button></div></div></InventoryDialog>}
  </div>;
}
