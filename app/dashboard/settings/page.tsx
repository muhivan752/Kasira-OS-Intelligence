'use client';

import { useState, useEffect, useRef } from 'react';
import { getOutlets, updateOutlet, updateStockMode, getCurrentUser, getTaxConfig, updateTaxConfig, getReferralCode, getReferralStats } from '@/app/actions/api';
import { Loader2, Store, Clock, Link as LinkIcon, CreditCard, Upload, ImageOff, Image, Package, Receipt, Gift, Copy, Share2, Check } from 'lucide-react';
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

  // Tax config state
  const [taxConfig, setTaxConfig] = useState({
    pb1_enabled: false,
    tax_pct: 10,
    service_charge_enabled: false,
    service_charge_pct: 5,
    tax_inclusive: false,
  });
  const [savingTax, setSavingTax] = useState(false);
  const [taxSaved, setTaxSaved] = useState(false);

  // Referral
  const [referralCode, setReferralCode] = useState('');
  const [referralShareUrl, setReferralShareUrl] = useState('');
  const [referralShareText, setReferralShareText] = useState('');
  const [referralStats, setReferralStats] = useState<any>(null);
  const [copied, setCopied] = useState(false);

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

        // Load tax config
        try {
          const tc = await getTaxConfig(data.id);
          if (tc) setTaxConfig(tc);
        } catch {}
      }
      const user = await getCurrentUser();
      if (user) {
        const tier = user.subscription_tier || 'starter';
        setIsPro(['pro', 'business', 'enterprise'].includes(tier));
      }

      // Load referral
      try {
        const refData = await getReferralCode();
        if (refData) {
          setReferralCode(refData.referral_code);
          setReferralShareUrl(refData.share_url);
          setReferralShareText(refData.share_text);
        }
        const stats = await getReferralStats();
        if (stats) setReferralStats(stats);
      } catch {}
    } catch (error) {
      console.error('Failed to load outlet data', error);
    } finally {
      setLoading(false);
    }
  }

  const [showStockModeConfirm, setShowStockModeConfirm] = useState<string | null>(null);
  const [stockModeSuccess, setStockModeSuccess] = useState('');

  function handleStockModeClick(mode: string) {
    if (!outlet || mode === stockMode) return;
    if (mode === 'recipe') {
      setShowStockModeConfirm(mode);
    } else {
      setShowStockModeConfirm(mode);
    }
  }

  async function confirmStockModeChange() {
    const mode = showStockModeConfirm;
    if (!mode || !outlet) return;
    setShowStockModeConfirm(null);
    setSavingStockMode(true);
    setStockModeError('');
    setStockModeSuccess('');
    try {
      await updateStockMode(outlet.id, mode);
      setStockMode(mode);
      if (mode === 'recipe') {
        setStockModeSuccess('Mode Resep & HPP aktif! Langkah selanjutnya: buka menu Bahan Baku untuk menambahkan bahan, lalu hubungkan resep di setiap produk.');
      } else {
        setStockModeSuccess('Mode Stok Sederhana aktif. Stok kembali dihitung per produk.');
      }
      setTimeout(() => setStockModeSuccess(''), 8000);
    } catch (e: any) {
      setStockModeError(e.message);
    }
    setSavingStockMode(false);
  }

  async function handleTaxSave() {
    if (!outlet) return;
    setSavingTax(true);
    try {
      await updateTaxConfig(outlet.id, taxConfig);
      setTaxSaved(true);
      setTimeout(() => setTaxSaved(false), 2000);
    } catch (e: any) {
      alert(e.message || 'Gagal menyimpan');
    }
    setSavingTax(false);
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
                {stockModeSuccess && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <p className="text-sm text-green-800 font-medium">{stockModeSuccess}</p>
                  </div>
                )}
                <div className="space-y-3">
                  <label className={`flex items-start gap-3 p-4 border rounded-xl cursor-pointer transition ${stockMode === 'simple' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <input type="radio" name="stock_mode" value="simple" checked={stockMode === 'simple'}
                      onChange={() => handleStockModeClick('simple')} className="mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">Stok Sederhana</p>
                      <p className="text-sm text-gray-500">Stok per produk, berkurang otomatis setiap transaksi. Menu Bahan Baku & HPP tidak aktif.</p>
                    </div>
                  </label>
                  <label className={`flex items-start gap-3 p-4 border rounded-xl cursor-pointer transition ${stockMode === 'recipe' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <input type="radio" name="stock_mode" value="recipe" checked={stockMode === 'recipe'}
                      onChange={() => handleStockModeClick('recipe')} className="mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">Resep & HPP</p>
                      <p className="text-sm text-gray-500">Stok per bahan baku, berkurang otomatis berdasarkan resep. HPP dihitung otomatis. Stok produk tidak ditampilkan.</p>
                    </div>
                  </label>
                </div>
                {savingStockMode && <p className="text-sm text-blue-600">Menyimpan...</p>}

                {/* Confirmation Dialog */}
                {showStockModeConfirm && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
                      <h3 className="text-lg font-bold text-gray-900 mb-2">
                        {showStockModeConfirm === 'recipe' ? 'Beralih ke Mode Resep & HPP?' : 'Kembali ke Stok Sederhana?'}
                      </h3>
                      {showStockModeConfirm === 'recipe' ? (
                        <div className="text-sm text-gray-600 space-y-2 mb-5">
                          <p>Dengan mode Resep & HPP:</p>
                          <ul className="list-disc ml-5 space-y-1">
                            <li>Stok dihitung dari <strong>bahan baku</strong>, bukan per produk</li>
                            <li>Setiap produk perlu <strong>resep</strong> yang terhubung ke bahan</li>
                            <li>HPP otomatis dihitung dari harga bahan</li>
                            <li>Stok sederhana (per produk) <strong>tidak akan ditampilkan</strong></li>
                          </ul>
                          <p className="mt-3 text-amber-700 bg-amber-50 rounded-lg p-3">
                            Setelah beralih, buka <strong>Bahan Baku</strong> untuk menambahkan bahan, lalu hubungkan resep di menu produk.
                          </p>
                        </div>
                      ) : (
                        <div className="text-sm text-gray-600 space-y-2 mb-5">
                          <p>Kembali ke stok sederhana:</p>
                          <ul className="list-disc ml-5 space-y-1">
                            <li>Stok kembali dihitung <strong>per produk</strong></li>
                            <li>Menu Bahan Baku & HPP <strong>tidak aktif</strong></li>
                            <li>Data resep & bahan baku tetap tersimpan</li>
                          </ul>
                        </div>
                      )}
                      <div className="flex gap-3">
                        <button onClick={() => setShowStockModeConfirm(null)}
                          className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition">
                          Batal
                        </button>
                        <button onClick={confirmStockModeChange}
                          className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition">
                          Ya, Beralih
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tax & Service Charge */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <Receipt className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Pajak & Service Charge</h2>
            </div>
            <div className="p-6 space-y-5">
              {/* PB1 / Pajak Restoran */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Pajak (PB1)</p>
                    <p className="text-xs text-gray-500">Pajak restoran yang dikenakan ke pelanggan</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setTaxConfig(c => ({ ...c, pb1_enabled: !c.pb1_enabled }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      taxConfig.pb1_enabled ? 'bg-blue-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      taxConfig.pb1_enabled ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>
                {taxConfig.pb1_enabled && (
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={taxConfig.tax_pct}
                      onChange={e => setTaxConfig(c => ({ ...c, tax_pct: parseFloat(e.target.value) || 0 }))}
                      className="w-20 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-center focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <span className="text-sm text-gray-500">%</span>
                  </div>
                )}
              </div>

              {/* Service Charge */}
              <div className="border-t border-gray-100 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Service Charge</p>
                    <p className="text-xs text-gray-500">Biaya layanan tambahan</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setTaxConfig(c => ({ ...c, service_charge_enabled: !c.service_charge_enabled }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      taxConfig.service_charge_enabled ? 'bg-blue-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      taxConfig.service_charge_enabled ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>
                {taxConfig.service_charge_enabled && (
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={taxConfig.service_charge_pct}
                      onChange={e => setTaxConfig(c => ({ ...c, service_charge_pct: parseFloat(e.target.value) || 0 }))}
                      className="w-20 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-center focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <span className="text-sm text-gray-500">%</span>
                  </div>
                )}
              </div>

              {/* Tax Inclusive */}
              {taxConfig.pb1_enabled && (
                <div className="border-t border-gray-100 pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Harga Termasuk Pajak</p>
                      <p className="text-xs text-gray-500">Harga menu sudah include pajak</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setTaxConfig(c => ({ ...c, tax_inclusive: !c.tax_inclusive }))}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        taxConfig.tax_inclusive ? 'bg-blue-600' : 'bg-gray-200'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        taxConfig.tax_inclusive ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                </div>
              )}

              {/* Preview */}
              {(taxConfig.pb1_enabled || taxConfig.service_charge_enabled) && (
                <div className="border-t border-gray-100 pt-4">
                  <p className="text-xs text-gray-500 mb-2">Contoh pesanan Rp100.000:</p>
                  <div className="bg-gray-50 rounded-lg p-3 text-xs space-y-1">
                    <div className="flex justify-between text-gray-600">
                      <span>Subtotal</span><span>Rp100.000</span>
                    </div>
                    {taxConfig.pb1_enabled && !taxConfig.tax_inclusive && (
                      <div className="flex justify-between text-gray-600">
                        <span>Pajak ({taxConfig.tax_pct}%)</span>
                        <span>Rp{(100000 * taxConfig.tax_pct / 100).toLocaleString('id-ID')}</span>
                      </div>
                    )}
                    {taxConfig.pb1_enabled && taxConfig.tax_inclusive && (
                      <div className="flex justify-between text-gray-400 italic">
                        <span>Pajak ({taxConfig.tax_pct}%, termasuk)</span>
                        <span>Rp{Math.round(100000 - 100000 / (1 + taxConfig.tax_pct / 100)).toLocaleString('id-ID')}</span>
                      </div>
                    )}
                    {taxConfig.service_charge_enabled && (
                      <div className="flex justify-between text-gray-600">
                        <span>Service ({taxConfig.service_charge_pct}%)</span>
                        <span>Rp{(100000 * taxConfig.service_charge_pct / 100).toLocaleString('id-ID')}</span>
                      </div>
                    )}
                    <div className="flex justify-between font-bold text-gray-900 border-t border-gray-200 pt-1">
                      <span>Total</span>
                      <span>Rp{(() => {
                        let total = 100000;
                        if (taxConfig.service_charge_enabled) total += 100000 * taxConfig.service_charge_pct / 100;
                        if (taxConfig.pb1_enabled && !taxConfig.tax_inclusive) total += 100000 * taxConfig.tax_pct / 100;
                        return Math.round(total).toLocaleString('id-ID');
                      })()}</span>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={handleTaxSave}
                disabled={savingTax}
                className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {savingTax ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                {taxSaved ? 'Tersimpan!' : 'Simpan Pengaturan Pajak'}
              </button>
            </div>
          </div>

          {/* Billing */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <Receipt className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Langganan & Billing</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                Kelola paket langganan, lihat invoice, dan bayar tagihan.
              </p>
              <Link
                href="/dashboard/settings/billing"
                className="block w-full text-center px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-colors"
              >
                Kelola Langganan
              </Link>
            </div>
          </div>

          {/* Referral */}
          {referralCode && (
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-emerald-200 flex items-center gap-2">
                <Gift className="w-5 h-5 text-emerald-600" />
                <h2 className="text-lg font-bold text-gray-900">Referral Program</h2>
                <span className="ml-auto text-xs font-semibold text-emerald-700 bg-emerald-100 px-2 py-1 rounded-full">20% komisi</span>
              </div>
              <div className="p-6 space-y-4">
                <p className="text-sm text-gray-600">
                  Ajak pebisnis lain pakai Kasira. Kamu dapat <span className="font-bold text-emerald-700">20% komisi</span> dari langganan mereka setiap bulan!
                </p>

                {/* Code + Copy */}
                <div className="bg-white rounded-lg border border-emerald-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Kode referral kamu</p>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-gray-900 tracking-wider font-mono">{referralCode}</span>
                    <button
                      onClick={() => { navigator.clipboard.writeText(referralShareUrl); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                      className="ml-auto p-2 text-gray-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                      title="Salin link"
                    >
                      {copied ? <Check className="w-5 h-5 text-emerald-600" /> : <Copy className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Share buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => { navigator.clipboard.writeText(referralShareText); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-emerald-700 bg-emerald-100 rounded-lg hover:bg-emerald-200 transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                    {copied ? 'Tersalin!' : 'Salin Teks'}
                  </button>
                  <a
                    href={`https://wa.me/?text=${encodeURIComponent(referralShareText)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Share2 className="w-4 h-4" />
                    Share via WA
                  </a>
                </div>

                {/* Stats */}
                {referralStats && (
                  <div className="grid grid-cols-3 gap-3 pt-2">
                    <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                      <p className="text-2xl font-bold text-gray-900">{referralStats.total_referrals}</p>
                      <p className="text-xs text-gray-500">Referral</p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                      <p className="text-2xl font-bold text-emerald-600">Rp{((referralStats.pending_balance || 0) / 1000).toFixed(0)}rb</p>
                      <p className="text-xs text-gray-500">Pending</p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                      <p className="text-2xl font-bold text-gray-900">Rp{((referralStats.total_earned || 0) / 1000).toFixed(0)}rb</p>
                      <p className="text-xs text-gray-500">Dicairkan</p>
                    </div>
                  </div>
                )}

                {/* Referral list */}
                {referralStats?.referrals?.length > 0 && (
                  <div className="pt-2">
                    <p className="text-xs font-medium text-gray-500 mb-2">Merchant yang kamu referral:</p>
                    <div className="space-y-2">
                      {referralStats.referrals.map((r: any) => (
                        <div key={r.id} className="flex items-center justify-between bg-white rounded-lg border border-gray-200 px-3 py-2">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{r.referred_name}</p>
                            <p className="text-xs text-gray-500">{r.referred_tier}</p>
                          </div>
                          <p className="text-sm font-semibold text-emerald-600">Rp{((r.total_commission || 0) / 1000).toFixed(0)}rb</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
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
