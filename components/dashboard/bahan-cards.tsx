'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import { createPurchase, restockIngredient, updateIngredient, updateProduct } from '@/app/actions/api';

// Kartu konfirmasi alat bahan Selaris AI (backend/services/selaris_bahan.py).
// Angka di kartu dihitung backend. Simpan memanggil endpoint yang sama dengan
// halaman Bahan Baku dan Nota Belanja, jadi izin, audit, dan HPP rata-rata
// bergerak diputuskan di sana, bukan di kartu ini.

type Impact = { produk: string; modal_lama: number | null; modal_baru: number | null; margin_baru: number | null; harga_jual: number | null };
export type IngredientPriceCard = {
  type: 'ingredient_price'; ingredient_id: string; row_version: number; bahan: string; base_unit: string;
  harga_lama: number; jumlah_lama: number; harga_baru: number; jumlah_baru: number; biaya_lama: number; biaya_baru: number; produk: Impact[];
};
type StockLine = { ingredient_id: string; bahan: string; jumlah: number; satuan: string; jumlah_dasar: number; base_unit: string;
  stok_lama: number; stok_baru: number; harga_total: number | null; biaya_lama: number; biaya_baru: number | null };
export type StockInCard = {
  type: 'stock_in'; outlet_id: string; pemasok: string | null; lines: StockLine[]; nota: boolean; total: number | null;
  produk: Impact[]; masalah: { bahan: string; masalah: string; kandidat?: string[] }[];
};
type SellLine = { product_id: string; row_version: number; menu: string; cara: string; harga_lama: number; harga_baru: number;
  modal: number | null; margin_lama: number | null; margin_baru: number | null; di_bawah_modal: boolean; lonjakan: boolean;
  varian: { nama: string; lama: number; baru: number }[] };
export type SellPriceCard = { type: 'sell_price'; lines: SellLine[]; masalah: { menu: string; masalah: string; kandidat?: string[] }[] };
export type BahanCard = IngredientPriceCard | StockInCard | SellPriceCard;
export const isBahanCard = (event: { type?: string }) => ['ingredient_price', 'stock_in', 'sell_price'].includes(event.type || '');

const rp = (n: number | null | undefined) => 'Rp ' + Math.round(Number(n) || 0).toLocaleString('id-ID');
const qty = (n: number, unit: string) => `${Number(n.toFixed(2)).toLocaleString('id-ID')} ${unit}`;
// Biaya per satuan dasar sering pecahan kecil (Rp 0,038/gram); tampilkan per 1.000 untuk gram/ml.
function perUnit(cost: number, unit: string) {
  return unit === 'gram' ? `${rp(cost * 1000)}/kg` : unit === 'ml' ? `${rp(cost * 1000)}/liter` : `${rp(cost)}/${unit}`;
}

function ImpactList({ rows }: { rows: Impact[] }) {
  if (!rows.length) return null;
  return <>
    <p className="saran-note">Modal per porsi yang ikut berubah:</p>
    <ul className="saran-rows">{rows.map(r => <li key={r.produk}>
      <span>{r.produk}</span>
      <span className="saran-num">{rp(r.modal_lama)} ke {rp(r.modal_baru)}{r.margin_baru != null ? ` · margin ${r.margin_baru.toLocaleString('id-ID')}%` : ''}</span>
    </li>)}</ul>
  </>;
}

export function BahanCardView({ card }: { card: BahanCard }) {
  return card.type === 'ingredient_price' ? <PriceCard card={card} /> : card.type === 'sell_price' ? <SellCard card={card} /> : <StockCard card={card} />;
}

function PriceCard({ card }: { card: IngredientPriceCard }) {
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle'), [error, setError] = useState('');
  async function save() {
    if (state !== 'idle') return;
    setState('saving'); setError('');
    try {
      await updateIngredient(card.ingredient_id, { buy_price: card.harga_baru, buy_qty: card.jumlah_baru, row_version: card.row_version });
      setState('saved');
    } catch (e) {
      setState('idle');
      const message = e instanceof Error ? e.message : '';
      setError(/refresh|diubah/i.test(message) ? 'Harga bahan ini sudah diubah dari tempat lain. Minta Selaris AI menyiapkan ulang.' : message || 'Harga belum tersimpan. Coba lagi.');
    }
  }
  return <section className="saran-card mt-3" aria-label={`Ubah harga ${card.bahan}`}>
    <span className="saran-tag saran-brand">Ubah harga beli</span>
    <p className="saran-prop">{card.bahan}</p>
    <ul className="saran-rows">
      <li><span>Sekarang</span><span className="saran-num">{rp(card.harga_lama)} per {qty(card.jumlah_lama, card.base_unit)}</span></li>
      <li><span>Jadi</span><span className="saran-num">{rp(card.harga_baru)} per {qty(card.jumlah_baru, card.base_unit)}</span></li>
      <li><span>Modal bahan</span><span className="saran-num">{perUnit(card.biaya_lama, card.base_unit)} ke {perUnit(card.biaya_baru, card.base_unit)}</span></li>
    </ul>
    <ImpactList rows={card.produk} />
    <p className="saran-note">Stok tidak berubah. Kalau barangnya baru datang, catat sebagai bahan masuk supaya harganya dirata-rata dengan stok lama.</p>
    {error && <p className="saran-error" role="alert">{error}</p>}
    {state === 'saved'
      ? <p className="saran-notice" role="status">Harga {card.bahan} tersimpan. Modal produk di atas sudah memakai harga baru.</p>
      : <div className="saran-acts">
          <button type="button" className="saran-btn saran-primary" disabled={state === 'saving'} onClick={save}>{state === 'saving' ? 'Menyimpan…' : 'Simpan harga'}</button>
          <Link className="saran-btn inline-flex items-center" href="/dashboard/bahan-baku">Buka Bahan Baku</Link>
        </div>}
  </section>;
}

