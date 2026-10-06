'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Download, Plus, RefreshCw, Pencil, Trash2 } from 'lucide-react';
import { InventoryDialog } from '@/components/inventory-dialog';
import { getFinanceSetup, getFinanceReport, createExpense, updateExpense, deleteExpense, copyRecurringExpenses } from '@/app/actions/api';
import { jakartaDate, money, monthName, moveMonth, reportCsv, type FinanceExpense, type FinanceSummary, type FinanceSetup } from '@/lib/finance';
import './finance.css';

type Setup = FinanceSetup;
const METHODS = [['cash', 'Tunai'], ['transfer', 'Transfer'], ['qris', 'QRIS'], ['card', 'Kartu'], ['ewallet', 'E-wallet']] as const;
const errorText = (error: unknown) => error instanceof Error ? error.message : 'Koneksi terputus. Coba lagi.';

export default function KeuanganPage() {
  const [setup, setSetup] = useState<Setup | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [outletId, setOutletId] = useState('');
  const [month, setMonth] = useState(() => jakartaDate().slice(0, 7));
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [expenses, setExpenses] = useState<FinanceExpense[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState<Partial<FinanceExpense> | null>(null);
  const [confirming, setConfirming] = useState<FinanceExpense | 'recurring' | null>(null);
  const [mutating, setMutating] = useState(false);
  const request = useRef(0);
  const currentMonth = jakartaDate().slice(0, 7);

  const bootstrap = useCallback(async () => {
    setInitialLoading(true); setError('');
    try {
      const result = await getFinanceSetup();
      if (!result.success) { setError(result.message); return; }
      const data = result.data;
      setSetup(data);
      setOutletId(data.outlets.find(o => o.id === data.selectedOutletId)?.id || data.outlets[0]?.id || '');
    } catch (e) { setError(errorText(e)); }
    finally { setInitialLoading(false); }
  }, []);

  const reload = useCallback(async () => {
    if (!outletId) return;
    const id = ++request.current;
    setLoading(true); setError(''); setSummary(null); setExpenses([]);
    try {
      const result = await getFinanceReport(outletId, month);
      if (id === request.current) {
        if (result.success) { setSummary(result.data.summary); setExpenses(result.data.expenses); }
        else setError(result.message);
      }
    } catch (e) { if (id === request.current) setError(errorText(e)); }
    finally { if (id === request.current) setLoading(false); }
  }, [outletId, month]);

  useEffect(() => { void bootstrap(); }, [bootstrap]);
  useEffect(() => { void reload(); return () => { request.current++; }; }, [reload]);

  const changePeriod = (value: string) => {
    if (/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(value) && value >= '2000-01' && value <= currentMonth) {
      setSummary(null); setExpenses([]); setMonth(value); setNotice('');
    }
  };
  const outletName = setup?.outlets.find(o => o.id === outletId)?.name || '';
  const exportReport = () => {
    if (!summary) return;
    const url = URL.createObjectURL(new Blob([reportCsv(summary, expenses, outletName)], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `keuangan-${month}-${outletId}.csv`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setNotice('Laporan diunduh. File memuat ringkasan, arus kas, dan catatan pengeluaran.');
  };
  const confirmAction = async () => {
    if (!confirming || mutating) return;
    setMutating(true); setError('');
    try {
      if (confirming === 'recurring') {
        const result = await copyRecurringExpenses(outletId, month);
        if (!result.success) { setError(result.message); return; }
        setNotice(result.message || 'Pembayaran bulanan dicatat.');
      } else {
        const result = await deleteExpense(confirming.id);
        if (!result.success) { setError(result.message); return; }
        setNotice('Pengeluaran dihapus dari laporan. Riwayat perubahan tetap dicatat.');
      }
      setConfirming(null); await reload();
    } catch (e) { setError(errorText(e)); }
    finally { setMutating(false); }
  };

  return <div className="finance-workspace">
    <header className="finance-heading">
      <div><h1>Keuangan</h1><p>Periksa hasil usaha, uang masuk dan keluar, serta pengeluaran toko.</p></div>
      <button className="f-button f-primary" disabled={!setup || !outletId || loading || !!error || !!form || mutating} onClick={() => setForm({ category: 'lainnya', payment_method: 'cash', recurring: 'none' })}>
        <Plus size={18} aria-hidden="true" /> Catat pengeluaran
      </button>
    </header>
    {initialLoading ? <p role="status" className="f-panel">Memuat akun dan outlet…</p> : <>
      {setup && setup.outlets.length > 0 && <div className="finance-toolbar">
        <label>Outlet<select aria-label="Outlet" value={outletId} disabled={!!form || !!confirming || mutating} onChange={e => { setSummary(null); setExpenses([]); setOutletId(e.target.value); setNotice(''); }}>
          {setup.outlets.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select></label>
        <label>Bulan laporan<input type="month" min="2000-01" max={currentMonth} value={month} disabled={!!form || !!confirming || mutating} onChange={e => changePeriod(e.target.value)} /></label>
        <div className="f-period-buttons">
          <button className="f-button" aria-label="Bulan sebelumnya" disabled={month <= '2000-01' || !!form || !!confirming || mutating} onClick={() => changePeriod(moveMonth(month, -1))}>Sebelumnya</button>
          <button className="f-button" aria-label="Bulan berikutnya" disabled={month >= currentMonth || !!form || !!confirming || mutating} onClick={() => changePeriod(moveMonth(month, 1))}>Berikutnya</button>
        </div>
        <button className="f-button" disabled={loading || mutating || !!form || !!confirming} onClick={() => void reload()}><RefreshCw size={16} aria-hidden="true" /> Muat ulang</button>
        <button className="f-button" disabled={!summary || loading || mutating} onClick={exportReport}><Download size={16} aria-hidden="true" /> Unduh CSV</button>
      </div>}
      {notice && <div role="status" className="f-notice">{notice}</div>}
      {error && <div role="alert" className="f-notice f-error"><p>{error}</p>
        {!confirming && <button className="f-button" onClick={() => void (setup ? reload() : bootstrap())}>Coba lagi</button>}
        {error.includes('Masuk kembali') && <Link className="f-button" href="/login">Masuk kembali</Link>}
      </div>}
      {setup && !setup.outlets.length && <div className="f-panel"><h2>Belum ada outlet</h2><p>Tambahkan outlet agar transaksi dan pengeluaran bisa direkap.</p><Link className="f-button" href="/dashboard/settings">Buka pengaturan</Link></div>}
      {loading && <p role="status" className="f-panel">Memuat laporan {monthName(month)}…</p>}
      {summary && !loading && <>
        <section className="f-panel f-result" aria-labelledby="profit-heading">
          <div className="f-report-title"><div><p className="f-eyebrow">{outletName} · {monthName(month)}</p><h2 id="profit-heading">Laba setelah biaya tercatat</h2></div><span className="f-estimate">Perkiraan</span></div>
          <p className={`f-amount ${Number(summary.net_profit) < 0 ? 'f-negative' : ''}`}>{money(summary.net_profit)}</p>
          <p>{summary.orders_count} pesanan lunas · margin {summary.net_margin_pct}%</p>
          <p className="f-explanation">Dihitung dari penjualan, HPP terkini, refund, dan biaya yang sudah dicatat. Angka dapat berubah saat harga modal atau catatan biaya diperbarui. Total penjualan masih termasuk pajak dan biaya layanan yang tercatat di POS.</p>
          {summary.cogs_coverage < 1 && <div className="f-notice">HPP baru tersedia untuk {(summary.cogs_coverage * 100).toLocaleString('id-ID', { maximumFractionDigits: 1 })}% jumlah barang terjual. Laba bisa terlihat terlalu tinggi. <Link href="/dashboard/menu">Periksa harga modal produk</Link>.</div>}
          <dl className="f-calculation">
            <Amount label="Penjualan sebelum refund" value={summary.revenue} />
            <Amount label="Refund" value={summary.refunds} subtract />
            {Number(summary.delivery_fees || 0) > 0 && <Amount label="Ongkir terkumpul" value={summary.delivery_fees!} />}
            <Amount label="HPP barang terjual" value={summary.cogs} subtract />
            <Amount label="Laba kotor perkiraan" value={summary.gross_profit} total />
            <Amount label="Pengeluaran tercatat" value={summary.expenses_total} subtract />
            <Amount label="Pengeluaran kas kecil" value={summary.petty_cash_out} subtract />
            <Amount label="Laba setelah biaya tercatat" value={summary.net_profit} total />
          </dl>
        </section>
        <div className="f-columns">
          <section className="f-panel" aria-labelledby="cash-heading"><h2 id="cash-heading">Arus kas bulan ini</h2>
            <p>Perubahan uang selama {monthName(month)}. Ini bukan saldo rekening atau kas yang sudah dihitung fisik.</p>
            <dl className="f-calculation"><Amount label="Uang masuk" value={summary.cash_in} /><Amount label="Uang keluar" value={summary.cash_out} subtract /><Amount label="Perubahan kas" value={summary.cash_net} total /></dl>
            <div className="f-account-list">{summary.accounts.map(a => <div key={a.id || a.name}><h3>{a.name}</h3><p>Masuk {money(a.inflow)} · keluar {money(a.outflow)}</p><p>Perubahan <strong>{money(a.net)}</strong></p></div>)}</div>
            <p className="f-explanation">Pembayaran nota: {money(summary.purchases_paid)}. Pembelian stok memengaruhi kas saat dibayar dan HPP saat barang terjual. Akun asal pembayaran nota belum dicatat, sehingga ditampilkan terpisah.</p>
            {summary.cash_history_estimated && <p className="f-notice">Sebagian nota lama belum punya riwayat pembayaran lengkap. Bagian kas tersebut masih memakai perkiraan bulan penerimaan.</p>}
          </section>
          <section className="f-panel" aria-labelledby="payables-heading"><h2 id="payables-heading">Utang supplier saat ini</h2><p className="f-secondary-amount">{money(summary.payables_outstanding)}</p>
            <p>Semua nota yang belum lunas, termasuk dari bulan lain. Angka ini mengikuti kondisi terbaru.</p>
            {Number(summary.payables_overdue || 0) > 0 && <p className="f-notice">Lewat jatuh tempo: <strong>{money(summary.payables_overdue!)}</strong></p>}
            <Link className="f-button" href="/dashboard/pembelian">Periksa nota dan pembayaran</Link>
            <h3 className="f-spaced">Pengeluaran per kategori</h3>
            {!summary.expenses_by_category.length ? <p>Belum ada pengeluaran tercatat pada bulan ini.</p> : <dl className="f-calculation">{summary.expenses_by_category.map(c => <Amount key={c.key} label={`${c.label} (${c.count} catatan)`} value={c.amount} />)}</dl>}
          </section>
        </div>
        {summary.recurring_pending > 0 && <div className="f-notice f-recurring"><div><strong>{summary.recurring_pending} pembayaran bulanan bisa disalin</strong><p>Periksa dahulu apakah sewa, gaji, atau tagihan lainnya sudah benar-benar dibayar.</p></div><button className="f-button" disabled={mutating} onClick={() => setConfirming('recurring')}>Periksa sebelum mencatat</button></div>}
        <section className="f-panel" aria-labelledby="expenses-heading"><div className="f-report-title"><h2 id="expenses-heading">Catatan pengeluaran</h2><span>{expenses.length} catatan</span></div>
          {!expenses.length ? <p className="f-empty">Belum ada pengeluaran pada {monthName(month)}. Catat pembayaran listrik, sewa, gaji, atau biaya toko lainnya setelah dibayar.</p> : <ul className="f-expense-list">{expenses.map(e => <li key={e.id}>
            <div className="f-expense-detail"><time dateTime={e.paid_at}>{jakartaDate(new Date(e.paid_at))}</time><h3>{e.category_label}</h3>{e.note && <p>{e.note}</p>}<p>{e.cash_account_name || METHODS.find(([key]) => key === e.payment_method)?.[1] || 'Nonkas'}{e.supplier_name ? ` · ${e.supplier_name}` : ''}{e.recurring === 'monthly' ? ' · template bulanan' : ''}</p></div>
            <strong className="f-expense-amount">{money(e.amount)}</strong>
            <div className="f-expense-actions">{e.purchase_id ? <Link className="f-button" href="/dashboard/pembelian">Lihat nota</Link> : e.payment_method === 'none' ? <span>Catatan nonkas dari stok</span> : <>
              <button className="f-button" aria-label={`Ubah ${e.category_label}${e.note ? ` ${e.note}` : ''}`} onClick={() => setForm(e)}><Pencil size={16} aria-hidden="true" /> Ubah</button>
              <button className="f-button f-delete" aria-label={`Hapus ${e.category_label}${e.note ? ` ${e.note}` : ''}`} onClick={() => { setError(''); setConfirming(e); }}><Trash2 size={16} aria-hidden="true" /> Hapus</button>
            </>}</div>
          </li>)}</ul>}
        </section>
        <section className="f-panel"><h2>Perbandingan enam bulan</h2><p>Semua bulan memakai HPP terkini dan biaya yang sudah dicatat.</p><div className="f-trend">{summary.trend.map(t => <div key={t.month}><h3>{monthName(t.month)}</h3><p>Penjualan {money(t.revenue)}</p><p>Laba perkiraan <strong className={Number(t.net) < 0 ? 'f-negative' : ''}>{money(t.net)}</strong></p></div>)}</div></section>
        <p className="f-footnote">Periode laporan memakai WIB. Biaya tanpa outlet juga ikut ditampilkan. {summary.generated_at && <>Diperbarui {new Date(summary.generated_at).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })} WIB.</>}</p>
      </>}
    </>}
    {form && setup && <ExpenseForm initial={form} setup={setup} outletId={outletId} outletName={outletName} onClose={() => setForm(null)} onSaved={async message => { setForm(null); setNotice(message); await reload(); }} />}
    {confirming && <InventoryDialog title={confirming === 'recurring' ? 'Catat pembayaran bulanan' : 'Hapus catatan pengeluaran'} busy={mutating} onClose={() => { setConfirming(null); setError(''); }}><div className="finance-form">
      {confirming === 'recurring' ? <p>Salin {summary?.recurring_pending} catatan yang belum ada ke {monthName(month)} untuk {outletName}. Ini langsung mencatat biaya dan uang keluar. Lanjutkan hanya jika pembayaran sudah dilakukan. Nominal yang berubah bisa diperbaiki setelah disalin.</p> : <p>Hapus {confirming.category_label} senilai {money(confirming.amount)}{confirming.note ? ` (${confirming.note})` : ''}? Laporan laba dan arus kas akan dihitung ulang.</p>}
      {error && <p role="alert" className="f-notice f-error">{error}</p>}
      <div className="f-form-actions"><button className="f-button" disabled={mutating} onClick={() => { setConfirming(null); setError(''); }}>Batal</button><button className="f-button f-primary" disabled={mutating} onClick={() => void confirmAction()}>{mutating ? 'Menyimpan…' : confirming === 'recurring' ? 'Sudah dibayar, catat' : 'Hapus pengeluaran'}</button></div>
    </div></InventoryDialog>}
  </div>;
}

function Amount({ label, value, subtract, total }: { label: string; value: string; subtract?: boolean; total?: boolean }) {
  return <div className={total ? 'f-total' : ''}><dt>{label}</dt><dd>{subtract && Number(value) !== 0 ? '− ' : ''}{money(value)}</dd></div>;
}

function ExpenseForm({ initial, setup, outletId, outletName, onClose, onSaved }: {
  initial: Partial<FinanceExpense>; setup: Setup; outletId: string; outletName: string; onClose: () => void; onSaved: (message: string) => Promise<void>;
}) {
  const [fields, setFields] = useState({ category: initial.category || 'lainnya', amount: initial.amount ? String(initial.amount) : '',
    date: initial.paid_at ? jakartaDate(new Date(initial.paid_at)) : jakartaDate(), payment_method: initial.payment_method || 'cash',
    cash_account_id: initial.cash_account_id || '', supplier_id: initial.supplier_id || '', note: initial.note || '', recurring: initial.recurring || 'none' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [pendingCreate, setPendingCreate] = useState<Record<string, unknown> | null>(null);
  const activeAccounts = setup.accounts.filter(a => a.is_active || a.id === initial.cash_account_id);
  const locked = busy || !!pendingCreate;
  const selectedAccount = fields.cash_account_id ? activeAccounts.find(a => a.id === fields.cash_account_id)
    : activeAccounts.find(a => a.is_active && a.default_for.includes(fields.payment_method));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); if (busy) return;
    if (!/^\d+(\.\d{1,2})?$/.test(fields.amount) || Number(fields.amount) <= 0 || Number(fields.amount) >= 1e10) { setError('Isi nominal lebih dari nol, maksimal dua angka desimal.'); return; }
    if (!fields.date || fields.date > jakartaDate()) { setError('Pilih tanggal pembayaran yang sudah terjadi.'); return; }
    if (!selectedAccount) { setError('Pilih akun asal pembayaran yang aktif.'); return; }
    setBusy(true); setError('');
    try {
      const payload = { category: fields.category, amount: fields.amount,
        paid_at: initial.paid_at && jakartaDate(new Date(initial.paid_at)) === fields.date ? initial.paid_at
          : fields.date === jakartaDate() ? new Date().toISOString() : `${fields.date}T12:00:00+07:00`,
        payment_method: fields.payment_method, cash_account_id: selectedAccount.id,
        supplier_id: fields.supplier_id || null, note: fields.note.trim() || null, recurring: fields.recurring };
      if (initial.id) {
        const result = await updateExpense(initial.id, { ...payload, row_version: initial.row_version });
        if (!result.success) { setError(result.message); return; }
      }
      else {
        const request = pendingCreate || { ...payload, outlet_id: outletId, client_request_id: crypto.randomUUID() };
        setPendingCreate(request);
        const result = await createExpense(request);
        if (!result.success) {
          if (!result.uncertain) setPendingCreate(null);
          setError(result.message); return;
        }
      }
      await onSaved(`${initial.id ? 'Pengeluaran diperbarui' : 'Pengeluaran dicatat'} untuk ${fields.date} WIB.`);
    } catch (e) { setError(`${errorText(e)}${!initial.id ? ' Coba simpan lagi untuk memeriksa permintaan yang sama. Formulir tetap disimpan.' : ''}`); }
    finally { setBusy(false); }
  };
  return <InventoryDialog title={initial.id ? 'Ubah pengeluaran' : 'Catat pengeluaran'} busy={busy} onClose={onClose}><form className="finance-form" onSubmit={submit}>
    <p>Catat pembayaran yang sudah dilakukan untuk <strong>{outletName}</strong>. Pembelian stok dan pelunasan supplier dicatat melalui <Link href="/dashboard/pembelian">Nota belanja</Link> supaya tidak terhitung dua kali.</p>
    {pendingCreate && error && <p className="f-notice">Penyimpanan sebelumnya belum bisa dipastikan. Tombol simpan memeriksa permintaan yang sama agar tidak membuat catatan ganda.</p>}
    <label>Kategori<select aria-label="Kategori" value={fields.category} onChange={e => setFields({ ...fields, category: e.target.value })} disabled={locked}>{setup.categories.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}</select></label>
    {fields.category === 'bahan' && <p className="f-notice">Untuk pembelian barang atau bahan yang masuk stok, gunakan Nota belanja agar stok dan harga modal ikut diperbarui.</p>}
    <div className="f-field-grid"><label>Nominal (Rp)<input autoFocus required type="number" inputMode="decimal" min="0.01" max="9999999999.99" step="0.01" value={fields.amount} onChange={e => setFields({ ...fields, amount: e.target.value })} disabled={locked} placeholder="Contoh: 350000" /></label>
      <label>Tanggal pembayaran (WIB)<input required type="date" max={jakartaDate()} value={fields.date} onChange={e => setFields({ ...fields, date: e.target.value })} disabled={locked} /></label></div>
    <div className="f-field-grid"><label>Metode pembayaran<select aria-label="Metode pembayaran" value={fields.payment_method} onChange={e => setFields({ ...fields, payment_method: e.target.value, cash_account_id: '' })} disabled={locked}>{METHODS.map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
      <label>Akun asal pembayaran<select aria-label="Akun asal pembayaran" value={fields.cash_account_id} onChange={e => setFields({ ...fields, cash_account_id: e.target.value })} disabled={locked}><option value="">{selectedAccount ? `Otomatis: ${selectedAccount.name}` : 'Pilih akun aktif'}</option>{activeAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label></div>
    <label>Catatan (opsional)<input maxLength={200} value={fields.note} onChange={e => setFields({ ...fields, note: e.target.value })} disabled={locked} placeholder="Contoh: listrik toko bulan Oktober" /></label>
    {!!setup.suppliers.length && <label>Supplier (opsional)<select aria-label="Supplier (opsional)" value={fields.supplier_id} onChange={e => setFields({ ...fields, supplier_id: e.target.value })} disabled={locked}><option value="">Tidak terkait supplier</option>{setup.suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>}
    <label className="f-checkbox"><input type="checkbox" checked={fields.recurring === 'monthly'} onChange={e => setFields({ ...fields, recurring: e.target.checked ? 'monthly' : 'none' })} disabled={locked} /><span>Jadikan template bulanan. Bulan berikutnya tetap perlu diperiksa dan dicatat setelah dibayar.</span></label>
    {fields.amount && Number(fields.amount) > 0 && <p className="f-notice">Akan mencatat biaya {money(fields.amount)} dan uang keluar dari {selectedAccount?.name || 'akun yang dipilih'}.</p>}
    {error && <p role="alert" className="f-notice f-error">{error}</p>}
    <div className="f-form-actions"><button type="button" className="f-button" disabled={busy} onClick={onClose}>Batal</button><button type="submit" className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan…' : initial.id ? 'Simpan perubahan' : 'Catat pembayaran'}</button></div>
  </form></InventoryDialog>;
}
