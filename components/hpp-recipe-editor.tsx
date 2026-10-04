'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { loadHppRecipe, saveHppIngredient, saveHppRecipe } from '@/app/actions/api';
import { convertHppQuantity, existingHppQuantity, hppMoney, hppNumber, hppUnits } from '@/lib/hpp';
import type { HppIngredient, HppProduct, HppRecipe } from '@/lib/hpp';

type Row = { id: string; quantity: string; unit: string; optional: boolean; reviewed: boolean; notes?: string | null };
function recipeRows(recipe: HppRecipe | null, ingredients: HppIngredient[]): Row[] {
  return (recipe?.ingredients || []).map(item => {
    const ingredient = ingredients.find(i => i.id === item.ingredient_id);
    const unit = ingredient && item.quantity_unit === ingredient.base_unit ? hppUnits(ingredient.base_unit)[0] : item.quantity_unit;
    const quantity = unit !== item.quantity_unit ? convertHppQuantity(item.quantity, item.quantity_unit, unit) : item.quantity;
    return { id: item.ingredient_id, quantity: String(quantity ?? item.quantity), unit,
      optional: item.is_optional, reviewed: unit !== item.quantity_unit, notes: item.notes };
  });
}
type Props = { brandId: string; product: HppProduct; onSaved?: (recipe: HppRecipe) => void;
  onDirtyChange?: (dirty: boolean) => void; onBusyChange?: (busy: boolean) => void; onNext?: () => void };

