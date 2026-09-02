'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ShoppingCart, Plus, Receipt, Truck, AlertTriangle, CheckCircle2, X, Trash2,
  Camera, Loader2, Wallet, CalendarClock, TrendingUp, TrendingDown, Pencil,
} from 'lucide-react';
import {
  getOutlets, getCurrentUser, getProducts, getIngredients,
  getSuppliers, createSupplier, updateSupplier, deleteSupplier,
  getPurchases, getPurchaseSummary, createPurchase, payPurchase, scanInvoice, proxyUploadImage,
} from '@/app/actions/api';

// ── Tipe ──────────────────────────────────────────────────────────────

interface Supplier {
  id: string; name: string; phone?: string | null; address?: string | null; notes?: string | null;
  payment_terms_days: number; is_active: boolean; row_version: number;
  purchase_count: number; purchase_total: string; outstanding_total: string;
}
interface PurchaseLine {
  id: string; ingredient_id?: string | null; product_id?: string | null; is_other?: boolean; name: string;
  quantity: number; unit?: string | null; qty_base?: number | null;
  unit_price: string; total_price: string; cost_before?: string | null; cost_after?: string | null;
}
interface Purchase {
  id: string; po_number: string; supplier_id?: string | null; supplier_name?: string | null;
  invoice_no?: string | null; photo_url?: string | null; notes?: string | null; received_at?: string | null;
  total_amount: string; paid_amount: string; outstanding_amount: string; due_at?: string | null;
  row_version: number; items: PurchaseLine[];
}
interface Summary {
  month_total: string; month_count: number; outstanding_total: string; outstanding_count: number;
  next_due_at?: string | null; next_due_supplier?: string | null; next_due_amount?: string | null;
}
interface Target { key: string; kind: 'ingredient' | 'product'; id: string; name: string; unit: string; hint?: string }
interface DraftLine { key: string; targetKey: string; quantity: string; unit: string; unit_price: string; total_price: string; rawName?: string; newName?: string; newBaseUnit?: string; newSellPrice?: string }
// targetKey khusus: '__other' (bukan stok), '__new_ing' (bahan baru, Pro), '__new_prod' (produk baru)

const rp = (n: number | string | null | undefined) =>
  'Rp ' + Math.round(Number(n || 0)).toLocaleString('id-ID');
