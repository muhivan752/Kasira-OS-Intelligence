'use client';

import { useState, useEffect } from 'react';
import { getOutlets, setupPayment } from '@/app/actions/api';
import { Loader2, CreditCard, CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

export default function PaymentSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [outlet, setOutlet] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState({
    server_key: '',
    client_key: '',
    is_production: false
  });

  const [accordionOpen, setAccordionOpen] = useState(true);

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
        
        // If already connected, we might want to show masked keys
        // But for security, we usually don't send them back from backend
        // We'll just rely on the payment_status or similar field
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
    setError('');
    setSuccess('');
    
    const payload = {
      midtrans_server_key: formData.server_key,
      midtrans_client_key: formData.client_key,
      midtrans_is_production: formData.is_production
    };

    const res = await setupPayment(outlet.id, payload);
    if (res.success) {
      setSuccess('Integrasi Midtrans berhasil disimpan dan diuji!');
      setFormData({ server_key: '', client_key: '', is_production: formData.is_production });
      loadData();
    } else {
      setError(res.message || 'Key tidak valid');
    }
    setSaving(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  const isConnected = !!outlet?.midtrans_client_key;
  const isProd = outlet?.midtrans_is_production;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pengaturan Pembayaran</h1>
        <p className="text-gray-500">Integrasikan QRIS Midtrans untuk menerima pembayaran non-tunai.</p>
      </div>

      {/* Status Badge */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
            isConnected 
              ? isProd ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'
              : 'bg-red-100 text-red-600'
          }`}>
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">Status Integrasi</h2>
            <p className="text-sm text-gray-500">
              {isConnected 
                ? 'Pembayaran QRIS aktif dan siap digunakan.' 
                : 'Belum terhubung. Hanya menerima pembayaran tunai.'}
            </p>
          </div>
        </div>
        <div>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            isConnected 
              ? isProd ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              : 'bg-red-100 text-red-800'
          }`}>
            {isConnected 
              ? isProd ? 'QRIS Aktif - Production' : 'QRIS Aktif - Sandbox'
              : 'Cash Only'}
          </span>
        </div>
      </div>

      {/* Guide Accordion */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <button 
          onClick={() => setAccordionOpen(!accordionOpen)}
          className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <h3 className="text-sm font-bold text-gray-900">Panduan Integrasi (3 Langkah)</h3>
          {accordionOpen ? <ChevronUp className="w-5 h-5 text-gray-500" /> : <ChevronDown className="w-5 h-5 text-gray-500" />}
        </button>
        
        {accordionOpen && (
          <div className="p-6 space-y-4 border-t border-gray-200">
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">1</div>
              <div>
                <p className="text-sm font-medium text-gray-900">Daftar Akun Midtrans</p>
                <p className="text-sm text-gray-500 mt-1">
                  Buat akun di <a href="https://dashboard.midtrans.com/register" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">dashboard.midtrans.com</a> dan selesaikan proses verifikasi bisnis Anda.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">2</div>
              <div>
                <p className="text-sm font-medium text-gray-900">Dapatkan Access Keys</p>
                <p className="text-sm text-gray-500 mt-1">
                  Masuk ke dashboard Midtrans, buka menu <strong>Settings</strong> &gt; <strong>Access Keys</strong>.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">3</div>
              <div>
                <p className="text-sm font-medium text-gray-900">Copy & Paste Keys</p>
                <p className="text-sm text-gray-500 mt-1">
                  Salin <strong>Server Key</strong> dan <strong>Client Key</strong>, lalu paste ke form di bawah ini.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">Konfigurasi API Keys</h2>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-red-600 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <p>{error}</p>
            </div>
          )}
          
          {success && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-start gap-2 text-green-600 text-sm">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <p>{success}</p>
            </div>
          )}

          {isConnected && !formData.server_key && (
            <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-600 mb-2">Keys saat ini (Masked):</p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">Server Key:</span>
                  <span className="text-sm font-mono text-gray-900">sk-********************</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">Client Key:</span>
                  <span className="text-sm font-mono text-gray-900">{outlet.midtrans_client_key}</span>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-4">
                Isi form di bawah hanya jika Anda ingin memperbarui keys.
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Server Key</label>
            <input 
              type="password" 
              required={!isConnected}
              value={formData.server_key}
              onChange={e => setFormData({...formData, server_key: e.target.value})}
              placeholder="SB-Mid-server-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client Key</label>
            <input 
              type="text" 
              required={!isConnected}
              value={formData.client_key}
              onChange={e => setFormData({...formData, client_key: e.target.value})}
              placeholder="SB-Mid-client-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
            />
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <div className="relative">
                <input 
                  type="checkbox" 
                  className="sr-only"
                  checked={formData.is_production}
                  onChange={e => setFormData({...formData, is_production: e.target.checked})}
                />
                <div className={`block w-10 h-6 rounded-full transition-colors ${formData.is_production ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <div className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${formData.is_production ? 'translate-x-4' : ''}`}></div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Mode Production</p>
                <p className="text-xs text-gray-500">Aktifkan jika menggunakan keys Production (bukan Sandbox).</p>
              </div>
            </label>
          </div>

          <div className="pt-4 flex justify-end">
            <button 
              type="submit"
              disabled={saving || (!isConnected && (!formData.server_key || !formData.client_key))}
              className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {isConnected && (formData.server_key || formData.client_key) ? 'Perbarui & Test Ulang' : isConnected ? 'Test Ulang' : 'Test & Simpan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
