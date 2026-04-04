'use client';

import { useState, useEffect } from 'react';
import { getOutlets, getPaymentStatus, setupPaymentOwnKey, removePaymentOwnKey } from '@/app/actions/api';
import { Loader2, CreditCard, CheckCircle2, AlertCircle, Eye, EyeOff, Trash2 } from 'lucide-react';

export default function PaymentSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [outlet, setOutlet] = useState<any>(null);
  const [paymentStatus, setPaymentStatus] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const o = outlets[0];
        setOutlet(o);
        const status = await getPaymentStatus(o.id);
        setPaymentStatus(status);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setSaving(true);
    setError('');
    setSuccess('');
    const res = await setupPaymentOwnKey(outlet.id, apiKey.trim());
    if (res.success) {
      setSuccess('API Key Xendit berhasil disimpan! QRIS sudah aktif.');
      setApiKey('');
      loadData();
    } else {
      setError(res.message || 'Gagal menyimpan API key');
    }
    setSaving(false);
  };

  const handleRemove = async () => {
    if (!confirm('Hapus API key Xendit? QRIS tidak akan bisa digunakan.')) return;
    setRemoving(true);
    setError('');
    const res = await removePaymentOwnKey(outlet.id);
    if (res.success) {
      setSuccess('API key dihapus. Outlet kembali ke mode Cash Only.');
      loadData();
    } else {
      setError(res.message || 'Gagal menghapus');
    }
    setRemoving(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="animate-spin w-6 h-6 text-gray-400" /></div>;

  const isConnected = paymentStatus?.is_connected;
  const mode = paymentStatus?.mode || 'none';

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pengaturan Pembayaran</h1>
        <p className="text-gray-500 text-sm mt-1">Aktifkan QRIS dengan memasukkan Secret Key Xendit Anda.</p>
      </div>

      {/* Status card */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-11 h-11 rounded-full flex items-center justify-center ${isConnected ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">
              {isConnected ? 'QRIS Aktif' : 'Cash Only'}
            </p>
            <p className="text-sm text-gray-500">
              {mode === 'own_key' && 'Menggunakan API Key Xendit Anda sendiri'}
              {mode === 'xenplatform' && 'Menggunakan Xendit xenPlatform (sub-account)'}
              {mode === 'none' && 'Belum terhubung ke Xendit'}
            </p>
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${isConnected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
          {isConnected ? 'Aktif' : 'Tidak Aktif'}
        </span>
      </div>

      {/* Alert */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /><p>{error}</p>
        </div>
      )}
      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-start gap-2 text-green-700 text-sm">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /><p>{success}</p>
        </div>
      )}

      {/* Form input own key */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">API Key Xendit</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Daftarkan akun Xendit Anda di{' '}
            <a href="https://dashboard.xendit.co" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              dashboard.xendit.co
            </a>
            , lalu copy Secret Key dari menu <strong>Settings → API Keys</strong>.
          </p>
        </div>
        <form onSubmit={handleSave} className="p-6 space-y-4">
          {mode === 'own_key' && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
              API Key sudah terpasang. Masukkan key baru di bawah untuk menggantinya.
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Secret Key Xendit</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="xnd_production_..."
                className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
              />
              <button type="button" onClick={() => setShowKey(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">Key disimpan terenkripsi dan tidak pernah ditampilkan ulang.</p>
          </div>

          <div className="flex items-center justify-between pt-2">
            {mode === 'own_key' && (
              <button
                type="button"
                onClick={handleRemove}
                disabled={removing}
                className="flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700 disabled:opacity-50"
              >
                {removing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Hapus API Key
              </button>
            )}
            <div className={mode === 'own_key' ? '' : 'ml-auto'}>
              <button
                type="submit"
                disabled={saving || !apiKey.trim()}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                {mode === 'own_key' ? 'Ganti API Key' : 'Simpan & Aktifkan QRIS'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Info box */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <p className="font-semibold mb-1">Cara mendapatkan Secret Key Xendit:</p>
        <ol className="list-decimal list-inside space-y-1 text-amber-700">
          <li>Buka <strong>dashboard.xendit.co</strong> dan login</li>
          <li>Pergi ke <strong>Settings → API Keys</strong></li>
          <li>Klik <strong>Generate Secret Key</strong></li>
          <li>Copy key yang diawali <code className="bg-amber-100 px-1 rounded">xnd_production_</code></li>
          <li>Paste di kolom di atas dan klik Simpan</li>
        </ol>
      </div>
    </div>
  );
}
