'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createProduct, getCategories, getOutlets, getProducts } from '@/app/actions/api';
import { AuthShell } from '@/components/auth/auth-shell';

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [outlet, setOutlet] = useState<any>(null);
  const [categories, setCategories] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [category, setCategory] = useState('');

  async function load() {
    setLoading(true); setError('');
    try {
      const outlets = await getOutlets();
      if (!outlets?.length) { router.replace('/login'); return; }
      const current = outlets[0];
      setOutlet(current);
      const [cats, products] = await Promise.all([getCategories(current.brand_id), getProducts(current.brand_id)]);
      setCategories(cats || []); setCategory(cats?.[0]?.id || '');
      if (products?.length) setStep(1);
    } catch { setError('Usaha belum dapat dimuat. Periksa koneksi lalu coba lagi.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function save(event: React.FormEvent) {
    event.preventDefault(); setError(''); setSaving(true);
    const result = await createProduct({ brand_id: outlet.brand_id, name: name.trim(), base_price: Number(price), stock_enabled: false, stock_qty: 0, is_active: true, ...(category ? { category_id: category } : {}) });
    if (result.success) setStep(1); else setError(result.message || 'Produk belum tersimpan. Coba lagi.');
    setSaving(false);
  }
  return <AuthShell>
    {loading ? <p role="status">Menyiapkan usaha Anda…</p> : <>
      <p className="auth-kicker">{outlet?.name || 'Usaha Anda'} / {step + 1} dari 2</p>
      <div className="auth-progress" aria-label={`Langkah ${step + 1} dari 2`}><span /><span className={step === 1 ? 'complete' : ''} /></div>
      <div className="auth-heading"><h1>{step === 0 ? 'Mulai dari produk pertama.' : 'Usaha Anda siap dipakai.'}</h1><p>{step === 0 ? 'Cukup nama dan harga. Stok serta resep bisa diatur saat Anda membutuhkannya.' : 'Lanjutkan dari dashboard atau gunakan aplikasi kasir di perangkat Anda.'}</p></div>
      {error && <div className="auth-error" role="alert">{error}</div>}
      {!outlet ? <button className="ks-btn" onClick={load}>Coba lagi</button> : step === 0 ? <form className="auth-form" onSubmit={save}>
        <label htmlFor="product-name">Nama produk<input id="product-name" autoFocus value={name} onChange={event => setName(event.target.value)} placeholder="Contoh: Kopi susu" minLength={2} required /></label>
        <label htmlFor="product-price">Harga jual (Rp)<input id="product-price" inputMode="numeric" type="number" min="1" step="1" value={price} onChange={event => setPrice(event.target.value)} placeholder="18000" required /></label>
        {categories.length > 0 && <label htmlFor="product-category">Kategori<select id="product-category" value={category} onChange={event => setCategory(event.target.value)}>{categories.map(cat => <option key={cat.id} value={cat.id}>{cat.name}</option>)}</select></label>}
        <button className="ks-btn" disabled={saving}>{saving ? 'Menyimpan produk…' : 'Simpan dan lanjut'}</button>
        <button className="auth-text-button" type="button" disabled={saving} onClick={() => { setError(''); setStep(1); }}>Tambahkan produk nanti</button>
      </form> : <div className="auth-actions">
        <div className="auth-setup-list"><p><strong>Menu dan harga</strong><span>Tambah produk berikutnya dari dashboard.</span></p><p><strong>Pembayaran</strong><span>Tunai bisa langsung dipakai. Atur QRIS atau rekening saat diperlukan.</span></p><p><strong>Printer</strong><span>Hubungkan dari pengaturan aplikasi kasir.</span></p></div>
        <Link className="ks-btn" href="/dashboard">Buka dashboard usaha</Link>
        <a className="ks-btn ks-btn-outline" href="/api/download/pos">Unduh aplikasi kasir Android</a>
        <Link className="auth-text-button" href="/dashboard/settings/payment">Atur metode pembayaran</Link>
        <button className="auth-text-button" type="button" onClick={() => setStep(0)}>Kembali ke produk pertama</button>
      </div>}
    </>}
  </AuthShell>;
}
