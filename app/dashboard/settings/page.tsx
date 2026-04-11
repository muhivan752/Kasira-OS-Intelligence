'use client';

import { useState, useEffect, useRef } from 'react';
import { getOutlets, updateOutlet, updateStockMode, getCurrentUser } from '@/app/actions/api';
import { Loader2, Store, Clock, Link as LinkIcon, CreditCard, Upload, ImageOff, Image, Package } from 'lucide-react';
import Link from 'next/link';

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [outlet, setOutlet] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [uploadingCover, setUploadingCover] = useState(false);
  const [stockMode, setStockMode] = useState('simple');
  const [savingStockMode, setSavingStockMode] = useState(false);
  const [stockModeError, setStockModeError] = useState('');
  const [isPro, setIsPro] = useState(false);
  const coverInputRef = useRef<HTMLInputElement>(null);

  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    address: '',
    opening_hours: '',
    is_open: true,
    cover_image_url: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const data = outlets[0];
        setOutlet(data);
        setFormData({
          name: data.name || '',
          phone: data.phone || '',
          address: data.address || '',
          opening_hours: typeof data.opening_hours === 'string' ? data.opening_hours : '',
          is_open: data.is_open !== false,
          cover_image_url: data.cover_image_url || '',
        });
        setStockMode(data.stock_mode || 'simple');
      }
      const user = await getCurrentUser();
      if (user) {
        const tier = user.subscription_tier || 'starter';
        setIsPro(['pro', 'business', 'enterprise'].includes(tier));
      }
    } catch (error) {
      console.error('Failed to load outlet data', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleStockModeChange(mode: string) {
    if (!outlet || mode === stockMode) return;
    setSavingStockMode(true);
    setStockModeError('');
    try {
      await updateStockMode(outlet.id, mode);
      setStockMode(mode);
    } catch (e: any) {
      setStockModeError(e.message);
    }
    setSavingStockMode(false);
  }

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingCover(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (res.ok && data.url) {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || '';
        setFormData(f => ({ ...f, cover_image_url: `${baseUrl}${data.url}` }));
      } else {
        alert(data.detail || 'Gagal upload gambar');
      }
    } catch {
      alert('Gagal upload gambar');
    } finally {
      setUploadingCover(false);
      if (coverInputRef.current) coverInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const res = await updateOutlet(outlet.id, formData);
    if (res.success) {
      alert('Pengaturan berhasil disimpan');
      loadData();
    } else {
      alert(res.message || 'Gagal menyimpan pengaturan');
    }
    setSaving(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }

  const storefrontUrl = outlet?.slug
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/${outlet.slug}`
    : '';

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pengaturan Outlet</h1>
        <p className="text-gray-500">Kelola informasi dasar dan tampilan storefront Anda.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Settings Form */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <Store className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Informasi Dasar</h2>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {/* Cover Image */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                  <Image className="w-4 h-4 text-gray-500" />
                  Foto Cover Storefront
                </label>
                <input ref={coverInputRef} type="file" accept="image/*" className="hidden"
                  onChange={handleCoverUpload} />
                {formData.cover_image_url ? (
                  <div className="space-y-2">
                    <div className="relative w-full h-36 rounded-xl overflow-hidden border border-gray-200 bg-gray-100">
                      <img
                        src={formData.cover_image_url}
                        alt="Cover"
                        className="w-full h-full object-cover"
                        onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                    </div>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => coverInputRef.current?.click()}
                        disabled={uploadingCover}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 disabled:opacity-50">
                        {uploadingCover ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                        Ganti foto
                      </button>
                      <button type="button" onClick={() => setFormData(f => ({ ...f, cover_image_url: '' }))}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50">
                        <ImageOff className="w-3.5 h-3.5" /> Hapus foto
                      </button>
                    </div>
                  </div>
                ) : (
                  <button type="button" onClick={() => coverInputRef.current?.click()}
                    disabled={uploadingCover}
                    className="w-full flex flex-col items-center justify-center gap-2 h-28 border-2 border-dashed border-gray-300 rounded-xl hover:border-blue-400 hover:bg-blue-50 transition-colors disabled:opacity-50">
                    {uploadingCover
                      ? <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                      : <Upload className="w-6 h-6 text-gray-400" />}
                    <span className="text-xs text-gray-500">
                      {uploadingCover ? 'Mengupload...' : 'Klik untuk pilih foto cover storefront'}
                    </span>
                  </button>
                )}
                <p className="text-xs text-gray-400 mt-1">Tampil sebagai banner di bagian atas storefront. Ukuran ideal: 800×300px</p>
              </div>

              <div className="border-t border-gray-100 pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama Outlet</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nomor Telepon / WhatsApp</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={e => setFormData({ ...formData, phone: e.target.value.replace(/\D/g, '') })}
                  placeholder="628123456789"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alamat Lengkap</label>
                <textarea
                  rows={3}
                  value={formData.address}
                  onChange={e => setFormData({ ...formData, address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                />
              </div>

              <div className="pt-2 border-t border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900">Status Operasional</h3>
                    <p className="text-xs text-gray-500">Buka atau tutup toko untuk pesanan online.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, is_open: !formData.is_open })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                      formData.is_open ? 'bg-blue-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      formData.is_open ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    Jam Operasional
                  </label>
                  <input
                    type="text"
                    placeholder="Contoh: 08:00 - 22:00"
                    value={formData.opening_hours}
                    onChange={e => setFormData({ ...formData, opening_hours: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center justify-center px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Simpan Perubahan
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Storefront Link */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Link Storefront</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                Bagikan link ini ke pelanggan untuk menerima pesanan online.
              </p>
              {storefrontUrl ? (
                <>
                  <div>
                    <input
                      type="text"
                      readOnly
                      value={storefrontUrl}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-sm text-gray-600 outline-none"
                    />
                  </div>
                  <a
                    href={storefrontUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full text-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    Buka Storefront
                  </a>
                </>
              ) : (
                <p className="text-sm text-gray-400 italic">Slug outlet belum tersedia</p>
              )}
            </div>
          </div>

          {/* Stock Mode (Pro only) */}
          {isPro && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <Package className="w-5 h-5 text-gray-500" />
                <h2 className="text-lg font-bold text-gray-900">Mode Stok</h2>
              </div>
              <div className="p-6 space-y-4">
                <p className="text-sm text-gray-600">
                  Pilih cara mengelola stok produk Anda.
                </p>
                {stockModeError && <p className="text-sm text-red-600">{stockModeError}</p>}
                <div className="space-y-3">
                  <label className={`flex items-start gap-3 p-4 border rounded-xl cursor-pointer transition ${stockMode === 'simple' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <input type="radio" name="stock_mode" value="simple" checked={stockMode === 'simple'}
                      onChange={() => handleStockModeChange('simple')} className="mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">Sederhana</p>
                      <p className="text-sm text-gray-500">Stok per produk, deduct langsung dari transaksi. Cocok untuk awal.</p>
                    </div>
                  </label>
                  <label className={`flex items-start gap-3 p-4 border rounded-xl cursor-pointer transition ${stockMode === 'recipe' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <input type="radio" name="stock_mode" value="recipe" checked={stockMode === 'recipe'}
                      onChange={() => handleStockModeChange('recipe')} className="mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">Resep & HPP</p>
                      <p className="text-sm text-gray-500">Stok per bahan baku, deduct otomatis berdasarkan resep. Hitung HPP otomatis.</p>
                    </div>
                  </label>
                </div>
                {savingStockMode && <p className="text-sm text-blue-600">Menyimpan...</p>}
              </div>
            </div>
          )}

          {/* Payment Settings */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Pembayaran</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                Atur metode pembayaran QRIS via Xendit untuk menerima pembayaran non-tunai.
              </p>
              <Link
                href="/dashboard/settings/payment"
                className="block w-full text-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Setup QRIS Xendit
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
