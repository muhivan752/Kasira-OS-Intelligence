'use client';

import { useState, useEffect } from 'react';
import { getOutlets, updateOutlet } from '@/app/actions/api';
import { Loader2, Store, Clock, Link as LinkIcon, CreditCard } from 'lucide-react';
import Link from 'next/link';

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [outlet, setOutlet] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    address: '',
    opening_hours: '',
    is_open: true
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
          opening_hours: data.opening_hours || '',
          is_open: data.is_open !== false // default true
        });
      }
    } catch (error) {
      console.error('Failed to load outlet data', error);
    } finally {
      setLoading(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    const res = await updateOutlet(outlet.id, formData);
    if (res.success) {
      alert('Pengaturan berhasil disimpan');
      loadData();
    } else {
      alert(res.message);
    }
    setSaving(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  const storefrontUrl = typeof window !== 'undefined' 
    ? `${window.location.origin}/store/${outlet?.slug}` 
    : `/store/${outlet?.slug}`;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pengaturan Outlet</h1>
        <p className="text-gray-500">Kelola informasi dasar dan operasional outlet Anda.</p>
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama Outlet</label>
                <input 
                  type="text" 
                  required
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nomor Telepon</label>
                <input 
                  type="tel" 
                  value={formData.phone}
                  onChange={e => setFormData({...formData, phone: e.target.value.replace(/\D/g, '')})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alamat Lengkap</label>
                <textarea 
                  rows={3}
                  value={formData.address}
                  onChange={e => setFormData({...formData, address: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                />
              </div>

              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900">Status Operasional</h3>
                    <p className="text-xs text-gray-500">Buka atau tutup toko Anda untuk pesanan online.</p>
                  </div>
                  <button 
                    type="button"
                    onClick={() => setFormData({...formData, is_open: !formData.is_open})}
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
                    onChange={e => setFormData({...formData, opening_hours: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button 
                  type="submit"
                  disabled={saving}
                  className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Simpan Perubahan
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Sidebar Settings */}
        <div className="space-y-6">
          {/* Storefront Link */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Link Storefront</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                Bagikan link ini ke pelanggan Anda untuk menerima pesanan online.
              </p>
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
            </div>
          </div>

          {/* Payment Settings Link */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold text-gray-900">Pembayaran</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                Atur metode pembayaran QRIS via Midtrans untuk menerima pembayaran non-tunai.
              </p>
              <Link 
                href="/dashboard/settings/payment"
                className="block w-full text-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Setup QRIS Midtrans
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
