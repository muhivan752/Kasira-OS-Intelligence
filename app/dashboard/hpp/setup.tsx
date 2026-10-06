'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { loadHppProducts } from '@/app/actions/api';
import { useProGuard } from '@/app/hooks/use-pro-guard';
import { HppRecipeEditor } from '@/components/hpp-recipe-editor';
import { hppMoney, hppNumber, type HppProduct, type HppRecipe } from '@/lib/hpp';

export function HppSetup({ initialProduct }: { initialProduct: string }) {
  const allowed = useProGuard('Atur HPP');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [brandId, setBrandId] = useState('');
  const [canManage, setCanManage] = useState(false), [managed, setManaged] = useState(false), [canChat, setCanChat] = useState(false);
  const [outlets, setOutlets] = useState<{ id: string; name: string }[]>([]), [outletId, setOutletId] = useState('');
  const [products, setProducts] = useState<HppProduct[]>([]);
  const [recipes, setRecipes] = useState<HppRecipe[]>([]);
  const [selected, setSelected] = useState(initialProduct);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const onDirtyChange = useCallback((value: boolean) => setDirty(value), []);
  const onBusyChange = useCallback((value: boolean) => setBusy(value), []);

  useEffect(() => {
    if (!allowed) return;
    let current = true;
    setLoading(true); setError('');
    loadHppProducts(outletId || undefined).then(result => {
      if (!current) return;
      if (!result.success) setError(result.message);
      else { setBrandId(result.brandId); setProducts(result.products); setRecipes(result.recipes);
        setCanManage(result.canManage); setCanChat(result.canChat); setManaged(result.managed); setOutlets(result.outlets); setOutletId(result.outletId); }
      setLoading(false);
    }).catch(() => { if (current) { setError('Produk belum bisa dimuat. Coba lagi.'); setLoading(false); } });
    return () => { current = false; };
  }, [allowed, reload, outletId]);

  function changeProduct(value: string) {
    if (dirty && !window.confirm('Perubahan resep belum disimpan. Buang perubahan dan pilih produk lain?')) return;
    setSelected(value); setDirty(false);
    const url = new URL(window.location.href);
    if (value) url.searchParams.set('product', value); else url.searchParams.delete('product');
    window.history.replaceState(null, '', url);
  }
  const product = products.find(item => item.id === selected);
  const prepared = products.filter(item => recipes.some(recipe => recipe.product_id === item.id));

  return <div className="hpp-workspace space-y-6 max-w-6xl">
    <header className="space-y-2"><h1 className="text-2xl sm:text-3xl font-semibold">{canManage ? 'Atur HPP' : 'HPP produk'}</h1><p className="max-w-2xl text-[var(--text-muted)]">Bahan dan resep dipakai bersama brand. HPP adalah modal bahan per porsi, sebelum biaya operasional.</p>{canChat && !loading && <Link className="hpp-button hpp-primary" href={`/dashboard/hpp/chat?outlet=${outletId}${selected ? `&product=${selected}` : ''}`}>Atur lewat percakapan</Link>}</header>
    {outlets.length > 1 && <label className="block max-w-2xl">Outlet<select className="hpp-control w-full" aria-label="Outlet" value={outletId || outlets[0].id} disabled={busy} onChange={e => { if (dirty && !window.confirm('Buang perubahan resep dan pindah outlet?')) return; setSelected(''); setDirty(false); setOutletId(e.target.value); }}>{outlets.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>}
    {!allowed || loading ? <p role="status">Memuat produk...</p> : error ? <div className="hpp-panel space-y-3"><p role="alert">{error}</p><button className="hpp-button" onClick={() => setReload(value => value + 1)}>Coba lagi</button><Link className="hpp-button" href="/dashboard/settings">Buka pengaturan</Link></div> : products.length === 0 ? <div className="hpp-panel space-y-3"><p>Belum ada produk. Tambahkan produk dan harga jualnya sebelum mengisi resep.</p><Link className="hpp-button hpp-primary" href="/dashboard/menu">Tambah produk di Menu</Link></div> : <>
      <div className="max-w-2xl space-y-2"><label htmlFor="hpp-product" className="block font-semibold">Produk yang ingin dihitung</label><select id="hpp-product" className="hpp-control w-full" disabled={busy} value={product ? selected : ''} onChange={event => changeProduct(event.target.value)}>
        <option value="">Pilih produk</option>{products.map(item => <option key={item.id} value={item.id}>{item.name}{!item.is_active ? ' (nonaktif)' : ''} · {recipes.some(recipe => recipe.product_id === item.id) ? 'Ada resep' : 'Belum ada resep'}</option>)}
      </select><p className="text-sm text-[var(--text-muted)]">{prepared.length} dari {products.length} produk memiliki resep. Kelengkapan resep diperiksa saat beralih mode stok.</p>
        {initialProduct && !product && !selected && <p className="text-sm">Pilih produk dari daftar untuk melanjutkan.</p>}
        {selected && !product && <p role="alert" className="text-sm text-[var(--danger)]">Produk pada tautan ini tidak tersedia. Pilih produk lain.</p>}
      </div>
      {product ? canManage ? <HppRecipeEditor key={product.id} brandId={brandId} product={product} onDirtyChange={onDirtyChange} onBusyChange={onBusyChange} onNext={() => { changeProduct(''); document.getElementById('hpp-product')?.focus(); }} onSaved={recipe => setRecipes(current => [...current.filter(item => item.product_id !== recipe.product_id), recipe])} />
        : <section className="hpp-panel space-y-3"><h2 className="font-semibold">{product.name}</h2><p>Akses baca. Penyimpanan langsung memerlukan hak kelola, persetujuan dan lihat harga pembelian.</p>{recipes.find(r => r.product_id === product.id) ? recipes.filter(r => r.product_id === product.id).map(r => <div key={r.id}><p>Modal bahan per porsi: <strong>{hppMoney(Number(r.total_cost))}</strong>{r.is_estimated ? ' · Estimasi' : ''}</p><ul>{r.ingredients.map((i, n) => <li key={`${i.ingredient_id}:${n}`}>{i.ingredient_name} · {hppNumber(i.quantity)} {i.quantity_unit}{i.is_optional ? ' (opsional)' : ''}</li>)}</ul>{r.notes && <p>{r.notes}</p>}</div>) : <p>Belum ada resep untuk produk ini.</p>}</section>
        : <div className="border-t border-[var(--border-default)] pt-6 max-w-2xl text-[var(--text-muted)]">Mulai dari satu produk. Bahan yang belum tersedia bisa ditambahkan langsung di sini, tanpa berpindah halaman.</div>}
    </>}
  </div>;
}
