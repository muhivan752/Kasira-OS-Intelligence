'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { applySuggestion, getSuggestions, refreshSuggestions, skipSuggestion, undoSuggestion } from '@/app/actions/suggestions';
import { approveHppChat } from '@/app/actions/api';

// Kartu Saran Selaris. Semua angka datang dari backend (services/suggestions.py,
// dihitung kode); layar ini hanya merakit kalimat dan tombol.
const rp = (n: number | string | null | undefined) => 'Rp ' + Math.round(Number(n) || 0).toLocaleString('id-ID');
const pct = (n: number | null | undefined) => (n ?? 0).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + '%';
const num = (n: number) => n.toLocaleString('id-ID', { maximumFractionDigits: 2 });
const REASONS = ['Sudah tahu', 'Angkanya tidak sesuai', 'Nanti saja', 'Tidak relevan'];
const perBulk = (unit: string) => (unit === 'gram' ? 1000 : unit === 'ml' ? 1000 : 1);
const bulkUnit = (unit: string) => (unit === 'gram' ? 'kg' : unit === 'ml' ? 'liter' : unit);

function runsOut(iso?: string | null) {
  if (!iso) return '';
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long' });
}

type Card = { tag: string; tone: 'urgent' | 'warn' | 'brand'; seen: string; prop: string;
  rows: [string, string, string?][]; chips: [string, 'good' | 'bad' | 'plain'][]; note?: string;
  primary?: string; editable?: { label: string; value: number; step: number; key: 'new_price' | 'qty' } };

function describe(s: any): Card {
  const f = s.facts || {};
  if (s.kind === 'stock_low') {
    const owner = s.proposal != null;
    const sup = f.supplier;
    return { tag: 'Mendesak · stok hampir habis', tone: 'urgent',
      seen: f.days_left != null
        ? `Sisa ${f.name} ${num(f.stock)} ${f.stock_unit}. Pemakaian rata-rata ${num(f.avg_daily)} ${f.avg_unit} per hari, jadi habis sekitar ${runsOut(f.runs_out_on)}.`
        : `Stok ${f.name} sudah di bawah batas minimum.`,
      prop: owner ? `Pesan ${num(f.order_qty)} ${f.order_unit} ${sup ? 'ke ' + sup.name : f.name}?` : 'Pemilik usaha sudah diberi tahu.',
      rows: owner ? [
        ['Harga terakhir', `${rp(f.price_per_unit * perBulk(f.price_unit))}/${bulkUnit(f.price_unit)}`],
        ['Perkiraan total', rp(f.order_total)],
        ['Cukup untuk', `± ${f.cover_days} hari`],
      ] : [],
      chips: [], note: owner ? `${sup?.phone ? `Kontak ${sup.name}: ${sup.phone}. ` : ''}Stok bertambah saat pembelian dicatat di menu Pembelian.` : undefined,
      primary: owner ? 'Tandai sudah dipesan' : undefined,
      editable: owner ? { label: `Jumlah (${f.order_unit})`, value: f.order_qty, step: 0.5, key: 'qty' } : undefined };
  }
  if (s.kind === 'ingredient_price_up') {
    const t = f.top || {};
    const others = (f.products || []).slice(1).map((p: any) => p.name);
    return { tag: 'Harga bahan naik', tone: 'warn',
      seen: `Harga ${f.ingredient} di nota ${new Date(f.date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })} dari ${f.supplier} naik ${pct(f.pct)} (${rp(f.old_price)} jadi ${rp(f.new_price)} per ${f.unit}). Modal ${t.name} naik ${rp(t.cost_now - t.cost_before)} per porsi.`,
      prop: t.new_price ? `Naikkan harga ${t.name} jadi ${rp(t.new_price)}?` : `Periksa harga jual produk yang memakai ${f.ingredient}.`,
      rows: [['Harga sekarang', `${rp(t.base_price)} · margin ${pct(t.margin_now)}`],
        ...(t.new_price ? [['Harga usulan', `${rp(t.new_price)} · margin ${pct(t.margin_new)}`] as [string, string]] : [])],
      chips: [[`Tanpa perubahan: −${rp(f.monthly_loss)}/bulan`, 'bad']],
      note: others.length ? `Juga terdampak: ${others.join(', ')}.` : 'Dihitung dari penjualan 30 hari terakhir.',
      primary: t.new_price ? 'Naikkan harga' : undefined,
      editable: t.new_price ? { label: 'Harga baru', value: t.new_price, step: 500, key: 'new_price' } : undefined };
  }
  if (s.kind === 'thin_margin') {
    return { tag: 'Margin terlalu tipis', tone: 'warn',
      seen: `${f.name} dijual ${rp(f.base_price)} dengan modal ${rp(f.cost)}. Untungnya ${rp(f.profit_per_unit)} per porsi (${pct(f.margin)}).`,
      prop: `Naikkan harga ${f.name} jadi ${rp(f.new_price)}?`,
      rows: [['Margin sekarang', pct(f.margin)], ['Margin dengan harga usulan', pct(f.margin_new)], ['Terjual 30 hari terakhir', `${f.sold_30d} porsi`]],
      chips: [[`+${rp(f.monthly_gain)}/bulan jika penjualan tetap`, 'good']],
      primary: 'Naikkan harga', editable: { label: 'Harga baru', value: f.new_price, step: 500, key: 'new_price' } };
  }
  const p = f.preview;
  const margin = p?.total_cost && f.base_price ? (f.base_price - Number(p.total_cost)) / f.base_price * 100 : null;
  return { tag: 'Resep belum ada', tone: 'brand',
    seen: `${f.name} terjual ${f.sold_30d} kali dalam 30 hari, tapi belum punya resep. Modal dan stoknya belum terhitung.`,
    prop: p ? `Pakai resep perkiraan ini untuk ${f.name}?` : `Siapkan resep ${f.name} bersama Selaris AI?`,
    rows: p ? p.lines.map((l: any) => [l.name, `${l.qty ?? '?'} ${l.unit}${l.cost ? ' · ' + rp(l.cost) : ''}`, l.estimated ? 'perkiraan' : 'harga toko']) : [],
    chips: p?.total_cost ? [[`Modal ${rp(p.total_cost)}`, 'plain'], ...(margin != null ? [[`Margin ${pct(margin)}`, 'good'] as [string, 'good']] : [])] : [],
    note: p ? 'Takaran berlabel perkiraan adalah usulan umum. Cek dan koreksi lewat Ubah.' : undefined,
    primary: p?.ready ? 'Pakai resep' : 'Siapkan resep' };
}

