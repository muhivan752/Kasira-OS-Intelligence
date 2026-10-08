'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { InventoryDialog } from '@/components/inventory-dialog';
import { getCustomerWorkspace, getCustomerWorkspaceDetail, saveCustomerWorkspace, addCustomerWorkspaceNote } from '@/app/actions/customers';
import type { CustomerList, CustomerDetail, CustomerFilters, CustomerSave, CustomerNote } from '@/lib/customers';
import { customerDate, customerCsv } from '@/lib/customers';
import { money, jakartaDate } from '@/lib/finance';
import '../keuangan/finance.css';
import './customers.css';

const initialFilters: CustomerFilters = { search: '', segment: '', sort: 'last_visit', skip: 0 };
const segments = [['', 'Semua pelanggan'], ['repeat', 'Belanja berulang'], ['lapse', 'Tidak belanja 30 hari'], ['new', 'Belanja pertama 30 hari'], ['unspent', 'Belum belanja']];
const sorts = [['last_visit', 'Terakhir belanja'], ['spent', 'Total belanja terbesar'], ['visits', 'Transaksi terbanyak'], ['newest', 'Terbaru dicatat'], ['name', 'Nama A sampai Z']];
type Pending = { id?: string; profile?: CustomerSave; note?: CustomerNote };
const pendingKey = 'selaris-customer-pending';

