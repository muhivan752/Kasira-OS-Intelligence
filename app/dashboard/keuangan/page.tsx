'use client';

import { useEffect, useState } from 'react';
import {
  Wallet, Plus, X, Trash2, Pencil, Loader2, AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight,
  TrendingUp, TrendingDown, Copy, Info, Receipt,
} from 'lucide-react';
import Link from 'next/link';
import {
  getOutlets, getFinanceSummary, getFinanceCategories, getCashAccounts, getExpenses,
  createExpense, updateExpense, deleteExpense, copyRecurringExpenses, getSuppliers,
} from '@/app/actions/api';

// ── Tipe ──────────────────────────────────────────────────────────────
interface Cat { key: string; label: string }
interface Account { id: string; name: string; kind: string; default_for: string[] }
interface Expense {
  id: string; category: string; category_label: string; amount: string; paid_at: string; payment_method: string;
  cash_account_id?: string | null; cash_account_name?: string | null; supplier_id?: string | null; supplier_name?: string | null;
  purchase_id?: string | null; note?: string | null; recurring: string; row_version: number;
}
interface Summary {
  month: string; revenue: string; refunds: string; net_revenue: string; cogs: string; cogs_coverage: number;
  gross_profit: string; gross_margin_pct: number; expenses_total: string; petty_cash_out: string;
  expenses_by_category: { key: string; label: string; amount: string; count: number }[];
  net_profit: string; net_margin_pct: number; orders_count: number;
  cash_in: string; cash_out: string; cash_net: string;
  accounts: { id: string | null; name: string; kind: string; inflow: string; outflow: string; net: string }[];
  purchases_paid: string; payables_outstanding: string;
  trend: { month: string; label: string; revenue: string; cogs: string; expenses: string; net: string }[];
  recurring_pending: number;
}

