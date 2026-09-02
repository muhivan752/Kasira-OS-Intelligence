'use client';

import { useState, useEffect } from 'react';
import { getOutlets, getCashiers, createCashier, toggleCashierActive, resetCashierPin, getCurrentShift, getUncountedShifts, countShift } from '@/app/actions/api';
import { Plus, Edit2, Loader2, X, KeyRound } from 'lucide-react';

export default function KasirPage() {
  const [loading, setLoading] = useState(true);
  const [cashiers, setCashiers] = useState<any[]>([]);
  const [outletId, setOutletId] = useState<string>('');
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isResetPinOpen, setIsResetPinOpen] = useState(false);
  const [selectedCashier, setSelectedCashier] = useState<any>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    pin: ''
  });
  const [newPin, setNewPin] = useState('');
  const [saving, setSaving] = useState(false);

  // Sesi kas (shift otomatis, gelombang 2)
  const [shift, setShift] = useState<any>(null);
  const [uncounted, setUncounted] = useState<any[]>([]);
  const [counting, setCounting] = useState<any>(null);
  const [countValue, setCountValue] = useState('');
  const [countSaving, setCountSaving] = useState(false);

  async function loadShift(id: string) {
    const [cur, unc] = await Promise.all([getCurrentShift(id), getUncountedShifts(id)]);
    // Tanpa sesi server tetap kirim { status: null, shift_mode } — bukan sesi.
    setShift(cur && cur.id ? cur : null);
    setUncounted(unc || []);
  }

  const rp = (n: any) => n == null ? '-' : 'Rp ' + Math.round(Number(n)).toLocaleString('id-ID');
  const tgl = (iso?: string | null) => iso ? new Date(iso).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-';

  const submitCount = async () => {
    if (!counting) return;
    const val = Number(countValue);
    if (!Number.isFinite(val) || val < 0) return;
    setCountSaving(true);
    try {
      await countShift(counting.id, val);
      setCounting(null);
      setCountValue('');
      if (outletId) await loadShift(outletId);
    } catch (e: any) {
      alert(e?.message || 'Gagal mencatat hitungan');
    } finally {
      setCountSaving(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const id = outlets[0].id;
        setOutletId(id);
        const data = await getCashiers(id);
        setCashiers(data || []);
        await loadShift(id);
      }
    } catch (error) {
      console.error('Failed to load cashiers', error);
    } finally {
      setLoading(false);
    }
  }

  const handleToggleActive = async (userId: string, currentStatus: boolean) => {
    const newStatus = !currentStatus;
    setCashiers(cashiers.map(c => c.id === userId ? { ...c, is_active: newStatus } : c));
    
    const success = await toggleCashierActive(userId, newStatus);
    if (!success) {
      setCashiers(cashiers.map(c => c.id === userId ? { ...c, is_active: currentStatus } : c));
      alert('Gagal mengubah status kasir');
    }
  };

  const openModal = () => {
    setFormData({ name: '', phone: '', pin: '' });
    setIsModalOpen(true);
  };

  const openResetPin = (cashier: any) => {
    setSelectedCashier(cashier);
    setNewPin('');
    setIsResetPinOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    if (!formData.phone.startsWith('628')) {
      alert('Nomor HP harus diawali dengan 628');
      setSaving(false);
      return;
    }

    if (formData.pin.length !== 6) {
      alert('PIN harus 6 digit');
      setSaving(false);
      return;
    }

    const payload = {
      outlet_id: outletId,
      name: formData.name,
      phone: formData.phone,
      pin: formData.pin,
      role: 'cashier'
    };

    const res = await createCashier(payload);

    if (res.success) {
      setIsModalOpen(false);
      loadData();
    } else {
      alert(res.message);
    }
    setSaving(false);
  };

  const handleResetPin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPin.length !== 6) {
      alert('PIN harus 6 digit');
      return;
    }

    setSaving(true);
    const success = await resetCashierPin(selectedCashier.id, newPin);
    if (success) {
      setIsResetPinOpen(false);
      alert('PIN berhasil direset');
    } else {
      alert('Gagal mereset PIN');
    }
    setSaving(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Memuat...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kelola Kasir</h1>
          <p className="text-gray-500">Tambah dan atur akses kasir untuk outlet Anda.</p>
        </div>
        <button 
          onClick={openModal}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Tambah Kasir
        </button>
      </div>

      {/* Sesi kas. Terbuka sendiri di transaksi pertama, tutup sendiri 04.00.
          Pemilik lihat semua angka; kasir di mode Standar menghitung tanpa
          melihat angka harapan, jadi selisihnya cuma kelihatan di sini. */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-gray-900">Sesi kas sekarang</h2>
            {shift && <span className="rounded-full bg-green-50 px-2.5 py-1 text-xs font-semibold text-green-700">Berjalan</span>}
          </div>
          {!shift ? (
            <p className="mt-3 text-sm text-gray-500">Belum ada sesi berjalan. Sesi terbuka sendiri di transaksi pertama.</p>
          ) : (
            <div className="mt-3 space-y-2 text-sm">
              <p className="text-gray-600">Dibuka {tgl(shift.start_time)}{shift.opened_by_name ? ` oleh ${shift.opened_by_name}` : ''}{shift.opened_by === 'auto' ? ' (otomatis)' : ''}</p>
              {shift.locked_to_name && (
                <p className="text-amber-700">Laci terkunci ke {shift.locked_to_name} (mode Ketat)</p>
              )}
              {shift.review?.length > 0 && (
                <div className="pt-1">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Rekap per kasir</p>
                  <ul className="mt-1 divide-y divide-gray-100">
                    {shift.review.map((r: any) => (
                      <li key={r.user_id} className="flex items-center justify-between py-1.5">
                        <span className="text-gray-900">{r.name} <span className="text-gray-400">· {r.orders} pesanan</span></span>
                        <span className="text-gray-700">tunai {rp(r.cash)} · QRIS {rp(r.qris)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Modal awal</p><p className="font-semibold text-gray-900">{rp(shift.starting_cash)}</p></div>
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Penjualan tunai</p><p className="font-semibold text-gray-900">{rp(shift.total_cash_sales)}</p></div>
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Penjualan QRIS</p><p className="font-semibold text-gray-900">{rp(shift.total_qris_sales)}</p></div>
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Mode kas</p><p className="font-semibold text-gray-900 capitalize">{shift.shift_mode || 'ringan'}</p></div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h2 className="font-bold text-gray-900">Kas belum dihitung</h2>
          {uncounted.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">Semua sesi 14 hari terakhir sudah dihitung.</p>
          ) : (
            <ul className="mt-3 divide-y divide-gray-100">
              {uncounted.map((u) => (
                <li key={u.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <div>
                    <p className="font-medium text-gray-900">{tgl(u.start_time)}{u.opened_by_name ? ` · ${u.opened_by_name}` : ''}</p>
                    <p className="text-xs text-gray-500">{u.status === 'paused' ? 'Dijeda' : 'Ditutup sistem 04.00'} · perkiraan {rp(u.expected_ending_cash)}</p>
                  </div>
                  <button onClick={() => { setCounting(u); setCountValue(''); }} className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">Catat hitungan</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {counting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl">
            <h3 className="font-bold text-gray-900">Hitungan kas sesi {tgl(counting.start_time)}</h3>
            <p className="mt-1 text-sm text-gray-500">Perkiraan sistem {rp(counting.expected_ending_cash)}. Masukkan uang yang benar-benar ada.</p>
            <input type="number" min="0" value={countValue} onChange={(e) => setCountValue(e.target.value)} placeholder="0"
              className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setCounting(null)} className="rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">Batal</button>
              <button onClick={submitCount} disabled={countSaving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{countSaving ? 'Menyimpan…' : 'Simpan'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Cashier List */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Nama Kasir</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Nomor HP</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Status</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {cashiers.length > 0 ? (
                cashiers.map((cashier) => (
                  <tr key={cashier.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                          {(cashier.full_name || '?').charAt(0).toUpperCase()}
                        </div>
                        <p className="text-sm font-medium text-gray-900">{cashier.full_name}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {cashier.phone}
                    </td>
                    <td className="px-6 py-4">
                      <button 
                        onClick={() => handleToggleActive(cashier.id, cashier.is_active)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                          cashier.is_active ? 'bg-blue-600' : 'bg-gray-200'
                        }`}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          cashier.is_active ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => openResetPin(cashier)}
                        title="Reset PIN"
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        <KeyRound className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                    Belum ada kasir terdaftar
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Cashier Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">Tambah Kasir Baru</h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama Lengkap</label>
                <input 
                  type="text" 
                  required
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nomor WhatsApp</label>
                <input 
                  type="tel" 
                  required
                  placeholder="628..."
                  value={formData.phone}
                  onChange={e => setFormData({...formData, phone: e.target.value.replace(/\D/g, '')})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">PIN (6 Digit)</label>
                <input 
                  type="text" 
                  required
                  maxLength={6}
                  placeholder="123456"
                  value={formData.pin}
                  onChange={e => setFormData({...formData, pin: e.target.value.replace(/\D/g, '')})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none tracking-widest text-center"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Batal
                </button>
                <button 
                  type="submit"
                  disabled={saving}
                  className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset PIN Modal */}
      {isResetPinOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">Reset PIN Kasir</h3>
              <button 
                onClick={() => setIsResetPinOpen(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleResetPin} className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                Masukkan PIN baru untuk kasir <strong>{selectedCashier?.full_name}</strong>.
              </p>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">PIN Baru (6 Digit)</label>
                <input 
                  type="text" 
                  required
                  maxLength={6}
                  placeholder="123456"
                  value={newPin}
                  onChange={e => setNewPin(e.target.value.replace(/\D/g, ''))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none tracking-widest text-center"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setIsResetPinOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Batal
                </button>
                <button 
                  type="submit"
                  disabled={saving || newPin.length !== 6}
                  className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Reset PIN
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
