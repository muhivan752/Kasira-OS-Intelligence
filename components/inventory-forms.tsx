'use client';

import { cloneElement, useId, useState } from 'react';
import { saveInventoryIngredient } from '@/app/actions/api';
import { hasRecordedStock, type InventoryIngredient } from '@/lib/ingredient-inventory';
import { convertHppQuantity, hppMoney, hppNumber, hppUnits } from '@/lib/hpp';

type IngredientPayload = Parameters<typeof saveInventoryIngredient>[0];
const purchaseUnits = ['gram', 'kg', 'ml', 'liter', 'pcs', 'bungkus'];
function Field({ label, children }: { label: string; children: React.ReactElement<{ id?: string }> }) {
  const id = useId();
  return <div className="flex min-w-0 flex-col gap-2"><label htmlFor={id} className="font-semibold">{label}</label>{cloneElement(children, { id })}</div>;
}

export function InventoryIngredientForm({ item, overhead, brandId, names, disabled, onDirty, onSave }: {
  item?: InventoryIngredient; overhead: boolean; brandId: string; names: string[]; disabled: boolean;
  onDirty: () => void; onSave: (payload: IngredientPayload) => Promise<void>;
}) {
  const [name, setName] = useState(item?.name ?? '');
  const [price, setPrice] = useState(item ? String(overhead ? item.overhead_cost_per_day ?? 0 : item.buy_price) : '');
  const [quantity, setQuantity] = useState(item ? String(item.buy_qty) : '');
  const [unit, setUnit] = useState(item?.base_unit ?? 'gram');
  const [error, setError] = useState('');
  const base = item?.base_unit ?? (unit === 'kg' ? 'gram' : unit === 'liter' ? 'ml' : unit);
  const canonical = convertHppQuantity(Number(quantity), unit, base);
  const validPrice = price.trim() !== '' && Number.isFinite(Number(price)) && Number(price) >= 0;
  const ready = name.trim() && validPrice && (overhead || quantity.trim() && canonical != null && Number.isFinite(canonical) && Number.isFinite(Number(price) / canonical));

  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (disabled) return;
    if (!ready) { setError(overhead ? 'Isi nama dan estimasi biaya yang valid.' : 'Isi nama, harga, dan jumlah pembelian lebih dari nol.'); return; }
    if (names.some(value => value.trim().toLocaleLowerCase('id') === name.trim().toLocaleLowerCase('id'))) {
      setError('Nama ini sudah ada. Gunakan bahan yang tersedia atau pilih nama lain.'); return;
    }
    setError('');
    await onSave({ brand_id: brandId, name: name.trim(), base_unit: overhead ? item?.base_unit ?? 'pcs' : base,
      unit_type: overhead ? item?.unit_type ?? 'COUNT' : item?.unit_type ?? (base === 'gram' ? 'WEIGHT' : base === 'ml' ? 'VOLUME' : 'COUNT'),
      buy_price: overhead ? Number(item?.buy_price ?? 0) : Number(price), buy_qty: overhead ? item?.buy_qty ?? 1 : canonical!,
      ingredient_type: overhead ? 'overhead' : 'recipe', ...(overhead ? { overhead_cost_per_day: Number(price) } : {}) });
  }
  return <form className="space-y-5" onSubmit={submit} onChange={onDirty} noValidate>
    <p className="text-muted">{overhead ? 'Estimasi pengeluaran per hari. Belum termasuk dalam HPP bahan per porsi.'
      : item ? 'Perubahan harga berlaku pada semua resep yang memakai bahan ini. Jumlah pembelian tidak mengubah stok.'
        : 'Isi sesuai pembelian Anda. Jumlah yang dibeli dipakai untuk menghitung biaya HPP; stok dicatat setelah bahan tersimpan.'}</p>
    <Field label={overhead ? 'Nama biaya' : 'Nama bahan'}><input className="hpp-control w-full" value={name} maxLength={200} disabled={disabled} required
      onChange={event => setName(event.target.value)} autoComplete="off" /></Field>
    <Field label={overhead ? 'Estimasi biaya per hari (Rp)' : 'Total harga pembelian (Rp)'}><input className="hpp-control w-full" type="number" min="0" step="any"
      inputMode="decimal" value={price} disabled={disabled} required onChange={event => setPrice(event.target.value)} /></Field>
    {!overhead && <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Jumlah yang dibeli"><input className="hpp-control w-full" type="number" min="0" step="any" inputMode="decimal"
          value={quantity} disabled={disabled} required onChange={event => setQuantity(event.target.value)} /></Field>
        <Field label="Satuan pembelian"><select className="hpp-control w-full" value={unit} disabled={disabled} onChange={event => setUnit(event.target.value)}>
          {(item ? hppUnits(item.base_unit) : purchaseUnits).map(value => <option key={value} value={value}>{value}</option>)}</select></Field>
      </div>
      {canonical != null && validPrice && <div className="inventory-message"><p className="font-semibold">Biaya HPP setelah disimpan: {hppMoney(Number(price) / canonical)} per {base}</p>
        {unit !== base && <p className="mt-1 text-muted">{hppNumber(Number(quantity))} {unit} dicatat sebagai {hppNumber(canonical)} {base}.</p>}</div>}
      {item && <p className="text-sm text-muted">Satuan stok tetap {item.base_unit}. Gunakan Tambah stok untuk mencatat bahan yang masuk.</p>}
    </>}
    {error && <p role="alert">{error}</p>}
    <button className="hpp-button hpp-primary w-full" disabled={disabled} type="submit">{item ? overhead ? 'Simpan biaya' : 'Simpan harga' : overhead ? 'Simpan biaya' : 'Simpan bahan'}</button>
  </form>;
}