const rp = (n: number | string | null | undefined) => 'Rp ' + Math.round(Number(n || 0)).toLocaleString('id-ID');
const rpShort = (n: number | string) => {
  const v = Number(n || 0), a = Math.abs(v);
  const s = a >= 1e9 ? (a / 1e9).toFixed(1) + ' M' : a >= 1e6 ? (a / 1e6).toFixed(1) + ' jt' : a >= 1e3 ? Math.round(a / 1e3) + ' rb' : String(a);
  return (v < 0 ? '−' : '') + s;
};
const tgl = (iso: string) => new Date(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
const monthKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
const monthLabel = (k: string) => { const [y, m] = k.split('-').map(Number); return new Date(y, m - 1, 1).toLocaleDateString('id-ID', { month: 'long', year: 'numeric' }); };
const shiftMonth = (k: string, d: number) => { const [y, m] = k.split('-').map(Number); return monthKey(new Date(y, m - 1 + d, 1)); };
const METHODS = [['cash', 'Tunai'], ['transfer', 'Transfer'], ['qris', 'QRIS'], ['card', 'Kartu'], ['ewallet', 'E-wallet']] as const;

export default function KeuanganPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState('');
  const [month, setMonth] = useState(() => monthKey(new Date()));
  const [summary, setSummary] = useState<Summary | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [cats, setCats] = useState<Cat[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [suppliers, setSuppliers] = useState<{ id: string; name: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [form, setForm] = useState<Partial<Expense> | null>(null);

  const showToast = (kind: 'ok' | 'err', text: string) => { setToast({ kind, text }); setTimeout(() => setToast(null), k5(kind)); };
  const k5 = (k: string) => (k === 'ok' ? 4000 : 7000);

  const reload = async (oid = outletId, m = month) => {
    if (!oid) return;
    setBusy(true);
    const [s, e] = await Promise.all([getFinanceSummary(oid, m), getExpenses(oid, m)]);
    setSummary(s); setExpenses(e); setBusy(false);
  };

  useEffect(() => {
    (async () => {
      try {
        const [outlets, c, a, sup] = await Promise.all([getOutlets(), getFinanceCategories(), getCashAccounts(), getSuppliers()]);
        setCats(c); setAccounts(a); setSuppliers(sup);
        if (!outlets?.length) return;
        setOutletId(outlets[0].id);
        await reload(outlets[0].id, month);
      } finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const changeMonth = async (d: number) => { const m = shiftMonth(month, d); setMonth(m); await reload(outletId, m); };

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-500">Memuat...</div>;
  if (!outletId) return <div className="bg-white rounded-xl border p-8 text-center text-gray-500">Belum ada outlet.</div>;

  const s = summary;
  const net = Number(s?.net_profit || 0);
  const isFuture = month > monthKey(new Date());

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Keuangan</h1>
          <p className="text-gray-500">Laba rugi & arus kas dihitung sendiri dari transaksi, nota belanja, dan pengeluaran.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-white border border-gray-200 rounded-lg">
            <button onClick={() => changeMonth(-1)} className="p-2 hover:bg-gray-50 rounded-l-lg"><ChevronLeft className="w-4 h-4" /></button>
            <span className="px-3 text-sm font-semibold text-gray-900 min-w-[150px] text-center">{monthLabel(month)}</span>
            <button onClick={() => changeMonth(1)} disabled={isFuture} className="p-2 hover:bg-gray-50 rounded-r-lg disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
          </div>
          <button onClick={() => setForm({ category: 'lainnya', payment_method: 'cash', recurring: 'none' })} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            <Plus className="w-4 h-4" /> Catat Pengeluaran
          </button>
        </div>
      </div>

      {toast && (
        <div className={`rounded-lg px-4 py-3 text-sm flex items-start gap-2 border ${toast.kind === 'ok' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
          {toast.kind === 'ok' ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />}<span>{toast.text}</span>
        </div>
      )}

      {s && s.recurring_pending > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-2"><Copy className="w-4 h-4" /> {s.recurring_pending} pengeluaran bulanan (sewa, gaji, dll) belum dicatat bulan ini.</span>
          <button onClick={async () => { try { const r = await copyRecurringExpenses(outletId, month); showToast('ok', r.message); await reload(); } catch (e: any) { showToast('err', e.message); } }} className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700">Salin dari bulan lalu</button>
        </div>
      )}

      {/* ── Laba rugi ── */}
      <div className={`rounded-2xl border p-5 ${net >= 0 ? 'bg-white border-gray-200' : 'bg-red-50 border-red-200'}`}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Laba bersih {monthLabel(month)}</p>
            <p className={`mt-1 text-4xl font-bold tabular-nums ${net >= 0 ? 'text-gray-900' : 'text-red-700'}`}>{busy ? '…' : rp(net)}</p>
            <p className="text-sm text-gray-500 mt-1">{s?.orders_count || 0} order lunas · margin bersih {s?.net_margin_pct ?? 0}%</p>
          </div>
          <Trend trend={s?.trend || []} />
        </div>
        <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-5 text-sm">
          <Row label="Pendapatan" value={s?.revenue} hint={Number(s?.refunds) > 0 ? `− refund ${rp(s?.refunds)}` : undefined} />
          <Row label="HPP terjual" value={s?.cogs} neg hint={s && s.cogs_coverage < 1 ? `${Math.round(s.cogs_coverage * 100)}% item punya HPP` : 'semua item punya HPP'} />
          <Row label="Laba kotor" value={s?.gross_profit} bold hint={`margin ${s?.gross_margin_pct ?? 0}%`} />
          <Row label="Pengeluaran" value={Number(s?.expenses_total || 0) + Number(s?.petty_cash_out || 0)} neg hint={Number(s?.petty_cash_out) > 0 ? `termasuk kas kecil shift ${rp(s?.petty_cash_out)}` : undefined} />
          <Row label="Laba bersih" value={s?.net_profit} bold />
        </div>
        {s && s.cogs_coverage < 0.7 && (
          <p className="mt-3 text-xs text-amber-700 flex items-start gap-1.5"><Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />Sebagian besar produk belum punya harga modal — laba kotor kelihatan lebih besar dari aslinya. Isi resep (Pro) atau catat nota belanja produk supaya HPP-nya terisi.</p>
        )}
      </div>

      {/* ── Arus kas ── */}
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="bg-white rounded-2xl border border-gray-200 p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-gray-900">Uangnya ada di mana</h2>
            <span className={`text-sm font-semibold tabular-nums ${Number(s?.cash_net) >= 0 ? 'text-green-700' : 'text-red-700'}`}>net {rp(s?.cash_net)}</span>
          </div>
          <div className="mt-3 divide-y divide-gray-100">
            {(s?.accounts || []).map(a => (
              <div key={a.id || a.name} className="py-2.5 flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium text-gray-900">{a.name}</p>
                  <p className="text-xs text-gray-500">masuk {rp(a.inflow)} · keluar {rp(a.outflow)}</p>
                </div>
                <span className={`font-bold tabular-nums ${Number(a.net) >= 0 ? 'text-gray-900' : 'text-red-700'}`}>{rp(a.net)}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500 space-y-1">
            <p>Belanja stok yang dibayar bulan ini: <b className="text-gray-700">{rp(s?.purchases_paid)}</b> (keluar dari kas, masuk laba rugi sebagai HPP waktu terjual).</p>
            {Number(s?.payables_outstanding) > 0 && <p>Utang supplier belum dibayar: <Link href="/dashboard/pembelian" className="font-semibold text-amber-700 hover:underline">{rp(s?.payables_outstanding)} →</Link></p>}
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-5">
          <h2 className="font-bold text-gray-900">Pengeluaran per kategori</h2>
          {(s?.expenses_by_category || []).length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">Belum ada pengeluaran bulan ini.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {s!.expenses_by_category.map(c => {
                const pct = Number(s!.expenses_total) ? Math.round(Number(c.amount) / Number(s!.expenses_total) * 100) : 0;
                return (
                  <div key={c.key} className="text-sm">
                    <div className="flex justify-between"><span className="text-gray-700">{c.label} <span className="text-gray-400">({c.count})</span></span><span className="font-semibold tabular-nums">{rp(c.amount)}</span></div>
                    <div className="mt-1 h-1.5 rounded-full bg-gray-100"><div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${pct}%` }} /></div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Daftar pengeluaran ── */}
      <div className="bg-white rounded-2xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-bold text-gray-900">Pengeluaran {monthLabel(month)}</h2>
          <span className="text-sm text-gray-500">{expenses.length} catatan</span>
        </div>
        {expenses.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            <Wallet className="w-10 h-10 mx-auto mb-2 text-blue-300" />
            Belum ada. Catat sewa, listrik, gaji, gas — sekali tap. Yang bulanan tandai "ulangi tiap bulan" biar tinggal disalin.
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {expenses.map(e => (
              <div key={e.id} className="px-5 py-3 flex items-center gap-3 text-sm">
                <div className="w-12 shrink-0 text-gray-400 tabular-nums">{tgl(e.paid_at)}</div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900 truncate">{e.category_label}{e.note ? <span className="text-gray-500 font-normal"> · {e.note}</span> : ''}</p>
                  <p className="text-xs text-gray-500">{e.cash_account_name || e.payment_method}{e.supplier_name ? ` · ${e.supplier_name}` : ''}{e.recurring === 'monthly' ? ' · tiap bulan' : ''}{e.purchase_id ? ' · dari nota belanja' : ''}</p>
                </div>
                <span className="font-semibold tabular-nums">{rp(e.amount)}</span>
                {e.purchase_id ? (
                  <Link href="/dashboard/pembelian" className="p-2 text-gray-400 hover:text-blue-600" title="Lihat nota"><Receipt className="w-4 h-4" /></Link>
                ) : (
                  <>
                    <button onClick={() => setForm(e)} className="p-2 text-gray-400 hover:text-gray-700"><Pencil className="w-4 h-4" /></button>
                    <button onClick={async () => { if (!confirm('Hapus pengeluaran ini?')) return; try { await deleteExpense(e.id); await reload(); showToast('ok', 'Dihapus'); } catch (er: any) { showToast('err', er.message); } }} className="p-2 text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {form && (
        <ExpenseModal
          initial={form} cats={cats} accounts={accounts} suppliers={suppliers} outletId={outletId}
          onClose={() => setForm(null)}
          onSaved={async (msg) => { setForm(null); await reload(); showToast('ok', msg); }}
        />
      )}
    </div>
  );
}

function Row({ label, value, neg, bold, hint }: { label: string; value?: string | number; neg?: boolean; bold?: boolean; hint?: string }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2.5">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`tabular-nums ${bold ? 'font-bold text-gray-900' : 'font-semibold text-gray-800'}`}>{neg ? '− ' : ''}{rp(value)}</p>
      {hint && <p className="text-[11px] text-gray-400 mt-0.5">{hint}</p>}
    </div>
  );
}

/** Tren 6 bulan: batang pendapatan + garis laba bersih, CSS murni. */
function Trend({ trend }: { trend: Summary['trend'] }) {
  if (!trend.length) return null;
  const max = Math.max(1, ...trend.map(t => Math.abs(Number(t.revenue)), ...trend.map(t => Math.abs(Number(t.net)))));
  return (
    <div className="flex items-end gap-2 h-20">
      {trend.map(t => {
        const rev = Number(t.revenue), net = Number(t.net);
        return (
          <div key={t.month} className="flex flex-col items-center gap-1 w-10" title={`${t.label}: pendapatan ${rp(rev)}, laba ${rp(net)}`}>
            <div className="relative w-full h-14 flex items-end justify-center">
              <div className="w-5 rounded-t bg-blue-200" style={{ height: `${Math.max(2, rev / max * 100)}%` }} />
              <div className={`absolute w-5 rounded-sm ${net >= 0 ? 'bg-green-500' : 'bg-red-500'}`} style={{ height: 3, bottom: `${Math.max(0, Math.min(100, (net >= 0 ? net : 0) / max * 100))}%` }} />
            </div>
            <span className={`text-[10px] ${net < 0 ? 'text-red-600' : 'text-gray-500'}`}>{t.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function ExpenseModal({ initial, cats, accounts, suppliers, outletId, onClose, onSaved }: {
  initial: Partial<Expense>; cats: Cat[]; accounts: Account[]; suppliers: { id: string; name: string }[]; outletId: string;
  onClose: () => void; onSaved: (msg: string) => void;
}) {
  const isEdit = !!initial.id;
  const [f, setF] = useState({
    category: initial.category || 'lainnya',
    amount: initial.amount ? String(Math.round(Number(initial.amount))) : '',
    paid_at: initial.paid_at ? initial.paid_at.slice(0, 10) : new Date().toISOString().slice(0, 10),
    payment_method: initial.payment_method || 'cash',
    cash_account_id: initial.cash_account_id || '',
    supplier_id: initial.supplier_id || '',
    note: initial.note || '',
    recurring: initial.recurring || 'none',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    if (!(Number(f.amount) > 0)) { setError('Isi nominalnya.'); return; }
    setBusy(true); setError('');
    try {
      const payload = {
        category: f.category, amount: Number(f.amount),
        paid_at: new Date(f.paid_at + 'T12:00:00').toISOString(),
        payment_method: f.payment_method, cash_account_id: f.cash_account_id || null,
        supplier_id: f.supplier_id || null, note: f.note || null, recurring: f.recurring,
      };
      if (isEdit) { await updateExpense(initial.id!, { ...payload, row_version: initial.row_version }); onSaved('Pengeluaran diperbarui'); }
      else { await createExpense({ ...payload, outlet_id: outletId }); onSaved('Pengeluaran dicatat'); }
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4" onClick={onClose}>
      <div className="bg-white w-full sm:max-w-lg rounded-t-2xl sm:rounded-2xl max-h-[92vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-3 flex items-center justify-between">
          <h2 className="font-bold text-gray-900">{isEdit ? 'Ubah Pengeluaran' : 'Catat Pengeluaran'}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="text-xs font-semibold text-gray-500">Buat apa</label>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {cats.map(c => (
                <button key={c.key} onClick={() => setF({ ...f, category: c.key })} className={`px-3 py-1.5 rounded-full text-sm border transition ${f.category === c.key ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-gray-200 text-gray-700 hover:border-blue-300'}`}>{c.label}</button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-500">Nominal</label>
              <input type="number" inputMode="numeric" min="0" autoFocus value={f.amount} onChange={e => setF({ ...f, amount: e.target.value })} placeholder="0" className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-lg font-semibold" />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500">Tanggal</label>
              <input type="date" value={f.paid_at} onChange={e => setF({ ...f, paid_at: e.target.value })} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-500">Bayar pakai</label>
              <select value={f.payment_method} onChange={e => setF({ ...f, payment_method: e.target.value, cash_account_id: '' })} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                {METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500">Dari akun</label>
              <select value={f.cash_account_id} onChange={e => setF({ ...f, cash_account_id: e.target.value })} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                <option value="">Otomatis ikut metode</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500">Catatan (opsional)</label>
            <input value={f.note} onChange={e => setF({ ...f, note: e.target.value })} placeholder="mis. Sewa ruko September" className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </div>
          {suppliers.length > 0 && (
            <div>
              <label className="text-xs font-semibold text-gray-500">Dibayar ke supplier (opsional)</label>
              <select value={f.supplier_id} onChange={e => setF({ ...f, supplier_id: e.target.value })} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                <option value="">—</option>
                {suppliers.map(sp => <option key={sp.id} value={sp.id}>{sp.name}</option>)}
              </select>
            </div>
          )}
          <label className="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" checked={f.recurring === 'monthly'} onChange={e => setF({ ...f, recurring: e.target.checked ? 'monthly' : 'none' })} className="mt-0.5" />
            <span>Ulangi tiap bulan <span className="text-gray-400">— bulan depan tinggal klik "Salin dari bulan lalu"</span></span>
          </label>
          {error && <p className="text-sm text-red-600 flex items-center gap-2"><AlertTriangle className="w-4 h-4" />{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Batal</button>
            <button onClick={submit} disabled={busy} className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">{busy && <Loader2 className="w-4 h-4 animate-spin" />}{isEdit ? 'Simpan' : 'Catat'}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