export default function CustomersPage() {
  const [filters, setFilters] = useState(initialFilters), [search, setSearch] = useState('');
  const [data, setData] = useState<CustomerList | null>(null), [loading, setLoading] = useState(true);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<string | null>(null), [creating, setCreating] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const storageKey = useRef<string | null>(null);
  useEffect(() => { const timer = setTimeout(() => setFilters(v => ({ ...v, search, skip: 0 })), 300); return () => clearTimeout(timer); }, [search]);
  useEffect(() => {
    let current = true; setLoading(true); setError(''); setData(null);
    getCustomerWorkspace(filters).then(result => { if (!current) return;
      if (result.success) {
        const key = `${pendingKey}:${result.data.workspace_key}`;
        if (storageKey.current !== key) {
          storageKey.current = key; setPending(null);
          try { const raw = sessionStorage.getItem(key); if (raw) { const saved = JSON.parse(raw); if (saved.profile?.client_request_id || saved.note?.client_request_id) setPending(saved); } } catch { /* Browser storage can be disabled. */ }
        }
        setData(result.data);
      } else setError(result.message); setLoading(false);
    });
    return () => { current = false; };
  }, [filters, revision]);
  const persist = (value: Pending | null) => { setPending(value); try { if (storageKey.current) { if (value) sessionStorage.setItem(storageKey.current, JSON.stringify(value)); else sessionStorage.removeItem(storageKey.current); } } catch { /* Retain the request in memory for this page. */ } };
  const saved = (message: string) => { persist(null); setNotice(message); setRevision(v => v + 1); };
  const change = (key: 'segment' | 'sort', value: string) => setFilters(v => ({ ...v, [key]: value, skip: 0 }));
  const exportPage = async () => { if (!data) return; const result = await getCustomerWorkspace(filters, true);
    if (!result.success) { setError(result.message); return; }
    const url = URL.createObjectURL(new Blob([customerCsv(result.data)], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a'); link.href = url; link.download = `pelanggan-halaman-${Math.floor(data.skip / 50) + 1}-${jakartaDate()}.csv`; link.click(); URL.revokeObjectURL(url); };
  return <div className="finance-workspace customer-workspace">
    <div className="finance-heading"><div><h1>Data pelanggan</h1><p className="f-explanation">Kontak, kebiasaan belanja, dan catatan layanan dalam satu profil.</p></div>
      {data?.can_manage !== false && <button className="f-button f-primary" data-inventory-add disabled={Boolean(pending) || !storageKey.current} onClick={() => setCreating(true)}>Tambah pelanggan</button>}</div>
    <p className="f-footnote">Profil dan catatan pelanggan dipakai bersama bisnis. {data?.scope === 'allowed_outlets' ? 'Riwayat dan nilai belanja hanya dari outlet yang diizinkan.' : 'Riwayat dari semua outlet bisnis.'} Transaksi tanpa pelanggan terpilih tidak masuk riwayat pelanggan.</p>
    {pending && <div className="f-notice" role="status"><p>Ada permintaan penyimpanan yang belum selesai. Periksa permintaan yang sama agar tidak tercatat dua kali.</p>
      {data?.can_manage !== false && <button className="f-button" onClick={() => { if (pending.id) setSelected(pending.id); else setCreating(true); }}>Lanjutkan penyimpanan</button>}</div>}
    {notice && <p className="f-notice" role="status">{notice}</p>}
    <div className="finance-toolbar"><label>Cari pelanggan<input type="search" maxLength={120} placeholder="Nama, nomor HP, atau email" value={search} onChange={e => setSearch(e.target.value)} /></label>
      <label>Kelompok pelanggan<select value={filters.segment} onChange={e => change('segment', e.target.value)}>{segments.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Urutkan<select value={filters.sort} onChange={e => change('sort', e.target.value)}>{sorts.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <button className="f-button" disabled={loading} onClick={() => setRevision(v => v + 1)}>Muat ulang</button></div>
    {loading ? <p className="f-notice" role="status">Memuat data pelanggan...</p> : error ? <div className="f-notice f-error" role="alert"><p>{error}</p><button className="f-button" data-inventory-retry onClick={() => setRevision(v => v + 1)}>Coba lagi</button></div> : data && <>
      <section className="f-panel"><h2>Ringkasan bisnis</h2><p className="f-footnote">Semua pelanggan, terlepas dari filter daftar.</p>
        <div className="c-summary"><div><p>Pelanggan tercatat</p><strong>{data.summary.total}</strong></div><div><p>Belanja berulang</p><strong>{data.summary.repeat}</strong></div><div><p>Total nota lunas</p><strong>{money(data.summary.spent)}</strong></div></div>
        <p className="f-footnote">{data.history_note} Diperbarui {customerDate(data.generated_at)} (WIB).</p></section>
      <section className="f-panel"><div className="f-report-title"><div><h2>Daftar pelanggan</h2><p>{data.total} pelanggan sesuai filter.</p></div>{data.can_export !== false && <button className="f-button" disabled={!data.items.length} onClick={() => void exportPage()}>Ekspor halaman CSV</button>}</div>
        {!data.items.length ? <div className="f-empty"><h3>{data.summary.total ? 'Tidak ada pelanggan sesuai filter' : 'Belum ada pelanggan tercatat'}</h3><p>Tambahkan kontak, atau pilih pelanggan saat kasir mencatat transaksi.</p>
          {(search || filters.segment) && <button className="f-button" onClick={() => { setSearch(''); setFilters(initialFilters); }}>Reset filter</button>}</div>
          : <ul className="c-list">{data.items.map(c => <li key={c.id}><div><h3>{c.name}</h3><p>{c.phone || 'Nomor HP belum diisi'}</p>{c.email && <p className="f-footnote">{c.email}</p>}</div>
            <div className="c-value"><p>{c.total_visits} transaksi lunas · {money(c.total_spent)}</p><p className="f-footnote">Terakhir: {customerDate(c.last_visit_at)}</p></div>
            <button className="f-button" disabled={Boolean(pending && pending.id !== c.id)} onClick={() => setSelected(c.id)} aria-label={`Buka profil ${c.name}`}>Buka profil</button></li>)}</ul>}
        {data.total > 0 && <div className="c-pager"><p>{data.skip + (data.items.length ? 1 : 0)} sampai {data.skip + data.items.length} dari {data.total}</p><div>
          <button className="f-button" disabled={filters.skip === 0} onClick={() => setFilters(v => ({ ...v, skip: Math.max(0, v.skip - 50) }))}>Sebelumnya</button>
          <button className="f-button" disabled={data.skip + data.items.length >= data.total} onClick={() => setFilters(v => ({ ...v, skip: v.skip + 50 }))}>Berikutnya</button></div></div>}</section>
    </>}
    {creating && <ProfileForm pending={pending?.profile && !pending.id ? pending : null} onPending={persist} onClose={() => setCreating(false)} onSaved={message => { saved(message); setCreating(false); }} />}
    {selected && <CustomerProfile id={selected} pending={pending?.id === selected ? pending : null} onPending={persist} onClose={() => setSelected(null)} onSaved={saved} />}
  </div>;
}

function ProfileForm({ customer, pending, onPending, onClose, onSaved }: { customer?: CustomerDetail; pending: Pending | null; onPending: (value: Pending | null) => void; onClose: () => void; onSaved: (message: string) => void }) {
  const preset = pending?.profile || customer;
  const [name, setName] = useState(preset?.name || ''), [phone, setPhone] = useState(preset?.phone || ''), [email, setEmail] = useState(preset?.email || '');
  const [notes, setNotes] = useState(preset?.notes || ''), [birthday, setBirthday] = useState(preset?.birthday || '');
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const frozen = Boolean(pending?.profile);
  const submit = async (event: React.FormEvent) => { event.preventDefault(); if (busy) return; setBusy(true); setError('');
    const payload: CustomerSave = pending?.profile || { client_request_id: crypto.randomUUID(), row_version: customer?.row_version,
      name: name.trim(), phone: phone.trim() || null, email: email.trim() || null, notes: notes.trim() || null, birthday: birthday || null, wa_marketing_consent: Boolean(preset?.wa_marketing_consent) && phone.trim() === (preset?.phone || '').trim() };
    onPending({ id: customer?.id, profile: payload });
    const result = await saveCustomerWorkspace(payload, customer?.id);
    setBusy(false); if (result.success) onSaved(result.message || 'Profil pelanggan disimpan'); else { setError(result.message); if (!result.uncertain) onPending(null); }
  };
  return <InventoryDialog title={customer ? 'Edit profil pelanggan' : 'Tambah pelanggan'} busy={busy} onClose={onClose}>
    <form className="finance-form" onSubmit={submit}><p>Isi informasi yang sudah dikonfirmasi pelanggan. Kolom selain nama boleh dikosongkan.</p>
      {frozen && <p className="f-notice">Periksa penyimpanan data yang sama sebelum mengubah isinya.</p>}
      {error && <p className="f-notice f-error" role="alert">{error}</p>}
      <label>Nama pelanggan<input autoFocus required maxLength={120} value={name} disabled={busy || frozen} onChange={e => setName(e.target.value)} /></label>
      <div className="f-field-grid"><label>Nomor HP<input type="tel" maxLength={40} placeholder="08 atau +62" value={phone} disabled={busy || frozen} onChange={e => setPhone(e.target.value)} /></label>
        <label>Email<input type="email" maxLength={254} value={email} disabled={busy || frozen} onChange={e => setEmail(e.target.value)} /></label></div>
      <label>Tanggal lahir<input type="date" max={jakartaDate()} value={birthday} disabled={busy || frozen} onChange={e => setBirthday(e.target.value)} /></label>
      <label>Preferensi / catatan profil<textarea maxLength={2000} value={notes} disabled={busy || frozen} onChange={e => setNotes(e.target.value)} /></label>

      <p className="f-footnote">Menyimpan izin ini tidak mengirim pesan. Perubahan nomor perlu persetujuan kembali.</p>
      <div className="f-form-actions"><button type="button" className="f-button" disabled={busy} onClick={onClose}>Tutup</button><button className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan...' : frozen ? 'Periksa penyimpanan profil' : 'Simpan profil'}</button></div>
    </form></InventoryDialog>;
}

function CustomerProfile({ id, pending, onPending, onClose, onSaved }: { id: string; pending: Pending | null; onPending: (value: Pending | null) => void; onClose: () => void; onSaved: (message: string) => void }) {
  const [data, setData] = useState<CustomerDetail | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(true);
  const [skip, setSkip] = useState(0), [revision, setRevision] = useState(0), [editing, setEditing] = useState(Boolean(pending?.profile));
  const [body, setBody] = useState(pending?.note?.body || ''), [kind, setKind] = useState<'note' | 'complaint'>(pending?.note?.kind || 'note');
  const [busy, setBusy] = useState(false), [noteError, setNoteError] = useState(''), [notice, setNotice] = useState('');
  const request = useRef(0);
  const load = useCallback(async () => { const serial = ++request.current; setLoading(true); setError(''); setData(null);
    const result = await getCustomerWorkspaceDetail(id, skip); if (request.current !== serial) return;
    if (result.success) setData(result.data); else setError(result.message); setLoading(false);
  }, [id, skip]);
  useEffect(() => { load(); return () => { request.current++; }; }, [load, revision]);
  const saveNote = async (event: React.FormEvent) => { event.preventDefault(); if (busy) return; setBusy(true); setNoteError('');
    const payload = pending?.note || { client_request_id: crypto.randomUUID(), body: body.trim(), kind };
    onPending({ id, note: payload }); const result = await addCustomerWorkspaceNote(id, payload); setBusy(false);
    if (result.success) { onPending(null); setBody(''); setNotice('Catatan pelanggan disimpan'); setRevision(v => v + 1); onSaved('Catatan pelanggan disimpan'); }
    else { setNoteError(result.message); if (!result.uncertain) onPending(null); }
  };
  if (editing && data && data.can_manage !== false) return <ProfileForm customer={data} pending={pending} onPending={onPending} onClose={() => { if (pending?.profile) onClose(); else setEditing(false); }} onSaved={message => { setEditing(false); setRevision(v => v + 1); onSaved(message); }} />;
  return <InventoryDialog title="Profil pelanggan" busy={busy} onClose={onClose}><div className="finance-form c-profile">
    {loading ? <p role="status">Memuat profil pelanggan...</p> : error ? <div className="f-notice f-error" role="alert"><p>{error}</p><button className="f-button" onClick={load}>Coba lagi</button></div> : data && <>
      <section><div className="f-report-title"><div><h3>{data.name}</h3><p>{data.phone || 'Nomor HP belum diisi'}</p>{data.email && <p>{data.email}</p>}</div>{data.can_manage !== false && <button className="f-button" disabled={Boolean(pending)} onClick={() => setEditing(true)}>Edit profil</button>}</div>
        <p>Tanggal lahir: {customerDate(data.birthday)}</p>
        {data.notes && <p className="f-notice c-pre">{data.notes}</p>}
        <div className="c-summary"><div><p>Transaksi lunas</p><strong>{data.total_visits}</strong></div><div><p>Total nota lunas</p><strong>{money(data.total_spent)}</strong></div><div><p>Rata-rata nota</p><strong>{money(data.avg_spent)}</strong></div><div><p>Terakhir belanja</p><strong>{customerDate(data.last_visit_at)}</strong></div></div>
        <p className="f-footnote">{data.scope === 'allowed_outlets' ? 'Outlet yang diizinkan.' : 'Semua outlet bisnis.'} Nilai nota berstatus lunas sebelum pengurangan refund; satu nota dihitung satu transaksi.</p></section>
      <section><h3>Produk yang sering dibeli</h3>{data.favourites.length ? <ul>{data.favourites.map(f => <li key={f.id}>{f.name} · {f.qty} pcs</li>)}</ul> : <p>Belum ada produk tercatat dari transaksi lunas.</p>}<p className="f-footnote">Berdasarkan jumlah item di seluruh riwayat nota lunas. Nama mengikuti katalog produk saat ini.</p></section>
      <section><h3>Riwayat transaksi lunas</h3>{data.orders.length ? <ul className="c-history">{data.orders.map(o => <li key={o.id}><p>{o.order_number} · {customerDate(o.created_at)} (WIB)</p><p>{o.items.map(i => `${i.name} ×${i.qty}`).join(', ') || 'Item tidak tersedia'}</p><strong>{money(o.total_amount)}</strong></li>)}</ul> : <p>Belum ada transaksi lunas di halaman ini.</p>}
        {data.total_visits > 20 && <div className="c-pager"><p>{skip + (data.orders.length ? 1 : 0)} sampai {skip + data.orders.length} dari {data.total_visits}</p><div><button className="f-button" disabled={!skip || busy} onClick={() => setSkip(v => Math.max(0, v - 20))}>Transaksi sebelumnya</button><button className="f-button" disabled={skip + data.orders.length >= data.total_visits || busy} onClick={() => setSkip(v => v + 20)}>Transaksi berikutnya</button></div></div>}</section>
      <section><h3>Catatan layanan</h3><p className="f-footnote">Catatan staf melengkapi konteks pelanggan dan terpisah dari riwayat transaksi.</p>
        {notice && <p role="status">{notice}</p>}{noteError && <p className="f-notice f-error" role="alert">{noteError}</p>}
        {data.can_manage !== false && <form className="finance-form" onSubmit={saveNote}><label>Jenis catatan<select value={kind} disabled={busy || Boolean(pending)} onChange={e => setKind(e.target.value as 'note' | 'complaint')}><option value="note">Catatan</option><option value="complaint">Keluhan</option></select></label>
          <label>Catatan baru<textarea required maxLength={500} value={body} disabled={busy || Boolean(pending)} onChange={e => setBody(e.target.value)} /></label>
          <button className="f-button" disabled={busy || (!body.trim() && !pending?.note)}>{busy ? 'Menyimpan...' : pending?.note ? 'Periksa penyimpanan catatan' : 'Simpan catatan'}</button></form>}
        {data.timeline.length ? <ul className="c-history">{data.timeline.map(n => <li key={n.id}><p className="f-footnote">{n.kind === 'complaint' ? 'Keluhan' : n.kind === 'consent' ? 'Izin promo' : 'Catatan aktivitas'} · {customerDate(n.created_at)} (WIB)</p><p className="c-pre">{n.body}</p></li>)}</ul> : <p>Belum ada catatan layanan.</p>}
        <p className="f-footnote">Menampilkan paling banyak {data.timeline_limit} aktivitas terakhir.</p></section>
    </>}
  </div></InventoryDialog>;
}
