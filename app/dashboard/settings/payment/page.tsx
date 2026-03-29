'use client';

import { useState, useEffect } from 'react';
import { getOutlets, setupPayment } from '@/app/actions/api';
import { Loader2, CreditCard, CheckCircle2, AlertCircle } from 'lucide-react';

export default function PaymentSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [outlet, setOutlet] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState({
    xendit_business_id: ''
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
    
    // In xenPlatform architecture, this setup API should be adjusted to store xendit_business_id
    const payload = {
      xendit_business_id: formData.xendit_business_id,
    };

    const res = await setupPayment(outlet.id, payload);
    if (res.success) {
      setSuccess('Sub-Account Xendit berhasil dihubungkan!');
      setFormData({ xendit_business_id: '' });
      loadData();
    } else {
      setError(res.message || 'ID tidak valid');
    }
    setSaving(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  const isConnected = !!outlet?.xendit_business_id;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pengaturan Pembayaran</h1>
        <p className="text-gray-500">Integrasikan QRIS Xendit (xenPlatform) untuk menerima pembayaran.</p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
            isConnected ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
          }`}>
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">Status Integrasi</h2>
            <p className="text-sm text-gray-500">
              {isConnected 
                ? 'Sub-Account Xendit aktif dan siap menerima QRIS.' 
                : 'Belum terhubung. Hanya menerima pembayaran tunai.'}
            </p>
          </div>
        </div>
        <div>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {isConnected ? 'QRIS Aktif' : 'Cash Only'}
          </span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">Konfigurasi xenPlatform</h2>
          <p className="text-sm text-gray-500 mt-1">
            Sistem kami menggunakan arsitektur Master-Sub Account. Uang hasil transaksi langsung masuk ke rekening Anda setelah diproses oleh Kasira.
          </p>
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

          {isConnected && (
            <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-sm font-medium text-gray-700">Sub-Account ID Aktif:</p>
              <p className="text-sm font-mono text-gray-900 mt-1">{outlet.xendit_business_id}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Xendit Business ID</label>
            <input 
              type="text" 
              required={!isConnected}
              value={formData.xendit_business_id}
              onChange={e => setFormData({...formData, xendit_business_id: e.target.value})}
              placeholder="Masukan manual Business ID Anda..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-2">
              (Isi form manual ini hanya jika Sub-Account Anda didaftarkan di luar integrasi otomatis API Kasira.)
            </p>
          </div>

          <div className="pt-4 flex justify-end">
            <button 
              type="submit"
              disabled={saving}
              className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {isConnected ? 'Perbarui ID' : 'Hubungkan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