export function InventoryStockForm({ item, disabled, onDirty, onSave }: {
  item: InventoryIngredient; disabled: boolean; onDirty: () => void; onSave: (quantity: number, notes: string) => Promise<void>;
}) {
  const [quantity, setQuantity] = useState(''), [unit, setUnit] = useState(item.base_unit), [notes, setNotes] = useState(''), [error, setError] = useState('');
  const canonical = convertHppQuantity(Number(quantity), unit, item.base_unit);
  const recorded = hasRecordedStock(item);
  const current = recorded ? Number(item.current_stock) : 0;
  const ready = quantity.trim() !== '' && canonical != null && Number.isFinite(canonical) && Number.isFinite(current + canonical);
  return <form className="space-y-5" noValidate onChange={onDirty} onSubmit={async event => {
    event.preventDefault(); if (disabled) return;
    if (!ready) { setError('Isi jumlah tambahan stok lebih dari nol.'); return; }
    setError(''); await onSave(canonical!, notes);
  }}>
    <div><p className="text-lg font-semibold">{item.name}</p><p className="mt-1 text-muted">Stok saat ini: {recorded ? `${hppNumber(current)} ${item.base_unit}` : 'belum dicatat'}.</p></div>
    <p className="text-muted">Masukkan bahan yang masuk. Jumlah ini akan ditambahkan ke stok yang tersedia.</p>
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Field label="Jumlah yang ditambahkan"><input className="hpp-control w-full" type="number" min="0" step="any" inputMode="decimal" value={quantity}
        disabled={disabled} required onChange={event => setQuantity(event.target.value)} /></Field>
      <Field label="Satuan tambahan stok"><select className="hpp-control w-full" value={unit} disabled={disabled} onChange={event => setUnit(event.target.value)}>
        {hppUnits(item.base_unit).map(value => <option key={value} value={value}>{value}</option>)}</select></Field>
    </div>
    {ready && <div className="inventory-message"><p>Tambahan: {hppNumber(canonical!)} {item.base_unit}</p>
      <p className="mt-1 font-semibold">Stok setelah disimpan: {hppNumber(current + canonical!)} {item.base_unit}</p>
      {!recorded && <p className="mt-1 text-muted">Ini menjadi catatan stok pertama bahan ini.</p>}</div>}
    <Field label="Catatan (opsional)"><textarea className="hpp-control w-full" rows={2} value={notes} maxLength={500} disabled={disabled} onChange={event => setNotes(event.target.value)} /></Field>
    {error && <p role="alert">{error}</p>}
    <button className="hpp-button hpp-primary w-full" disabled={disabled} type="submit">Simpan tambahan stok</button>
  </form>;
}
