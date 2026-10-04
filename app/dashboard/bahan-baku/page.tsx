'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { loadIngredientInventory, saveInventoryIngredient, addInventoryStock, removeInventoryIngredient } from '@/app/actions/api';
import { useProGuard } from '@/app/hooks/use-pro-guard';
import { InventoryDialog } from '@/components/inventory-dialog';
import { InventoryIngredientForm, InventoryStockForm } from '@/components/inventory-forms';
import { hasLowStock, hasRecordedStock, type InventoryIngredient } from '@/lib/ingredient-inventory';
import { hppMoney, hppNumber } from '@/lib/hpp';

type Modal = { kind: 'ingredient' | 'stock' | 'usage' | 'delete'; item?: InventoryIngredient; overhead?: boolean };
type Filter = 'all' | 'low' | 'unknown' | 'review' | 'unused';
const filters: { value: Filter; label: string }[] = [
  { value: 'all', label: 'Semua bahan' }, { value: 'low', label: 'Stok menipis atau habis' },
  { value: 'unknown', label: 'Stok belum dicatat' }, { value: 'review', label: 'Harga perlu diperiksa' },
  { value: 'unused', label: 'Belum dipakai di resep' },
];
type WriteResult = Awaited<ReturnType<typeof addInventoryStock>>;