function StockCard({ card }: { card: StockInCard }) {
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle'), [error, setError] = useState('');
  const [unpaid, setUnpaid] = useState(false);
  // Satu id per kartu: kalau koneksi putus lalu ditekan lagi, server mengenali nota yang sama.
  const requestId = useRef(crypto.randomUUID());
  const restocked = useRef(new Set<string>());
  const priced = card.lines.filter(l => l.harga_total), plain = card.lines.filter(l => !l.harga_total);
  const savedPurchase = useRef(false);

  async function save() {
    if (state !== 'idle') return;
    setState('saving'); setError('');
    try {
      if (priced.length && !savedPurchase.current) {
        const result = await createPurchase({
          client_request_id: requestId.current, outlet_id: card.outlet_id, supplier_name: card.pemasok || undefined,
          notes: 'Dicatat lewat Selaris AI', paid_amount: unpaid ? 0 : null,
          items: priced.map(l => ({ ingredient_id: l.ingredient_id, quantity: l.jumlah, unit: l.satuan,
            unit_price: Math.round((l.harga_total! / l.jumlah) * 100) / 100, total_price: l.harga_total })),
        });
        if (!result.success) throw new Error(result.message);
        savedPurchase.current = true;
      }
      for (const l of plain) {
        if (restocked.current.has(l.ingredient_id)) continue;
        await restockIngredient(l.ingredient_id, { outlet_id: card.outlet_id, quantity: l.jumlah_dasar, notes: 'Dicatat lewat Selaris AI' });
        restocked.current.add(l.ingredient_id);
      }
      setState('saved');
    } catch (e) {
      setState('idle');
      setError(e instanceof Error && e.message ? e.message : 'Belum tersimpan. Coba lagi.');
    }
  }

  return <section className="saran-card mt-3" aria-label="Bahan masuk">
    <span className="saran-tag saran-brand">{card.nota ? 'Nota belanja' : 'Bahan masuk'}</span>
    <p className="saran-prop">{card.nota && card.pemasok ? card.pemasok : card.lines.map(l => l.bahan).join(', ')}</p>
    <ul className="saran-rows">{card.lines.map(l => <li key={l.ingredient_id}>
      <span>{l.bahan}<em className="saran-fact">+{qty(l.jumlah, l.satuan)}</em></span>
      <span className="saran-num">Stok {qty(l.stok_lama, l.base_unit)} ke {qty(l.stok_baru, l.base_unit)}{l.harga_total ? ` · ${rp(l.harga_total)}` : ''}</span>
    </li>)}</ul>
    {priced.some(l => l.biaya_baru != null && Math.abs(l.biaya_baru - l.biaya_lama) > 1e-9) && <ul className="saran-rows">{priced.map(l => <li key={l.ingredient_id}>
      <span>Modal {l.bahan}</span><span className="saran-num">{perUnit(l.biaya_lama, l.base_unit)} ke {perUnit(l.biaya_baru ?? 0, l.base_unit)}</span>
    </li>)}</ul>}
    <ImpactList rows={card.produk} />
    {card.total != null && <div className="saran-chips"><span className="saran-chip">Total nota {rp(card.total)}</span></div>}
    {card.nota && state !== 'saved' && <label className="saran-note flex items-center gap-2">
      <input type="checkbox" checked={unpaid} onChange={e => setUnpaid(e.target.checked)} /> Belum dibayar, catat sebagai utang
    </label>}
    {plain.length > 0 && card.nota && <p className="saran-note">{plain.map(l => l.bahan).join(', ')} dicatat sebagai stok masuk tanpa harga.</p>}
    {card.masalah.length > 0 && <p className="saran-note">Belum masuk kartu: {card.masalah.map(m => `${m.bahan} (${m.masalah}${m.kandidat?.length ? `: ${m.kandidat.join(', ')}` : ''})`).join('; ')}.</p>}
    {error && <p className="saran-error" role="alert">{error}</p>}
    {state === 'saved'
      ? <p className="saran-notice" role="status">{card.nota ? 'Nota tersimpan di Pembelian. ' : ''}Stok sudah bertambah.</p>
      : <div className="saran-acts">
          <button type="button" className="saran-btn saran-primary" disabled={state === 'saving'} onClick={save}>{state === 'saving' ? 'Menyimpan…' : card.nota ? 'Simpan nota' : 'Simpan stok masuk'}</button>
          <Link className="saran-btn inline-flex items-center" href={card.nota ? '/dashboard/pembelian' : '/dashboard/bahan-baku'}>{card.nota ? 'Buka Pembelian' : 'Buka Bahan Baku'}</Link>
        </div>}
  </section>;
}