const rpDec = (n: number | string | null | undefined) => {
  const v = Number(n || 0);
  return 'Rp ' + (v % 1 === 0 ? v.toLocaleString('id-ID') : v.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
};
const tgl = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
const newKey = () => Math.random().toString(36).slice(2, 9);
// Satuan di nota — dipilih, bukan diketik. Konversi ke satuan stok bahan
// (gram/ml/pcs/bungkus) dikerjain backend (unit_utils.UNIT_ALIASES), jadi
// daftar ini WAJIB subset dari alias di sana.
const UNIT_GROUPS: { label: string; units: { v: string; l: string }[] }[] = [
  { label: 'Berat', units: [{ v: 'gram', l: 'gram (gr)' }, { v: 'ons', l: 'ons (100 gr)' }, { v: 'kg', l: 'kg' }] },
  { label: 'Volume', units: [{ v: 'ml', l: 'ml' }, { v: 'liter', l: 'liter' }, { v: 'galon', l: 'galon (19 L)' }] },
  { label: 'Hitungan', units: [{ v: 'pcs', l: 'pcs / buah' }, { v: 'butir', l: 'butir' }, { v: 'ekor', l: 'ekor' }, { v: 'ikat', l: 'ikat' }, { v: 'botol', l: 'botol' }, { v: 'kaleng', l: 'kaleng' }, { v: 'sisir', l: 'sisir' }, { v: 'lembar', l: 'lembar' }] },
  { label: 'Kemasan', units: [{ v: 'bungkus', l: 'bungkus' }, { v: 'sachet', l: 'sachet' }, { v: 'pak', l: 'pak' }, { v: 'renceng', l: 'renceng' }, { v: 'dus', l: 'dus (12)' }, { v: 'lusin', l: 'lusin (12)' }, { v: 'tray', l: 'tray (30)' }, { v: 'papan', l: 'papan telur (30)' }] },
];

export default function PembelianPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState('');
  const [brandId, setBrandId] = useState('');
  const [isPro, setIsPro] = useState(false);
  const [tab, setTab] = useState<'nota' | 'supplier'>('nota');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);

  const [showNota, setShowNota] = useState(false);
  const [detail, setDetail] = useState<Purchase | null>(null);
  const [supplierForm, setSupplierForm] = useState<Partial<Supplier> | null>(null);

  const showToast = (kind: 'ok' | 'err', text: string) => {
    setToast({ kind, text });
    setTimeout(() => setToast(null), kind === 'ok' ? 4000 : 7000);
  };

  const reload = async (oid = outletId) => {
    if (!oid) return;
    const [s, p, sup] = await Promise.all([getPurchaseSummary(oid), getPurchases(oid), getSuppliers()]);
    setSummary(s); setPurchases(p); setSuppliers(sup);
  };

  useEffect(() => {
    (async () => {
      try {
        const [user, outlets] = await Promise.all([getCurrentUser(), getOutlets()]);
        const pro = ['pro', 'business', 'enterprise'].includes(user?.subscription_tier || '');
        setIsPro(pro);
        if (!outlets?.length) { setLoading(false); return; }
        const o = outlets[0];
        setOutletId(o.id); setBrandId(o.brand_id);
        const [prods, ings] = await Promise.all([
          getProducts(o.brand_id),
          pro ? getIngredients(o.brand_id, o.id) : Promise.resolve([]),
        ]);
        const t: Target[] = [
          ...(ings || []).map((i: any) => ({
            key: `i:${i.id}`, kind: 'ingredient' as const, id: i.id, name: i.name, unit: i.base_unit,
            hint: i.cost_per_base_unit ? `HPP ${rpDec(i.cost_per_base_unit)}/${i.base_unit}` : undefined,
          })),
          ...(prods || []).map((p: any) => ({
            key: `p:${p.id}`, kind: 'product' as const, id: p.id, name: p.name, unit: 'pcs',
            hint: p.buy_price ? `beli ${rp(p.buy_price)}` : undefined,
          })),
        ];
        setTargets(t);
        await reload(o.id);
      } finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-500">Memuat...</div>;
  if (!outletId) return <div className="bg-white rounded-xl border p-8 text-center text-gray-500">Belum ada outlet.</div>;

  const outstanding = Number(summary?.outstanding_total || 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pembelian</h1>
          <p className="text-gray-500">Catat nota belanja — stok naik, HPP bahan ke-update, utang supplier tercatat. Otomatis.</p>
        </div>
        <button onClick={() => setShowNota(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
          <Plus className="w-4 h-4" /> Catat Nota
        </button>
      </div>

      {toast && (
        <div className={`rounded-lg px-4 py-3 text-sm flex items-start gap-2 border ${toast.kind === 'ok' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
          {toast.kind === 'ok' ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />}
          <span className="whitespace-pre-line">{toast.text}</span>
        </div>
      )}

      {/* Ringkasan */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Belanja bulan ini</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 tabular-nums">{rp(summary?.month_total)}</p>
          <p className="text-xs text-gray-500">{summary?.month_count || 0} nota</p>
        </div>
        <div className={`rounded-xl border p-4 ${outstanding > 0 ? 'bg-amber-50 border-amber-200' : 'bg-white border-gray-200'}`}>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Utang ke supplier</p>
          <p className={`mt-1 text-2xl font-bold tabular-nums ${outstanding > 0 ? 'text-amber-700' : 'text-gray-900'}`}>{rp(outstanding)}</p>
          <p className="text-xs text-gray-500">{summary?.outstanding_count || 0} nota belum lunas</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Jatuh tempo terdekat</p>
          {summary?.next_due_at ? (
            <>
              <p className="mt-1 text-2xl font-bold text-gray-900 tabular-nums">{rp(summary.next_due_amount)}</p>
              <p className="text-xs text-gray-500 flex items-center gap-1"><CalendarClock className="w-3 h-3" /> {tgl(summary.next_due_at)} · {summary.next_due_supplier || 'tanpa supplier'}</p>
            </>
          ) : (
            <p className="mt-1 text-lg font-semibold text-gray-400">Tidak ada</p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {([['nota', 'Nota Belanja', Receipt], ['supplier', 'Supplier', Truck]] as const).map(([k, label, Icon]) => (
          <button key={k} onClick={() => setTab(k)} className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition ${tab === k ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}>
            <Icon className="w-4 h-4" /> {label}
            <span className="text-xs text-gray-400">({k === 'nota' ? purchases.length : suppliers.length})</span>
          </button>
        ))}
      </div>

      {tab === 'nota' && (
        purchases.length === 0 ? (
          <EmptyNota onAdd={() => setShowNota(true)} />
        ) : (
          <div className="space-y-2">
            {purchases.map(p => {
              const utang = Number(p.outstanding_amount) > 0;
              const overdue = utang && p.due_at && new Date(p.due_at) < new Date();
              return (
                <button key={p.id} onClick={() => setDetail(p)} className="w-full text-left bg-white rounded-xl border border-gray-200 px-4 py-3 hover:border-blue-300 transition">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 truncate">{p.supplier_name || 'Tanpa supplier'} <span className="text-gray-400 font-normal text-sm">· {p.po_number}</span></p>
                      <p className="text-sm text-gray-500 truncate">{tgl(p.received_at)} · {p.items.length} item · {p.items.slice(0, 3).map(i => i.name).join(', ')}{p.items.length > 3 ? '…' : ''}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-bold text-gray-900 tabular-nums">{rp(p.total_amount)}</p>
                      {utang ? (
                        <span className={`inline-block mt-1 text-xs font-semibold px-2 py-0.5 rounded-full ${overdue ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                          {overdue ? 'Lewat tempo' : 'Utang'} {rp(p.outstanding_amount)}
                        </span>
                      ) : (
                        <span className="inline-block mt-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-700">Lunas</span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )
      )}

      {tab === 'supplier' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button onClick={() => setSupplierForm({ name: '', payment_terms_days: 0 })} className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:border-blue-300">
              <Plus className="w-4 h-4" /> Tambah Supplier
            </button>
          </div>
          {suppliers.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500 text-sm">
              Belum ada supplier. Supplier juga otomatis kebentuk waktu kamu ketik nama baru di nota.
            </div>
          ) : suppliers.map(s => (
            <div key={s.id} className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-semibold text-gray-900 truncate">{s.name}</p>
                <p className="text-sm text-gray-500 truncate">
                  {s.phone || 'tanpa nomor'} · tempo {s.payment_terms_days} hari · {s.purchase_count} nota · {rp(s.purchase_total)}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {Number(s.outstanding_total) > 0 && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Utang {rp(s.outstanding_total)}</span>
                )}
                <button onClick={() => setSupplierForm(s)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"><Pencil className="w-4 h-4" /></button>
                <button
                  onClick={async () => {
                    if (!confirm(`Hapus supplier ${s.name}?`)) return;
                    try { await deleteSupplier(s.id); await reload(); showToast('ok', 'Supplier dihapus'); }
                    catch (e: any) { showToast('err', e.message); }
                  }}
                  className="p-2 rounded-lg hover:bg-red-50 text-red-500"
                ><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNota && (
        <NotaModal
          outletId={outletId} isPro={isPro} suppliers={suppliers} targets={targets}
          onClose={() => setShowNota(false)}
          onSaved={async (p) => {
            setShowNota(false);
            await reload();
            const changes = p.items.filter(i => i.cost_before != null && i.cost_after != null && i.cost_before !== i.cost_after)
              .map(i => `${i.name}: ${rpDec(i.cost_before)} → ${rpDec(i.cost_after)}`);
            showToast('ok', `Nota ${p.po_number} dicatat. Stok masuk.` + (changes.length ? `\nHPP berubah — ${changes.join(' · ')}` : ''));
          }}
        />
      )}

      {detail && (
        <DetailModal
          purchase={detail}
          onClose={() => setDetail(null)}
          onPaid={async (updated) => { setDetail(updated); await reload(); showToast('ok', Number(updated.outstanding_amount) > 0 ? 'Pembayaran dicatat' : 'Nota lunas'); }}
        />
      )}

      {supplierForm && (
        <SupplierModal
          initial={supplierForm}
          onClose={() => setSupplierForm(null)}
          onSaved={async () => { setSupplierForm(null); await reload(); showToast('ok', 'Supplier disimpan'); }}
        />
      )}
    </div>
  );
}

// ── Kosong ────────────────────────────────────────────────────────────

function EmptyNota({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 sm:p-8">
      <div className="max-w-lg mx-auto text-center">
        <ShoppingCart className="w-12 h-12 mx-auto mb-3 text-blue-400" />
        <h2 className="text-lg font-bold text-gray-900">Belum ada nota belanja</h2>
        <p className="text-sm text-gray-500 mt-1">
          Tiap kali belanja bahan atau stok, catat notanya di sini. Kamu cuma isi apa yang dibeli dan berapa —
          stok bertambah, harga modal (HPP) dihitung ulang pakai rata-rata, dan utang ke supplier kecatat sendiri.
        </p>
        <div className="mt-5 grid gap-2 text-left text-sm text-gray-600 sm:grid-cols-3">
          <div className="rounded-lg bg-gray-50 p-3"><p className="font-semibold text-gray-900">1. Foto atau ketik</p>Upload foto nota, AI baca barisnya. Atau isi manual.</div>
          <div className="rounded-lg bg-gray-50 p-3"><p className="font-semibold text-gray-900">2. Cek & simpan</p>Cocokkan ke bahan/produk yang ada, konfirmasi harga.</div>
          <div className="rounded-lg bg-gray-50 p-3"><p className="font-semibold text-gray-900">3. Selesai</p>Stok, HPP, dan utang ke-update. Menu engineering langsung pakai angka baru.</div>
        </div>
        <button onClick={onAdd} className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          <Plus className="w-4 h-4" /> Catat Nota Pertama
        </button>
      </div>
    </div>
  );
}

// ── Modal: catat nota ─────────────────────────────────────────────────

function NotaModal({ outletId, isPro, suppliers, targets, onClose, onSaved }: {
  outletId: string; isPro: boolean; suppliers: Supplier[]; targets: Target[];
  onClose: () => void; onSaved: (p: Purchase) => void;
}) {
  const [supplierChoice, setSupplierChoice] = useState<string>('');   // id | '' | '__new'
  const [supplierName, setSupplierName] = useState('');
  const [receivedAt, setReceivedAt] = useState(() => new Date().toISOString().slice(0, 10));
  const [invoiceNo, setInvoiceNo] = useState('');
  const [notes, setNotes] = useState('');
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [lines, setLines] = useState<DraftLine[]>([{ key: newKey(), targetKey: '', quantity: '', unit: '', unit_price: '', total_price: '' }]);
  const [payMode, setPayMode] = useState<'lunas' | 'utang'>('lunas');
  const [paidAmount, setPaidAmount] = useState('');
  const [dueAt, setDueAt] = useState('');
  const [scanning, setScanning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const targetByKey = useMemo(() => Object.fromEntries(targets.map(t => [t.key, t])), [targets]);
  const total = lines.reduce((s, l) => s + (Number(l.total_price) || 0), 0);
  const ingredientTargets = targets.filter(t => t.kind === 'ingredient');
  const productTargets = targets.filter(t => t.kind === 'product');

  const updateLine = (key: string, patch: Partial<DraftLine>) => {
    setLines(ls => ls.map(l => {
      if (l.key !== key) return l;
      const next = { ...l, ...patch };
      // total ngikut qty × harga kecuali user ngetik total sendiri
      if ('quantity' in patch || 'unit_price' in patch) {
        const q = Number(next.quantity) || 0, up = Number(next.unit_price) || 0;
        next.total_price = q && up ? String(Math.round(q * up)) : next.total_price;
      }
      if ('targetKey' in patch && patch.targetKey) {
        const t = targetByKey[patch.targetKey];
        if (t && !next.unit) next.unit = t.unit;
      }
      return next;
    }));
  };

  const handleScan = async (file: File) => {
    setScanning(true); setError('');
    try {
      const fd = new FormData(); fd.append('file', file);
      const [scan, upload] = await Promise.all([scanInvoice(fd), (() => { const f2 = new FormData(); f2.append('file', file); return proxyUploadImage(f2); })()]);
      if (upload?.success && upload.url) setPhotoUrl(upload.url);
      if (!scan.success || !scan.data) { setError(scan.message || 'Nota tidak terbaca'); return; }
      const d = scan.data;
      if (d.supplier_name && !supplierName && !supplierChoice) {
        const existing = suppliers.find(s => s.name.toLowerCase() === String(d.supplier_name).toLowerCase());
        if (existing) setSupplierChoice(existing.id); else { setSupplierChoice('__new'); setSupplierName(d.supplier_name); }
      }
      if (d.invoice_number && !invoiceNo) setInvoiceNo(String(d.invoice_number));
      const scanned: DraftLine[] = (d.items || []).map((it: any) => {
        const match = it.matched_ingredient_id ? `i:${it.matched_ingredient_id}` : '';
        // Kalau bukan bahan, coba cocokkan ke nama produk.
        const prodMatch = !match ? productTargets.find(p => p.name.toLowerCase() === String(it.name || '').toLowerCase()) : null;
        return {
          key: newKey(), targetKey: match || prodMatch?.key || '', rawName: it.name,
          quantity: String(it.quantity || ''), unit: it.unit || '',
          unit_price: String(it.unit_price || ''), total_price: String(it.total_price || (it.quantity && it.unit_price ? Math.round(it.quantity * it.unit_price) : '')),
        };
      });
      if (scanned.length) setLines(scanned);
    } catch (e: any) { setError(e.message || 'Scan gagal'); }
    finally { setScanning(false); }
  };

  const submit = async () => {
    setError('');
    const valid = lines.filter(l => l.targetKey && Number(l.quantity) > 0);
    if (!valid.length) { setError('Isi minimal satu baris: pilih bahan/produk dan jumlahnya.'); return; }
    const unmatched = lines.filter(l => !l.targetKey && (l.rawName || l.quantity));
    if (unmatched.length) { setError(`Ada ${unmatched.length} baris belum dicocokkan: ${unmatched.map(l => l.rawName || 'baris kosong').join(', ')}. Pilih bahan/produk, atau pilih "Lainnya" kalau bukan stok.`); return; }
    const noName = valid.filter(l => (l.targetKey === '__other' || l.targetKey === '__new_ing' || l.targetKey === '__new_prod') && !(l.newName || l.rawName || '').trim());
    if (noName.length) { setError('Baris "Lainnya" / bahan baru / produk baru harus diisi namanya.'); return; }
    const noPrice = valid.filter(l => l.targetKey === '__new_prod' && !(Number(l.newSellPrice) > 0));
    if (noPrice.length) { setError('Produk baru butuh harga jual — itu yang dipakai di kasir.'); return; }
    if (payMode === 'utang' && Number(paidAmount || 0) >= total) { setError('Kalau belum lunas, nominal dibayar harus lebih kecil dari total.'); return; }

    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        outlet_id: outletId,
        supplier_id: supplierChoice && supplierChoice !== '__new' ? supplierChoice : null,
        supplier_name: supplierChoice === '__new' ? supplierName.trim() || null : null,
        invoice_no: invoiceNo || null,
        photo_url: photoUrl,
        notes: notes || null,
        received_at: receivedAt ? new Date(receivedAt + 'T12:00:00').toISOString() : null,
        paid_amount: payMode === 'lunas' ? null : Number(paidAmount || 0),
        due_at: payMode === 'utang' && dueAt ? new Date(dueAt + 'T12:00:00').toISOString() : null,
        items: valid.map(l => {
          const base = {
            quantity: Number(l.quantity),
            unit: l.unit || null,
            unit_price: Number(l.unit_price) || (Number(l.total_price) / Number(l.quantity)) || 0,
            total_price: Number(l.total_price) || null,
          };
          const name = (l.newName || l.rawName || '').trim();
          if (l.targetKey === '__other') return { ...base, name };
          if (l.targetKey === '__new_ing') return { ...base, new_ingredient: { name, base_unit: l.newBaseUnit || null } };
          if (l.targetKey === '__new_prod') return { ...base, new_product: { name, sell_price: Number(l.newSellPrice) } };
          const t = targetByKey[l.targetKey];
          return { ...base, ingredient_id: t.kind === 'ingredient' ? t.id : null, product_id: t.kind === 'product' ? t.id : null };
        }),
      };
      const saved = await createPurchase(payload);
      onSaved(saved);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="Catat Nota Belanja" onClose={onClose} wide>
      <div className="space-y-5">
        {/* Foto / scan */}
        <label className={`flex items-center gap-3 rounded-xl border-2 border-dashed p-4 cursor-pointer transition ${scanning ? 'border-blue-300 bg-blue-50' : 'border-gray-200 hover:border-blue-300'}`}>
          <input type="file" accept="image/*" capture="environment" className="hidden" disabled={scanning} onChange={e => { const f = e.target.files?.[0]; if (f) handleScan(f); e.target.value = ''; }} />
          {scanning ? <Loader2 className="w-6 h-6 text-blue-500 animate-spin shrink-0" /> : <Camera className="w-6 h-6 text-blue-500 shrink-0" />}
          <div className="text-sm">
            <p className="font-semibold text-gray-900">{scanning ? 'Membaca nota…' : photoUrl ? 'Foto tersimpan — scan ulang?' : 'Foto nota, biar AI yang ngisi barisnya'}</p>
            <p className="text-gray-500">JPG/PNG maks 10MB. Hasilnya tetap kamu cek dulu sebelum disimpan.</p>
          </div>
        </label>

        {/* Header nota */}
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-1">
            <label className="text-xs font-semibold text-gray-500">Supplier</label>
            <select value={supplierChoice} onChange={e => setSupplierChoice(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="">Tanpa supplier (pasar / eceran)</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              <option value="__new">+ Supplier baru…</option>
            </select>
            {supplierChoice === '__new' && (
              <input value={supplierName} onChange={e => setSupplierName(e.target.value)} placeholder="Nama supplier" className="mt-2 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            )}
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500">Tanggal</label>
            <input type="date" value={receivedAt} onChange={e => setReceivedAt(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500">No. nota (opsional)</label>
            <input value={invoiceNo} onChange={e => setInvoiceNo(e.target.value)} placeholder="NT-0012" className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        {/* Baris */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-gray-500">Barang yang dibeli</label>
            {!isPro && <span className="text-xs text-gray-400">Bahan baku & resep ada di paket Pro — di Starter, catat produk jadi.</span>}
          </div>
          <div className="space-y-2">
            {lines.map(l => {
              const t = targetByKey[l.targetKey];
              return (
                <div key={l.key} className={`rounded-lg border p-2.5 ${!l.targetKey && l.rawName ? 'border-amber-300 bg-amber-50' : 'border-gray-200'}`}>
                  {l.rawName && !l.targetKey && <p className="text-xs text-amber-700 mb-1">Dari nota: <b>{l.rawName}</b> — cocokkan ke bahan/produk:</p>}
                  <div className="grid gap-2 sm:grid-cols-[1.6fr_0.7fr_0.8fr_1fr_1fr_auto]">
                    <select value={l.targetKey} onChange={e => updateLine(l.key, { targetKey: e.target.value, newName: l.newName || l.rawName || '' })} className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0">
                      <option value="">Pilih bahan / produk…</option>
                      {ingredientTargets.length > 0 && <optgroup label="Bahan baku">{ingredientTargets.map(x => <option key={x.key} value={x.key}>{x.name}{x.hint ? ` · ${x.hint}` : ''}</option>)}</optgroup>}
                      {productTargets.length > 0 && <optgroup label="Produk">{productTargets.map(x => <option key={x.key} value={x.key}>{x.name}{x.hint ? ` · ${x.hint}` : ''}</option>)}</optgroup>}
                      <optgroup label="Belum ada di daftar">
                        {isPro && <option value="__new_ing">+ Bahan baku baru…</option>}
                        <option value="__new_prod">+ Produk jadi baru…</option>
                        <option value="__other">Lainnya — bukan stok (gas, plastik, tisu)</option>
                      </optgroup>
                    </select>
                    <input type="number" inputMode="decimal" min="0" step="any" value={l.quantity} onChange={e => updateLine(l.key, { quantity: e.target.value })} placeholder="Jml" className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0" />
                    <select value={l.unit} onChange={e => updateLine(l.key, { unit: e.target.value })} className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0">
                      <option value="">{t?.unit ? `satuan: ${t.unit}` : 'satuan'}</option>
                      {UNIT_GROUPS.map(g => <optgroup key={g.label} label={g.label}>{g.units.map(u => <option key={u.v} value={u.v}>{u.l}</option>)}</optgroup>)}
                    </select>
                    <input type="number" inputMode="numeric" min="0" value={l.unit_price} onChange={e => updateLine(l.key, { unit_price: e.target.value })} placeholder="Harga/satuan" className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0" />
                    <input type="number" inputMode="numeric" min="0" value={l.total_price} onChange={e => updateLine(l.key, { total_price: e.target.value })} placeholder="Total" className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0 font-semibold" />
                    <button onClick={() => setLines(ls => ls.length > 1 ? ls.filter(x => x.key !== l.key) : ls)} className="p-2 text-gray-400 hover:text-red-500"><X className="w-4 h-4" /></button>
                  </div>
                  {t?.kind === 'ingredient' && l.unit && l.unit !== t.unit && (
                    <p className="text-xs text-gray-500 mt-1">Dikonversi ke {t.unit} otomatis (mis. 2 kg → 2000 gram).</p>
                  )}
                  {(l.targetKey === '__other' || l.targetKey === '__new_ing' || l.targetKey === '__new_prod') && (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1.6fr_1fr_1fr]">
                      <input value={l.newName ?? ''} onChange={e => updateLine(l.key, { newName: e.target.value })}
                        placeholder={l.targetKey === '__other' ? 'Nama, mis. Gas 3kg' : l.targetKey === '__new_ing' ? 'Nama bahan, mis. Susu UHT' : 'Nama produk, mis. Roti Bakar'}
                        className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0" />
                      {l.targetKey === '__new_ing' && (
                        <select value={l.newBaseUnit ?? ''} onChange={e => updateLine(l.key, { newBaseUnit: e.target.value })} className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0">
                          <option value="">Satuan stok: ikut nota</option>
                          <option value="gram">gram</option><option value="ml">ml</option><option value="pcs">pcs</option><option value="bungkus">bungkus</option>
                        </select>
                      )}
                      {l.targetKey === '__new_prod' && (
                        <input type="number" min="0" value={l.newSellPrice ?? ''} onChange={e => updateLine(l.key, { newSellPrice: e.target.value })} placeholder="Harga jual di kasir" className="border border-gray-200 rounded-lg px-2 py-2 text-sm min-w-0" />
                      )}
                      <p className="text-xs text-gray-500 self-center">
                        {l.targetKey === '__other' ? 'Ikut total & utang, stok nggak disentuh.' : l.targetKey === '__new_ing' ? 'Dibikin otomatis waktu nota disimpan.' : 'Dibikin dengan stok awal = jumlah di nota.'}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <button onClick={() => setLines(ls => [...ls, { key: newKey(), targetKey: '', quantity: '', unit: '', unit_price: '', total_price: '' }])} className="mt-2 text-sm text-blue-600 font-medium hover:underline">+ Tambah baris</button>
        </div>

        {/* Bayar */}
        <div className="rounded-xl bg-gray-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Total nota</span>
            <span className="text-xl font-bold text-gray-900 tabular-nums">{rp(total)}</span>
          </div>
          <div className="flex gap-2">
            {(['lunas', 'utang'] as const).map(m => (
              <button key={m} onClick={() => setPayMode(m)} className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition ${payMode === m ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 bg-white text-gray-600'}`}>
                {m === 'lunas' ? 'Sudah dibayar lunas' : 'Belum lunas / sebagian'}
              </button>
            ))}
          </div>
          {payMode === 'utang' && (
            <div className="grid gap-2 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-gray-500">Sudah dibayar</label>
                <input type="number" min="0" value={paidAmount} onChange={e => setPaidAmount(e.target.value)} placeholder="0" className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500">Jatuh tempo</label>
                <input type="date" value={dueAt} onChange={e => setDueAt(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                <p className="text-xs text-gray-400 mt-1">Kosong = ikut tempo supplier (atau 7 hari).</p>
              </div>
            </div>
          )}
        </div>

        <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Catatan (opsional)" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />

        {error && <p className="text-sm text-red-600 flex items-start gap-2"><AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Batal</button>
          <button onClick={submit} disabled={saving} className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />} Simpan Nota
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Modal: detail nota + bayar utang ──────────────────────────────────

function DetailModal({ purchase, onClose, onPaid }: { purchase: Purchase; onClose: () => void; onPaid: (p: Purchase) => void }) {
  const [amount, setAmount] = useState(String(Math.round(Number(purchase.outstanding_amount))));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const utang = Number(purchase.outstanding_amount) > 0;

  return (
    <Modal title={purchase.po_number} onClose={onClose}>
      <div className="space-y-4">
        <div className="text-sm text-gray-600">
          <p><b className="text-gray-900">{purchase.supplier_name || 'Tanpa supplier'}</b> · {tgl(purchase.received_at)}{purchase.invoice_no ? ` · No. ${purchase.invoice_no}` : ''}</p>
          {purchase.notes && <p className="text-gray-500">{purchase.notes}</p>}
        </div>
        {purchase.photo_url && <a href={purchase.photo_url} target="_blank" rel="noreferrer" className="text-sm text-blue-600 hover:underline">Lihat foto nota</a>}
        <div className="divide-y divide-gray-100 border border-gray-200 rounded-lg">
          {purchase.items.map(i => {
            const before = Number(i.cost_before), after = Number(i.cost_after);
            const changed = i.cost_before != null && i.cost_after != null && before !== after;
            return (
              <div key={i.id} className="px-3 py-2 text-sm flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900">{i.name}{i.is_other && <span className="ml-2 text-[10px] font-semibold uppercase text-gray-400">bukan stok</span>}</p>
                  <p className="text-gray-500">{i.quantity} {i.unit || ''}{i.qty_base && i.qty_base !== i.quantity ? ` (= ${i.qty_base})` : ''} × {rp(i.unit_price)}</p>
                  {changed && (
                    <p className={`text-xs flex items-center gap-1 ${after > before ? 'text-amber-600' : 'text-green-600'}`}>
                      {after > before ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      HPP {rpDec(before)} → {rpDec(after)}
                    </p>
                  )}
                </div>
                <p className="font-semibold tabular-nums shrink-0">{rp(i.total_price)}</p>
              </div>
            );
          })}
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-sm space-y-1">
          <div className="flex justify-between"><span className="text-gray-500">Total</span><b className="tabular-nums">{rp(purchase.total_amount)}</b></div>
          <div className="flex justify-between"><span className="text-gray-500">Dibayar</span><span className="tabular-nums">{rp(purchase.paid_amount)}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Sisa utang</span><b className={`tabular-nums ${utang ? 'text-amber-700' : 'text-green-700'}`}>{utang ? rp(purchase.outstanding_amount) : 'Lunas'}</b></div>
          {utang && purchase.due_at && <div className="flex justify-between"><span className="text-gray-500">Jatuh tempo</span><span>{tgl(purchase.due_at)}</span></div>}
        </div>
        {utang && (
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className="text-xs font-semibold text-gray-500">Bayar utang</label>
              <input type="number" min="1" value={amount} onChange={e => setAmount(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </div>
            <button
              disabled={busy || !(Number(amount) > 0)}
              onClick={async () => {
                setBusy(true); setError('');
                try { onPaid(await payPurchase(purchase.id, Number(amount), purchase.row_version)); }
                catch (e: any) { setError(e.message); }
                finally { setBusy(false); }
              }}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Wallet className="w-4 h-4" /> {busy ? 'Menyimpan…' : 'Catat Bayar'}
            </button>
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}

// ── Modal: supplier ───────────────────────────────────────────────────

function SupplierModal({ initial, onClose, onSaved }: { initial: Partial<Supplier>; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: initial.name || '', phone: initial.phone || '', address: initial.address || '',
    notes: initial.notes || '', payment_terms_days: String(initial.payment_terms_days ?? 0),
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const isEdit = !!initial.id;

  const submit = async () => {
    setBusy(true); setError('');
    try {
      const payload = { ...form, payment_terms_days: Number(form.payment_terms_days) || 0 };
      if (isEdit) await updateSupplier(initial.id!, { ...payload, row_version: initial.row_version });
      else await createSupplier(payload);
      onSaved();
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <Modal title={isEdit ? 'Ubah Supplier' : 'Supplier Baru'} onClose={onClose}>
      <div className="space-y-3">
        {([['name', 'Nama', 'Toko Berkah'], ['phone', 'No. HP / WA', '0812…'], ['address', 'Alamat', 'Pasar Petisah'], ['notes', 'Catatan', 'Kirim tiap Senin']] as const).map(([k, label, ph]) => (
          <div key={k}>
            <label className="text-xs font-semibold text-gray-500">{label}</label>
            <input value={(form as any)[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} placeholder={ph} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </div>
        ))}
        <div>
          <label className="text-xs font-semibold text-gray-500">Tempo bayar (hari)</label>
          <input type="number" min="0" max="365" value={form.payment_terms_days} onChange={e => setForm(f => ({ ...f, payment_terms_days: e.target.value }))} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          <p className="text-xs text-gray-400 mt-1">0 = bayar cash. Nota yang belum lunas otomatis dapet jatuh tempo segini.</p>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Batal</button>
          <button onClick={submit} disabled={busy || !form.name.trim()} className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">{busy ? 'Menyimpan…' : 'Simpan'}</button>
        </div>
      </div>
    </Modal>
  );
}

// ── Modal shell ───────────────────────────────────────────────────────

function Modal({ title, onClose, children, wide }: { title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4" onClick={onClose}>
      <div className={`bg-white w-full ${wide ? 'sm:max-w-3xl' : 'sm:max-w-lg'} rounded-t-2xl sm:rounded-2xl max-h-[92vh] overflow-y-auto`} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-3 flex items-center justify-between z-10">
          <h2 className="font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