export function HppRecipeEditor({ brandId, product, onSaved, onDirtyChange, onBusyChange, onNext }: Props) {
  const [ingredients, setIngredients] = useState<HppIngredient[]>([]);
  const [recipe, setRecipe] = useState<HppRecipe | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const writeLock = useRef(false);
  const [selected, setSelected] = useState('');
  const [ingredientForm, setIngredientForm] = useState<{ existing?: HppIngredient; name: string; price: string; quantity: string; unit: string } | null>(null);
  const [ingredientError, setIngredientError] = useState('');
  const [ingredientNotice, setIngredientNotice] = useState('');
  const [reload, setReload] = useState(0);
  const addSelect = useRef<HTMLSelectElement>(null);
  const refocusAdd = useRef(false);
  useEffect(() => {
    if (!busy && refocusAdd.current) { addSelect.current?.focus(); refocusAdd.current = false; }
  }, [busy]);

  useEffect(() => {
    let current = true;
    setLoading(true); setLoadError(''); setSaved(false); setDirty(false); onDirtyChange?.(false);
    setIngredientForm(null); setIngredientNotice(''); setError(''); setSelected('');
    loadHppRecipe(brandId, product.id).then(result => {
      if (!current) return;
      if (!result.success) setLoadError(result.message);
      else {
        setIngredients(result.ingredients);
        setRecipe(result.recipe);
        setRows(recipeRows(result.recipe, result.ingredients));
      }
      setLoading(false);
    }).catch(() => { if (current) { setLoadError('Resep belum bisa dimuat. Coba lagi.'); setLoading(false); } });
    return () => { current = false; };
  }, [brandId, product.id, reload, onDirtyChange]);

  useEffect(() => {
    if (!dirty && !ingredientForm) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty, ingredientForm]);
  useEffect(() => { onDirtyChange?.(dirty || !!ingredientForm); }, [dirty, ingredientForm, onDirtyChange]);

  function markDirty() { setDirty(true); setSaved(false); setError(''); onDirtyChange?.(true); }
  function lock(value: boolean) { writeLock.current = value; setBusy(value); onBusyChange?.(value); }
  function addIngredient(ingredient: HppIngredient) {
    if (rows.some(row => row.id === ingredient.id)) return;
    setRows(current => [...current, { id: ingredient.id, quantity: '', unit: hppUnits(ingredient.base_unit)[0], optional: false, reviewed: true }]);
    setSelected(''); markDirty();
  }
  function changeRow(index: number, changes: Partial<Row>) {
    setRows(current => current.map((row, i) => i === index ? { ...row, ...changes,
      reviewed: changes.optional === undefined ? true : row.reviewed } : row));
    markDirty();
  }
  function openIngredient(existing?: HppIngredient) {
    setIngredientError('');
    setIngredientForm(existing ? { existing, name: existing.name, price: String(existing.buy_price), quantity: String(existing.buy_qty), unit: existing.base_unit }
      : { name: '', price: '', quantity: '', unit: 'gram' });
  }

  const calculated = rows.map(row => {
    const ingredient = ingredients.find(i => i.id === row.id);
    if (!ingredient) return { row, ingredient, quantity: null, cost: null, requiresReview: false };
    const quantity = row.reviewed ? convertHppQuantity(Number(row.quantity), row.unit, ingredient.base_unit)
      : existingHppQuantity(Number(row.quantity), row.unit, ingredient.base_unit);
    const requiresReview = !row.reviewed && row.unit.trim().toLowerCase() !== ingredient.base_unit.trim().toLowerCase();
    return { row, ingredient, quantity, requiresReview,
      cost: quantity === null ? null : row.optional ? 0 : quantity * Math.max(0, Number(ingredient.cost_per_base_unit)) };
  });
  const complete = calculated.length > 0 && calculated.every(item => item.cost !== null && Number.isFinite(item.cost)) && rows.some(row => !row.optional);
  const total = saved && !dirty && recipe ? Number(recipe.total_cost)
    : complete ? calculated.reduce((sum, item) => sum + item.cost!, 0) : null;

  async function submitIngredient(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ingredientForm || writeLock.current) return;
    const form = ingredientForm;
    const base = form.existing?.base_unit || (form.unit === 'kg' ? 'gram' : form.unit === 'liter' ? 'ml' : form.unit);
    const quantity = convertHppQuantity(Number(form.quantity), form.unit, base);
    if (quantity === null || form.price.trim() === '' || !Number.isFinite(Number(form.price)) || Number(form.price) < 0) {
      setIngredientError('Isi harga beli yang valid dan jumlah pembelian lebih dari nol. Harga Rp0 boleh untuk bahan gratis.'); return;
    }
    if (!form.existing && ingredients.some(i => i.name.trim().toLowerCase() === form.name.trim().toLowerCase())) {
      setIngredientError('Bahan dengan nama ini sudah ada. Pilih dari daftar bahan atau ubah harga belinya.'); return;
    }
    lock(true); setIngredientError('');
    try {
      const result = await saveHppIngredient({ brand_id: brandId, name: form.name, base_unit: base,
        unit_type: base === 'gram' ? 'WEIGHT' : base === 'ml' ? 'VOLUME' : 'COUNT', buy_price: Number(form.price), buy_qty: quantity },
        form.existing ? { id: form.existing.id, row_version: form.existing.row_version } : undefined);
      if (!result.success) { setIngredientError(result.message); return; }
      setIngredients(current => form.existing ? current.map(i => i.id === result.ingredient.id ? result.ingredient : i) : [...current, result.ingredient]);
      if (!form.existing) addIngredient(result.ingredient);
      setIngredientForm(null); setIngredientNotice(`${result.ingredient.name}: harga beli tersimpan. Stok fisik tidak berubah.`);
      setSaved(false);
      refocusAdd.current = true;
    } catch { setIngredientError('Bahan belum tersimpan. Periksa koneksi lalu coba lagi.'); }
    finally { lock(false); }
  }

  async function submitRecipe() {
    if (writeLock.current) return;
    setError('');
    if (!complete) { setError('Isi takaran lebih dari nol untuk setiap bahan, dengan minimal satu bahan utama.'); return; }
    if (calculated.some(item => item.requiresReview)) { setError('Periksa dan konfirmasi satuan resep lama sebelum menyimpan.'); return; }
    if (ingredientForm) { setError('Simpan atau batalkan perubahan harga bahan terlebih dahulu.'); return; }
    lock(true);
    try {
      const result = await saveHppRecipe(product.id, calculated.map(item => ({ ingredient_id: item.row.id,
        quantity: item.quantity!, quantity_unit: item.ingredient!.base_unit, is_optional: item.row.optional, notes: item.row.notes })), recipe?.id, recipe?.notes);
      if (!result.success) { setError(result.message); return; }
      setRecipe(result.recipe);
      setSaved(true); setDirty(false); onDirtyChange?.(false); onSaved?.(result.recipe);
      setRows(recipeRows(result.recipe, ingredients));
      try {
        const refreshed = await loadHppRecipe(brandId, product.id);
        if (!refreshed.success) throw new Error('refresh');
        setIngredients(refreshed.ingredients); setRows(recipeRows(result.recipe, refreshed.ingredients));
      } catch {
        setError('Resep sudah tersimpan, tetapi harga bahan terbaru belum bisa dimuat. Muat ulang halaman untuk memeriksa rinciannya.');
      }
    } catch { setError('Resep belum tersimpan. Periksa koneksi lalu coba lagi.'); }
    finally { lock(false); }
  }

  if (loading) return <p role="status" className="py-8 text-[var(--text-muted)]">Memuat bahan dan resep {product.name}...</p>;
  if (loadError) return <div className="hpp-panel space-y-3"><p role="alert">{loadError}</p><button className="hpp-button" onClick={() => setReload(value => value + 1)}>Coba lagi</button><Link className="hpp-button" href="/login">Login kembali</Link></div>;

  return <div className="hpp-editor grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
    <section className="hpp-panel min-w-0 space-y-5" aria-labelledby="hpp-recipe-heading">
      <div><h2 id="hpp-recipe-heading" className="text-xl font-semibold">Bahan untuk satu porsi</h2>
        <p className="mt-1 text-[var(--text-muted)]">Isi jumlah yang dipakai untuk membuat satu {product.name}. Harga beli diambil dari bahan yang dipilih.</p></div>
      <fieldset disabled={busy} className="space-y-4">
        <div className="space-y-2"><label htmlFor="hpp-add-ingredient" className="font-semibold">Tambahkan bahan ke resep</label>
          <div className="flex flex-wrap gap-2"><select id="hpp-add-ingredient" ref={addSelect} className="hpp-control flex-1 min-w-0" value={selected} onChange={event => setSelected(event.target.value)}>
            <option value="">Pilih bahan yang sudah ada</option>
            {ingredients.filter(i => i.ingredient_type !== 'overhead' && !rows.some(row => row.id === i.id)).map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
          </select><button className="hpp-button" disabled={!selected} onClick={() => { const ingredient = ingredients.find(i => i.id === selected); if (ingredient) addIngredient(ingredient); }}>Tambahkan</button></div>
          <button className="hpp-button hpp-text-button" onClick={() => openIngredient()}>Bahan belum ada? Buat bahan baru</button>
        </div>
        {rows.length === 0 && <p className="border-t border-[var(--border-subtle)] pt-4 text-[var(--text-muted)]">Belum ada bahan di resep ini. Pilih bahan di atas, atau buat bahan baru beserta harga belinya.</p>}
        <div className="divide-y divide-[var(--border-subtle)]">
          {calculated.map(({ row, ingredient, cost, requiresReview }, index) => {
            const id = `hpp-${product.id}-${index}`;
            return <div key={row.id} className="space-y-3 py-4 first:pt-0">
              <div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="font-semibold break-words">{ingredient?.name || 'Bahan tidak tersedia'}</h3>
                {ingredient && <p className="text-sm text-[var(--text-muted)]">Harga beli {hppMoney(Number(ingredient.buy_price))} untuk {hppNumber(ingredient.buy_qty)} {ingredient.base_unit}.</p>}
              </div><button className="hpp-button hpp-text-button shrink-0" aria-label={`Hapus ${ingredient?.name || 'bahan'} dari resep`} onClick={() => { setRows(current => current.filter((_, i) => i !== index)); markDirty(); }}>Hapus</button></div>
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div><label htmlFor={`${id}-qty`} className="mb-1 block text-sm font-semibold">Dipakai untuk satu porsi</label>
                  <div className="flex gap-2"><input id={`${id}-qty`} className="hpp-control min-w-0 w-full" type="number" inputMode="decimal" min="0" step="any" placeholder="Isi takaran" value={row.quantity} aria-describedby={`${id}-cost`} onChange={event => changeRow(index, { quantity: event.target.value })} />
                    <select aria-label={`Satuan takaran ${ingredient?.name || 'bahan'}`} className="hpp-control w-24 shrink-0" value={row.unit} onChange={event => changeRow(index, { unit: event.target.value })}>
                      {[...new Set([row.unit, ...hppUnits(ingredient?.base_unit || row.unit)])].map(unit => <option key={unit} value={unit}>{unit || 'Pilih satuan'}</option>)}
                    </select></div>
                </div>
                <div id={`${id}-cost`} className="sm:text-right sm:self-end"><p className="text-sm text-[var(--text-muted)]">{row.optional ? 'Bahan opsional' : 'Modal bahan per porsi'}</p><p className="font-semibold">{row.optional ? 'Tidak masuk HPP' : cost === null ? 'Isi takaran terlebih dahulu' : hppMoney(cost)}</p></div>
              </div>
              {ingredient && <div className="flex flex-wrap items-center justify-between gap-x-3">
                <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={row.optional} onChange={event => changeRow(index, { optional: event.target.checked })} />Bahan opsional, di luar HPP</label>
                <button className="hpp-button hpp-text-button text-sm" onClick={() => openIngredient(ingredient)}>Ubah harga beli {ingredient.name}</button>
              </div>}
              {ingredient?.needs_review && <p className="text-sm text-[var(--danger)]">Harga bahan ini masih perlu diperiksa. Cocokkan dengan nota melalui Ubah harga beli.</p>}
              {ingredient && Number(ingredient.buy_price) === 0 && <p className="text-sm text-[var(--text-muted)]">Harga beli bahan ini Rp0. Periksa bila bahan ini bukan bahan gratis.</p>}
              {requiresReview && ingredient && <div className="rounded-lg bg-[var(--surface-sunken)] p-3 text-sm space-y-2"><p>Satuan resep lama berbeda dari satuan stok ({ingredient.base_unit}). Periksa takaran agar HPP dan pengurangan stok memakai jumlah yang sama.</p>
                <button className="hpp-button" disabled={convertHppQuantity(Number(row.quantity), row.unit, ingredient.base_unit) === null} onClick={() => changeRow(index, {})}>Konfirmasi takaran {ingredient.name}</button></div>}
              {!ingredient && <p className="text-sm text-[var(--danger)]">Hapus bahan yang sudah tidak tersedia, lalu pilih penggantinya.</p>}
            </div>;
          })}
        </div>
      </fieldset>
      {ingredientNotice && <p role="status" className="text-sm text-[var(--success)]">{ingredientNotice}</p>}
      {ingredientForm && <form onSubmit={submitIngredient} className="border-t border-[var(--border-default)] pt-5 space-y-4" onKeyDown={event => { if (event.key === 'Escape' && !busy) { setIngredientForm(null); addSelect.current?.focus(); } }}>
        <h3 className="text-lg font-semibold">{ingredientForm.existing ? `Harga beli ${ingredientForm.name}` : 'Bahan baru'}</h3>
        <p className="text-sm text-[var(--text-muted)]">{ingredientForm.existing ? 'Harga ini dipakai oleh semua resep yang menggunakan bahan ini.' : 'Bahan tersimpan di Bahan Baku dan bisa dipakai produk lain.'} Isi sesuai pembelian terakhir. Jumlah pembelian di sini tidak menambah stok fisik.</p>
        <fieldset disabled={busy} className="space-y-3">
          {!ingredientForm.existing && <div><label className="mb-1 block font-semibold" htmlFor="hpp-new-name">Nama bahan</label><input autoFocus id="hpp-new-name" required className="hpp-control w-full" value={ingredientForm.name} onChange={event => setIngredientForm({ ...ingredientForm, name: event.target.value })} /></div>}
          <div><label className="mb-1 block font-semibold" htmlFor="hpp-buy-price">Total harga pembelian (Rp)</label><input autoFocus={!!ingredientForm.existing} id="hpp-buy-price" required className="hpp-control w-full" type="number" inputMode="decimal" min="0" step="any" value={ingredientForm.price} onChange={event => setIngredientForm({ ...ingredientForm, price: event.target.value })} /></div>
          <div><label className="mb-1 block font-semibold" htmlFor="hpp-buy-quantity">Jumlah bahan yang dibeli</label><div className="flex gap-2"><input id="hpp-buy-quantity" required className="hpp-control w-full min-w-0" type="number" inputMode="decimal" min="0" step="any" value={ingredientForm.quantity} onChange={event => setIngredientForm({ ...ingredientForm, quantity: event.target.value })} />
            <select aria-label="Satuan pembelian" className="hpp-control w-28" value={ingredientForm.unit} onChange={event => setIngredientForm({ ...ingredientForm, unit: event.target.value })}>
              {(ingredientForm.existing ? hppUnits(ingredientForm.existing.base_unit) : ['gram', 'kg', 'ml', 'liter', 'pcs', 'bungkus']).map(unit => <option key={unit}>{unit}</option>)}
            </select></div><p className="mt-2 text-sm text-[var(--text-muted)]">Contoh: satu kemasan berisi 1 kg. Isi jumlah 1, pilih kg, lalu isi harga satu kemasan.</p></div>
          {ingredientError && <p role="alert" className="text-[var(--danger)]">{ingredientError}</p>}
          <div className="flex flex-wrap gap-2"><button type="submit" className="hpp-button hpp-primary">{busy ? 'Menyimpan bahan...' : ingredientForm.existing ? 'Simpan harga beli' : 'Simpan bahan dan gunakan'}</button><button type="button" className="hpp-button" onClick={() => { setIngredientForm(null); addSelect.current?.focus(); }}>Batal</button></div>
        </fieldset>
      </form>}
    </section>
    <aside className="hpp-panel space-y-5 self-start xl:sticky xl:top-24" aria-labelledby="hpp-total-heading">
      <div><h2 id="hpp-total-heading" className="font-semibold">HPP per porsi</h2><p className="mt-2 text-3xl font-semibold tabular-nums" data-testid="hpp-total">{total === null ? 'Belum dihitung' : hppMoney(total)}</p><p className="mt-2 text-sm text-[var(--text-muted)]">Modal bahan untuk satu {product.name}. Belum termasuk gas, gaji, sewa, dan biaya operasional lain.</p></div>
      <dl className="space-y-3 border-t border-[var(--border-subtle)] pt-4"><div className="flex justify-between gap-3"><dt>Harga jual</dt><dd className="font-semibold">{hppMoney(Number(product.base_price))}</dd></div><div><dt className="text-sm text-[var(--text-muted)]">Selisih sebelum biaya operasional</dt><dd className="mt-1 font-semibold">{total === null ? 'Belum dihitung' : hppMoney(Number(product.base_price) - total)}</dd></div></dl>
      <div className="space-y-3">{error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
        <button className="hpp-button hpp-primary w-full" disabled={busy || !!ingredientForm} onClick={submitRecipe}>{busy ? 'Menyimpan...' : 'Simpan resep dan HPP'}</button>
        {saved && <p role="status" className="text-sm text-[var(--success)]">Resep tersimpan. HPP dari server: {hppMoney(Number(recipe?.total_cost || 0))} per porsi.</p>}
        {saved && onNext && <button className="hpp-button w-full" disabled={busy} onClick={onNext}>Atur produk lain</button>}
        {dirty && <p className="text-sm text-[var(--text-muted)]">Perubahan resep belum disimpan.</p>}
      </div>
      <div className="border-t border-[var(--border-subtle)] pt-4 text-sm space-y-2"><p>Menyimpan resep tidak mengubah mode stok. Siapkan resep produk lain sebelum mengaktifkan Resep &amp; HPP.</p><Link className="hpp-button w-full" href="/dashboard/settings">Buka pengaturan stok</Link><Link className="hpp-button hpp-text-button w-full" href="/dashboard/bahan-baku">Atur stok fisik bahan</Link><Link className="hpp-button hpp-text-button w-full" href="/dashboard/laporan/hpp">Lihat laporan HPP</Link></div>
    </aside>
  </div>;
}