export function SuggestionsPanel({ outletId }: { outletId?: string }) {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [asking, setAsking] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: string; value: number } | null>(null);

  const load = useCallback(async () => {
    if (!outletId) return;
    const res = await getSuggestions(outletId);
    // Gagal memuat = panel tidak tampil. Saran itu tambahan; Beranda tidak boleh jadi kotak error.
    if (res.success) setData(res.data);
  }, [outletId]);
  useEffect(() => { void load(); }, [load]);

  async function act(id: string, fn: () => Promise<any>, ok: string) {
    if (busy) return;
    setBusy(id); setNotice(''); setError('');
    try {
      const res = await fn();
      if (!res.success) { setError(res.message); return; }
      setNotice(ok); setAsking(null); setEditing(null);
      await load();
      return res.data;
    } finally { setBusy(null); }
  }

  async function apply(s: any, params?: any) {
    const done = await act(s.id, () => applySuggestion(s.id, params), s.kind === 'stock_low' ? 'Dicatat sudah dipesan.' : 'Diterapkan. Bisa dibatalkan kapan saja.');
    if (!done) return;
    if (s.kind === 'recipe_missing') {
      const ref = done.result?.hpp_session;
      if (ref?.ready && ref.fingerprint && !ref.replaces_recipe) {
        const approved = await approveHppChat(ref.id, ref.revision, ref.fingerprint, false, outletId);
        if (approved.success) { setNotice('Resep disimpan. Modal dan stok produk ini sekarang terhitung.'); await load(); return; }
      }
      if (ref?.id) router.push(`/dashboard/hpp/chat?conversation=${encodeURIComponent(ref.id)}`);
    }
  }

  async function edit(s: any) {
    if (s.kind === 'recipe_missing') {
      const done = await act(s.id, () => applySuggestion(s.id), '');
      const ref = done?.result?.hpp_session;
      if (ref?.id) router.push(`/dashboard/hpp/chat?conversation=${encodeURIComponent(ref.id)}`);
      return;
    }
    const c = describe(s);
    if (c.editable) setEditing({ id: s.id, value: c.editable.value });
  }

  if (!outletId || !data) return null;
  const open: any[] = data?.open || [];
  const decided: any[] = data?.decided || [];
  if (!open.length && !decided.length && !error) return null;

  return <section className="overview-panel saran" aria-labelledby="saran-judul">
    <header className="saran-head">
      <div><h2 id="saran-judul">Saran Selaris</h2>
        <p>{open.length ? `${open.length} hal perlu keputusan${data.monthly_impact ? `, dampak ${rp(data.monthly_impact)} per bulan` : ''}.` : 'Semua saran sudah diputuskan.'}</p></div>
      <button type="button" className="saran-link" onClick={() => act('refresh', () => refreshSuggestions(outletId), 'Selaris sedang memeriksa ulang. Muat ulang halaman sebentar lagi.')}>Periksa ulang</button>
    </header>
    <p className="sr-only" aria-live="polite">{notice}</p>
    {notice && <p className="saran-notice" role="status">{notice}</p>}
    {error && <p className="saran-error" role="alert">{error}</p>}
    <div className="saran-grid">
      {open.map(s => {
        const c = describe(s);
        const isEditing = editing?.id === s.id && c.editable;
        return <article key={s.id} className="saran-card" aria-busy={busy === s.id}>
          <span className={`saran-tag saran-${c.tone}`}>{c.tag}</span>
          <p className="saran-seen">{c.seen}</p>
          <p className="saran-prop">{c.prop}</p>
          {c.rows.length > 0 && <ul className="saran-rows">{c.rows.map(([k, v, badge], i) =>
            <li key={i}><span>{k}{badge && <em className={badge === 'perkiraan' ? 'saran-est' : 'saran-fact'}>{badge}</em>}</span><span className="saran-num">{v}</span></li>)}</ul>}
          {c.chips.length > 0 && <div className="saran-chips">{c.chips.map(([t, tone], i) => <span key={i} className={`saran-chip saran-chip-${tone}`}>{t}</span>)}</div>}
          {c.note && <p className="saran-note">{c.note}</p>}
          {isEditing && c.editable && <form className="saran-edit" onSubmit={e => { e.preventDefault(); void apply(s, { [c.editable!.key]: editing!.value }); }}>
            <label htmlFor={`saran-edit-${s.id}`}>{c.editable.label}</label>
            <input id={`saran-edit-${s.id}`} type="number" inputMode="decimal" min={c.editable.step} step={c.editable.step}
              value={editing!.value} onChange={e => setEditing({ id: s.id, value: Number(e.target.value) })} />
            <div className="saran-acts"><button type="submit" className="saran-btn saran-primary" disabled={!!busy}>Terapkan</button>
              <button type="button" className="saran-btn" onClick={() => setEditing(null)}>Batal</button></div>
          </form>}
          {!isEditing && asking === s.id && <div className="saran-why"><p>Kenapa diabaikan?</p>
            {REASONS.map(r => <button key={r} type="button" className="saran-btn saran-small" disabled={!!busy}
              onClick={() => act(s.id, () => skipSuggestion(s.id, r), 'Dicatat. Saran ini tidak diulang kecuali datanya berubah.')}>{r}</button>)}</div>}
          {!isEditing && asking !== s.id && s.can_apply && <div className="saran-acts">
            {c.primary && <button type="button" className="saran-btn saran-primary" disabled={!!busy} onClick={() => apply(s)}>{busy === s.id ? 'Memproses…' : c.primary}</button>}
            {(c.editable || s.kind === 'recipe_missing') && <button type="button" className="saran-btn" disabled={!!busy} onClick={() => edit(s)}>Ubah</button>}
            <button type="button" className="saran-btn saran-ghost" disabled={!!busy} onClick={() => setAsking(s.id)}>Abaikan</button>
          </div>}
        </article>;
      })}
    </div>
    {decided.length > 0 && <details className="saran-decided"><summary>Sudah diputuskan ({decided.length})</summary>
      <ul>{decided.map(s => <li key={s.id}>
        <span><b>{s.status === 'applied' ? 'Diterapkan' : s.status === 'undone' ? 'Dibatalkan' : 'Diabaikan'}</b> · {describe(s).prop.replace('?', '')}{s.skip_reason ? ` (${s.skip_reason})` : ''}</span>
        {s.can_undo && <button type="button" className="saran-link" disabled={!!busy} onClick={() => act(s.id, () => undoSuggestion(s.id), 'Dibatalkan. Data kembali seperti semula.')}>Batalkan</button>}
      </li>)}</ul></details>}
  </section>;
}