// Harga jual: hitungan awal dari backend (selaris_bahan.new_sell_price), tapi angkanya
// bisa diubah di sini sebelum Simpan. Margin ulang dihitung dari modal resep yang sama.
function SellCard({ card }: { card: SellPriceCard }) {
  const [prices, setPrices] = useState(() => Object.fromEntries(card.lines.map(l => [l.product_id, String(l.harga_baru)])));
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle'), [error, setError] = useState('');
  const done = useRef(new Set<string>()), [savedIds, setSavedIds] = useState<string[]>([]);
  const value = (l: SellLine) => Math.round(Number(prices[l.product_id]) || 0);
  const margin = (l: SellLine, price: number) => l.modal != null && price > 0 ? Math.round((price - l.modal) / price * 1000) / 10 : null;
  const invalid = card.lines.some(l => value(l) <= 0);

  async function save() {
    if (state !== 'idle' || invalid) return;
    setState('saving'); setError('');
    for (const l of card.lines) {
      if (done.current.has(l.product_id)) continue;
      const result = await updateProduct(l.product_id, { base_price: value(l), row_version: l.row_version });
      if (!result.success) {
        setState('idle');
        setError(/modified|concurrent/i.test(String(result.message)) ? `${l.menu} baru saja diubah dari tempat lain. Minta Selaris AI menyiapkan ulang.` : `${l.menu}: ${result.message || 'belum tersimpan'}`);
        return;
      }
      done.current.add(l.product_id);
      setSavedIds([...done.current]);
    }
    setState('saved');
  }

  return <section className="saran-card mt-3" aria-label="Ubah harga jual">
    <span className="saran-tag saran-brand">Ubah harga jual</span>
    <ul className="saran-rows">{card.lines.map(l => {
      const price = value(l), m = margin(l, price);
      return <li key={l.product_id} className="flex-col items-stretch">
        <div className="flex justify-between gap-3"><span>{l.menu}<em className="saran-fact">{l.cara}</em></span><span className="saran-num">{rp(l.harga_lama)} ke</span></div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="flex items-center gap-2 text-sm">Rp<input aria-label={`Harga baru ${l.menu}`} className="hpp-control w-32" inputMode="numeric" value={prices[l.product_id]} disabled={state !== 'idle' || savedIds.includes(l.product_id)} onChange={e => setPrices(v => ({ ...v, [l.product_id]: e.target.value.replace(/\D/g, '') }))} /></label>
          <span className="saran-num">{l.modal != null ? `modal ${rp(l.modal)} · margin ${l.margin_lama ?? '?'}% ke ${m ?? '?'}%` : 'belum ada resep, margin tidak dihitung'}</span>
        </div>
        {l.modal != null && price > 0 && price <= l.modal && <span className="saran-chip saran-chip-bad">Di bawah modal</span>}
        {l.harga_lama > 0 && (price > l.harga_lama * 3 || price * 3 < l.harga_lama) && <span className="saran-chip saran-chip-bad">Periksa angkanya, beda jauh dari harga lama</span>}
        {l.varian.length > 0 && <span className="saran-note">Varian ikut bergeser: {l.varian.map(v => `${v.nama} ${rp(v.lama)} ke ${rp(v.lama + price - l.harga_lama)}`).join(', ')}</span>}
      </li>;
    })}</ul>
    {card.masalah.length > 0 && <p className="saran-note">Belum masuk kartu: {card.masalah.map(m => `${m.menu} (${m.masalah}${m.kandidat?.length ? `: ${m.kandidat.join(', ')}` : ''})`).join('; ')}.</p>}
    <p className="saran-note">Harga baru dipakai kasir dan toko online setelah aplikasi kasir sinkron.</p>
    {error && <p className="saran-error" role="alert">{error}</p>}
    {state === 'saved'
      ? <p className="saran-notice" role="status">Harga jual tersimpan.</p>
      : <div className="saran-acts">
          <button type="button" className="saran-btn saran-primary" disabled={state === 'saving' || invalid} onClick={save}>{state === 'saving' ? 'Menyimpan…' : 'Simpan harga jual'}</button>
          <Link className="saran-btn inline-flex items-center" href="/dashboard/menu">Buka Menu</Link>
        </div>}
  </section>;
}