export default function IngredientsPage() {
  const allowed = useProGuard('Bahan Baku');
  const [inventory, setInventory] = useState<{ ingredients: InventoryIngredient[]; outletId: string; brandId: string; stockMode: string }>();
  const [loading, setLoading] = useState(true), [loadError, setLoadError] = useState('');
  const [view, setView] = useState<'recipe' | 'overhead'>('recipe');
  const [filter, setFilter] = useState<Filter>('all'), [query, setQuery] = useState('');
  const [modal, setModal] = useState<Modal>(), [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [uncertain, setUncertain] = useState(false);
  const [notice, setNotice] = useState(''), [created, setCreated] = useState<InventoryIngredient>();
  const lock = useRef(false), mounted = useRef(true), loadSequence = useRef(0);

  async function load() {
    const sequence = ++loadSequence.current;
    setLoading(true); setLoadError('');
    try {
      const result = await loadIngredientInventory();
      if (!mounted.current || sequence !== loadSequence.current) return;
      if (result.success) setInventory(result);
      else setLoadError(result.message);
    } catch {
      if (mounted.current && sequence === loadSequence.current) setLoadError('Daftar bahan belum bisa dimuat. Coba lagi.');
    } finally {
      if (mounted.current && sequence === loadSequence.current) setLoading(false);
    }
  }
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { if (allowed) void load(); }, [allowed]);
  useEffect(() => {
    if (!dirty) return;
    const prevent = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', prevent);
    return () => window.removeEventListener('beforeunload', prevent);
  }, [dirty]);

  function open(next: Modal) { setError(''); setUncertain(false); setDirty(false); setModal(next); }
  function close() {
    if (lock.current || (dirty && !window.confirm('Tutup form dan buang perubahan yang belum disimpan?'))) return;
    if (uncertain) { void reconcile(); return; }
    setModal(undefined); setDirty(false); setError('');
  }
  async function write(action: () => Promise<WriteResult>, success: (data: InventoryIngredient) => void) {
    if (lock.current || uncertain) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const result = await action();
      if (!mounted.current) return;
      if (!result.success) { setError(result.message); setUncertain(result.uncertain); return; }
      success(result.data); setModal(undefined); setDirty(false);
    } catch {
      setError('Hasil penyimpanan belum dapat dipastikan. Muat ulang data sebelum mencoba lagi.'); setUncertain(true);
    } finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  function merge(data: InventoryIngredient, old?: InventoryIngredient) {
    // Price responses omit outlet stock and recipe usage. Preserve the loaded values.
    const updated = { ...old, ...data, current_stock: data.current_stock ?? old?.current_stock,
      min_stock: data.min_stock ?? old?.min_stock, used_in: data.used_in ?? old?.used_in };
    setInventory(current => current && ({ ...current, ingredients: old
      ? current.ingredients.map(item => item.id === old.id ? updated : item)
      : [...current.ingredients, updated].sort((a, b) => a.name.localeCompare(b.name, 'id')) }));
    return updated;
  }
  async function reconcile() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setCreated(undefined);
    setNotice('Periksa data terbaru sebelum mengulang perubahan.');
    await load();
    lock.current = false;
    if (mounted.current) { setModal(undefined); setDirty(false); setError(''); setUncertain(false); setBusy(false); }
  }

  const ingredients = inventory?.ingredients ?? [];
  const recipe = ingredients.filter(item => item.ingredient_type !== 'overhead');
  const overhead = ingredients.filter(item => item.ingredient_type === 'overhead');
  const matches = (item: InventoryIngredient) => filter === 'all' || filter === 'low' && hasLowStock(item)
    || filter === 'unknown' && !hasRecordedStock(item) || filter === 'review' && item.needs_review
    || filter === 'unused' && !item.used_in?.length;
  const visible = (view === 'recipe' ? recipe.filter(matches) : overhead)
    .filter(item => item.name.toLocaleLowerCase('id').includes(query.trim().toLocaleLowerCase('id')));
  const heading = modal?.kind === 'stock' ? 'Tambah stok' : modal?.kind === 'usage' ? 'Pemakaian bahan'
    : modal?.kind === 'delete' ? 'Hapus bahan' : modal?.overhead ? modal.item ? 'Ubah biaya operasional' : 'Tambah biaya operasional'
      : modal?.item ? 'Ubah harga bahan' : 'Tambah bahan';

  return <div className="hpp-workspace inventory-workspace mx-auto max-w-6xl space-y-6 pb-12">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="max-w-xl"><h1 className="text-3xl font-semibold tracking-tight">Bahan Baku</h1>
        <p className="mt-2 text-muted">Kelola stok dan harga bahan di sini. Susun takaran per produk melalui Atur HPP.</p></div>
      <div className="flex flex-wrap gap-2"><Link href="/dashboard/hpp" className="hpp-button">Atur HPP</Link>
        <button data-inventory-add className="hpp-button hpp-primary" disabled={!inventory || loading || !!loadError}
          onClick={() => open({ kind: 'ingredient', overhead: view === 'overhead' })}>{view === 'recipe' ? 'Tambah bahan' : 'Tambah biaya'}</button></div>
    </header>

    <nav aria-label="Jenis bahan" className="inventory-tabs flex flex-wrap gap-x-6">
      <button className="hpp-button" aria-pressed={view === 'recipe'} onClick={() => { setView('recipe'); setQuery(''); }}>
        Bahan resep{inventory ? ` (${recipe.length})` : ''}</button>
      <button className="hpp-button" aria-pressed={view === 'overhead'} onClick={() => { setView('overhead'); setQuery(''); }}>
        Biaya operasional{inventory ? ` (${overhead.length})` : ''}</button>
    </nav>
    {notice && <div className="hpp-panel space-y-3" role="status"><p>{notice}</p>
      {created && <button className="hpp-button" onClick={() => open({ kind: 'stock', item: created })}>Catat stok {created.name}</button>}</div>}
    {!allowed || loading ? <p role="status" className="py-8 text-muted">Memuat daftar bahan…</p>
      : loadError ? <div className="hpp-panel space-y-3" role="alert"><p>{loadError}</p>
        <button data-inventory-retry className="hpp-button" onClick={() => void load()}>Muat ulang</button>
        {loadError.includes('Sesi') && <Link href="/login" className="hpp-button ml-2">Masuk kembali</Link>}</div>
        : <>
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex min-w-0 flex-1 flex-col gap-2"><span className="font-semibold">Cari {view === 'recipe' ? 'bahan' : 'biaya'}</span>
              <input className="hpp-control w-full" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={view === 'recipe' ? 'Nama bahan' : 'Nama biaya'} /></label>
            {view === 'recipe' && <label className="flex w-full flex-col gap-2 sm:w-auto"><span id="inventory-filter-label" className="font-semibold">Tampilkan</span>
              <select aria-labelledby="inventory-filter-label" className="hpp-control" value={filter} onChange={event => setFilter(event.target.value as Filter)}>
                {filters.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>}
          </div>
          {view === 'overhead' && <p className="text-muted">Catat estimasi pengeluaran harian seperti gas atau sewa. Biaya ini belum termasuk dalam HPP bahan per porsi.</p>}
          {view === 'recipe' && inventory?.stockMode !== 'hpp' && recipe.length > 0 && <p className="text-muted">Stok bahan baru berkurang mengikuti resep saat mode HPP aktif di Pengaturan.</p>}
          {visible.length === 0 ? <div className="hpp-panel space-y-3">
            <h2 className="text-lg font-semibold">{query || view === 'recipe' && filter !== 'all' ? 'Tidak ada hasil yang sesuai' : view === 'recipe' ? 'Belum ada bahan' : 'Belum ada biaya operasional'}</h2>
            <p className="text-muted">{query || view === 'recipe' && filter !== 'all' ? 'Coba nama lain atau tampilkan semua bahan.'
              : view === 'recipe' ? 'Tambahkan bahan dan harga pembeliannya. Setelah itu, catat stok yang tersedia.' : 'Tambahkan pengeluaran yang ingin dicatat sebagai estimasi harian.'}</p>
            {query || view === 'recipe' && filter !== 'all' ? <button className="hpp-button" onClick={() => { setQuery(''); setFilter('all'); }}>Reset pencarian</button>
              : <button className="hpp-button" onClick={() => open({ kind: 'ingredient', overhead: view === 'overhead' })}>{view === 'recipe' ? 'Tambah bahan pertama' : 'Tambah biaya pertama'}</button>}
          </div> : <div className="inventory-list">{visible.map(item => <article key={item.id} data-ingredient={item.id} className="inventory-row">
            <div className="min-w-0"><h2 className="text-lg font-semibold break-words">{item.name}</h2>
              {view === 'recipe' && <p className="mt-1 text-muted">{item.used_in?.length ? `Dipakai di ${item.used_in.length} resep` : 'Belum dipakai di resep'}</p>}
              {item.needs_review && <p className="mt-1 font-semibold">Harga perlu diperiksa</p>}</div>
            {view === 'recipe' ? <>
              <div><p className="text-sm text-muted">Stok tersedia</p><p className="mt-1 text-xl font-semibold tabular-nums">
                {hasRecordedStock(item) ? `${hppNumber(Number(item.current_stock))} ${item.base_unit}` : 'Belum dicatat'}</p>
                {hasLowStock(item) && <p className="mt-1 font-semibold">{Number(item.current_stock) <= 0 ? 'Stok habis' : 'Stok menipis'}</p>}
                {item.min_stock != null && <p className="mt-1 text-sm text-muted">Batas minimum {hppNumber(Number(item.min_stock))} {item.base_unit}</p>}</div>
              <div><p className="text-sm text-muted">Biaya HPP per {item.base_unit}</p><p className="mt-1 text-lg font-semibold tabular-nums">{hppMoney(Number(item.cost_per_base_unit))}</p>
                <p className="mt-1 text-sm text-muted">Pembelian terakhir {hppMoney(Number(item.buy_price))} untuk {hppNumber(Number(item.buy_qty))} {item.base_unit}</p></div>
            </> : <div><p className="text-sm text-muted">Estimasi per hari</p><p className="mt-1 text-xl font-semibold tabular-nums">{hppMoney(Number(item.overhead_cost_per_day ?? 0))}</p></div>}
            <div className="inventory-actions flex flex-wrap gap-2">
              {view === 'recipe' && <button className="hpp-button" onClick={() => open({ kind: 'stock', item })}>Tambah stok</button>}
              <button className="hpp-button" onClick={() => open({ kind: 'ingredient', item, overhead: view === 'overhead' })}>{view === 'recipe' ? 'Ubah harga' : 'Ubah biaya'}</button>
              {view === 'recipe' && <button className="hpp-button hpp-text-button" onClick={() => open({ kind: 'usage', item })}>Lihat pemakaian</button>}
              <button className="hpp-button hpp-text-button" aria-label={`Hapus ${item.name}`} onClick={() => open({ kind: 'delete', item })}>Hapus</button>
            </div>
          </article>)}</div>}
        </>}

    {modal && inventory && <InventoryDialog title={heading} busy={busy} onClose={close}>
      {busy && <p role="status" className="mb-4 text-muted">Menyimpan perubahan…</p>}
      {error && <div role="alert" className="inventory-message mb-4 space-y-3"><p>{error}</p>
        {uncertain && <button className="hpp-button" disabled={busy} onClick={() => void reconcile()}>Periksa data terbaru</button>}
        {error.includes('Sesi') && <Link href="/login" className="hpp-button">Masuk kembali</Link>}
        {!uncertain && error.includes('refresh') && <button className="hpp-button" disabled={busy} onClick={() => void reconcile()}>Muat ulang data</button>}</div>}
      {modal.kind === 'ingredient' && <InventoryIngredientForm item={modal.item} overhead={!!modal.overhead} brandId={inventory.brandId}
        names={ingredients.filter(item => item.id !== modal.item?.id).map(item => item.name)} disabled={busy || uncertain} onDirty={() => setDirty(true)}
        onSave={payload => write(() => saveInventoryIngredient(payload, modal.item), data => {
          const saved = merge(data, modal.item); setCreated(!modal.item && !modal.overhead ? saved : undefined);
          setNotice(modal.item ? `${saved.name} diperbarui. ${modal.overhead ? 'Estimasi biaya tersimpan.' : 'Harga ini berlaku pada semua resep yang memakai bahan tersebut. Stok tetap sama.'}`
            : modal.overhead ? `${saved.name} ditambahkan.` : `${saved.name} ditambahkan. Stok belum dicatat.`);
        })} />}
      {modal.kind === 'stock' && modal.item && <InventoryStockForm item={modal.item} disabled={busy || uncertain} onDirty={() => setDirty(true)}
        onSave={(quantity, notes) => write(() => addInventoryStock(modal.item!.id, inventory.outletId, quantity, notes), data => {
          const saved = merge(data, modal.item); setCreated(undefined); setNotice(`Stok ${saved.name} berhasil ditambahkan.`);
        })} />}
      {modal.kind === 'usage' && modal.item && <div className="space-y-4"><p className="font-semibold">{modal.item.name}</p>
        {modal.item.used_in?.length ? <ul className="space-y-3">{modal.item.used_in.map((usage, index) => <li key={index} className="inventory-message">
          <p className="font-semibold">{usage.product_name}</p><p className="text-muted">{hppNumber(usage.qty_per_serving)} {usage.unit} per porsi</p></li>)}</ul>
          : <p className="text-muted">Bahan ini belum dipakai di resep. Pilih produknya di Atur HPP untuk menambahkan takaran.</p>}
        <Link href="/dashboard/hpp" className="hpp-button hpp-primary">Buka Atur HPP</Link></div>}
      {modal.kind === 'delete' && modal.item && <div className="space-y-4"><p className="font-semibold">{modal.item.name}</p>
        {modal.item.used_in?.length ? <><p>Bahan masih dipakai di resep. Lepaskan bahan dari resep tersebut sebelum menghapusnya.</p>
          <Link href="/dashboard/hpp" className="hpp-button">Buka Atur HPP</Link></>
          : <><p>Hapus bahan ini dari daftar? Bahan tidak akan tersedia untuk resep atau penambahan stok berikutnya.</p>
            <button className="hpp-button" disabled={busy || uncertain} onClick={() => void write(() => removeInventoryIngredient(modal.item!.id), () => {
              setInventory(current => current && ({ ...current, ingredients: current.ingredients.filter(item => item.id !== modal.item!.id) }));
              setCreated(undefined); setNotice(`${modal.item!.name} dihapus dari daftar.`);
            })}>{busy ? 'Menghapus…' : 'Hapus bahan'}</button></>}
      </div>}
    </InventoryDialog>}
  </div>;
}
