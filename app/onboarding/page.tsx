'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getOutlets, updateOutlet, createProduct, setupPayment } from '@/app/actions/api';
import { Loader2, CheckCircle2, Store, Coffee, Utensils, ShoppingBag, ChevronRight, Download } from 'lucide-react';

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [outlet, setOutlet] = useState<any>(null);
  const router = useRouter();

  // Step 1: Business Type
  const [businessType, setBusinessType] = useState('');

  // Step 2: First Menu
  const [menuData, setMenuData] = useState({ name: '', price: '' });

  // Step 3: QRIS Setup
  const [qrisData, setQrisData] = useState({ server_key: '', client_key: '', is_production: false });

  useEffect(() => {
    async function loadData() {
      try {
        const outlets = await getOutlets();
        if (outlets && outlets.length > 0) {
          setOutlet(outlets[0]);
        } else {
          // If no outlet, they shouldn't be here, but we'll handle it gracefully
          router.push('/dashboard');
        }
      } catch (error) {
        console.error('Failed to load outlet', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [router]);

  const handleStep1 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessType) return;
    
    setSaving(true);
    // We might save business type to outlet settings or just proceed
    // For now, just proceed to step 2
    setStep(2);
    setSaving(false);
  };

  const handleStep2 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!menuData.name || !menuData.price) return;
    
    setSaving(true);
    const res = await createProduct({
      outlet_id: outlet.id,
      name: menuData.name,
      price: parseFloat(menuData.price),
      stock: 100, // Default stock
      is_active: true
    });
    
    if (res.success) {
      setStep(3);
    } else {
      alert(res.message);
    }
    setSaving(false);
  };

  const handleStep3 = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!qrisData.server_key || !qrisData.client_key) {
      // Skip
      setStep(4);
      return;
    }
    
    setSaving(true);
    const payload = {
      midtrans_server_key: qrisData.server_key,
      midtrans_client_key: qrisData.client_key,
      midtrans_is_production: qrisData.is_production
    };

    const res = await setupPayment(outlet.id, payload);
    if (res.success) {
      setStep(4);
    } else {
      alert(res.message || 'Key tidak valid. Silakan periksa kembali atau lewati langkah ini.');
    }
    setSaving(false);
  };

  const handleSkipStep3 = () => {
    setStep(4);
  };

  const finishOnboarding = () => {
    router.push('/dashboard');
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex flex-col items-center relative z-10">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors ${
                  step > i ? 'bg-green-500 text-white' : 
                  step === i ? 'bg-blue-600 text-white ring-4 ring-blue-100' : 
                  'bg-gray-200 text-gray-500'
                }`}>
                  {step > i ? <CheckCircle2 className="w-6 h-6" /> : i}
                </div>
                <span className={`mt-2 text-xs font-medium ${step >= i ? 'text-gray-900' : 'text-gray-500'}`}>
                  {i === 1 ? 'Tipe Bisnis' : i === 2 ? 'Menu Pertama' : i === 3 ? 'Pembayaran' : 'Selesai'}
                </span>
              </div>
            ))}
            <div className="absolute top-5 left-0 w-full h-0.5 bg-gray-200 -z-0">
              <div 
                className="h-full bg-blue-600 transition-all duration-300 ease-in-out"
                style={{ width: `${((step - 1) / 3) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          {step === 1 && (
            <div className="p-8">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900">Apa tipe bisnis Anda?</h2>
                <p className="text-gray-500 mt-2">Pilih kategori yang paling sesuai dengan usaha Anda.</p>
              </div>
              
              <form onSubmit={handleStep1} className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { id: 'cafe', name: 'Cafe / Coffee Shop', icon: Coffee },
                    { id: 'resto', name: 'Restoran', icon: Utensils },
                    { id: 'warung', name: 'Warung Makan', icon: Store },
                    { id: 'lain', name: 'Lainnya', icon: ShoppingBag },
                  ].map((type) => (
                    <label 
                      key={type.id}
                      className={`
                        relative flex flex-col items-center p-6 cursor-pointer rounded-xl border-2 transition-all
                        ${businessType === type.id 
                          ? 'border-blue-600 bg-blue-50' 
                          : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                        }
                      `}
                    >
                      <input 
                        type="radio" 
                        name="business_type" 
                        value={type.id} 
                        checked={businessType === type.id}
                        onChange={(e) => setBusinessType(e.target.value)}
                        className="sr-only"
                      />
                      <type.icon className={`w-10 h-10 mb-3 ${businessType === type.id ? 'text-blue-600' : 'text-gray-400'}`} />
                      <span className={`font-medium ${businessType === type.id ? 'text-blue-900' : 'text-gray-900'}`}>
                        {type.name}
                      </span>
                    </label>
                  ))}
                </div>
                
                <div className="pt-6 flex justify-end">
                  <button 
                    type="submit"
                    disabled={!businessType || saving}
                    className="flex items-center justify-center px-6 py-3 text-base font-medium text-white bg-blue-600 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    Lanjut <ChevronRight className="w-5 h-5 ml-2" />
                  </button>
                </div>
              </form>
            </div>
          )}

          {step === 2 && (
            <div className="p-8">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900">Tambahkan Menu Pertama</h2>
                <p className="text-gray-500 mt-2">Mulai dengan menambahkan satu menu andalan Anda.</p>
              </div>
              
              <form onSubmit={handleStep2} className="space-y-6 max-w-md mx-auto">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nama Menu</label>
                  <input 
                    type="text" 
                    required
                    placeholder="Contoh: Nasi Goreng Spesial"
                    value={menuData.name}
                    onChange={e => setMenuData({...menuData, name: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-lg"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Harga (Rp)</label>
                  <input 
                    type="number" 
                    required
                    min="0"
                    placeholder="25000"
                    value={menuData.price}
                    onChange={e => setMenuData({...menuData, price: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-lg"
                  />
                </div>
                
                <div className="pt-6 flex justify-between items-center">
                  <button 
                    type="button"
                    onClick={() => setStep(1)}
                    className="text-gray-500 hover:text-gray-700 font-medium"
                  >
                    Kembali
                  </button>
                  <button 
                    type="submit"
                    disabled={!menuData.name || !menuData.price || saving}
                    className="flex items-center justify-center px-6 py-3 text-base font-medium text-white bg-blue-600 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
                    Simpan & Lanjut <ChevronRight className="w-5 h-5 ml-2" />
                  </button>
                </div>
              </form>
            </div>
          )}

          {step === 3 && (
            <div className="p-8">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900">Terima Pembayaran QRIS</h2>
                <p className="text-gray-500 mt-2">Hubungkan akun Midtrans untuk menerima pembayaran non-tunai (Opsional).</p>
              </div>
              
              <form onSubmit={handleStep3} className="space-y-6 max-w-md mx-auto">
                <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 mb-6">
                  <p className="text-sm text-blue-800">
                    Anda bisa melewati langkah ini dan mengaturnya nanti di menu <strong>Pengaturan &gt; Pembayaran</strong>.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Server Key</label>
                  <input 
                    type="password" 
                    value={qrisData.server_key}
                    onChange={e => setQrisData({...qrisData, server_key: e.target.value})}
                    placeholder="SB-Mid-server-..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Client Key</label>
                  <input 
                    type="text" 
                    value={qrisData.client_key}
                    onChange={e => setQrisData({...qrisData, client_key: e.target.value})}
                    placeholder="SB-Mid-client-..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
                  />
                </div>

                <div className="pt-6 flex justify-between items-center">
                  <button 
                    type="button"
                    onClick={handleSkipStep3}
                    className="text-gray-500 hover:text-gray-700 font-medium"
                  >
                    Lewati
                  </button>
                  <button 
                    type="submit"
                    disabled={saving || Boolean(!qrisData.server_key && qrisData.client_key) || Boolean(qrisData.server_key && !qrisData.client_key)}
                    className="flex items-center justify-center px-6 py-3 text-base font-medium text-white bg-blue-600 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
                    {qrisData.server_key && qrisData.client_key ? 'Test & Lanjut' : 'Lanjut'} <ChevronRight className="w-5 h-5 ml-2" />
                  </button>
                </div>
              </form>
            </div>
          )}

          {step === 4 && (
            <div className="p-8 text-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 className="w-10 h-10 text-green-600" />
              </div>
              
              <h2 className="text-3xl font-bold text-gray-900 mb-4">Setup Selesai!</h2>
              <p className="text-gray-600 max-w-md mx-auto mb-8">
                Outlet Anda sudah siap. Sekarang Anda bisa mengunduh aplikasi Kasir (APK) untuk digunakan di tablet atau smartphone Android di toko Anda.
              </p>
              
              <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 max-w-md mx-auto mb-8 text-left">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Download className="w-5 h-5 text-blue-600" />
                  Instruksi Instalasi
                </h3>
                <ol className="list-decimal list-inside space-y-3 text-sm text-gray-600">
                  <li>Unduh file APK melalui tombol di bawah.</li>
                  <li>Buka file APK yang sudah diunduh di perangkat Android Anda.</li>
                  <li>Jika muncul peringatan keamanan, pilih <strong>Settings</strong> dan aktifkan <strong>Allow from this source</strong>.</li>
                  <li>Lanjutkan instalasi hingga selesai.</li>
                  <li>Buka aplikasi Kasira dan login menggunakan nomor HP Anda.</li>
                </ol>
              </div>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <button 
                  className="w-full sm:w-auto flex items-center justify-center px-6 py-3 text-base font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-xl hover:bg-blue-100 transition-colors"
                >
                  <Download className="w-5 h-5 mr-2" />
                  Unduh APK Kasir
                </button>
                <button 
                  onClick={finishOnboarding}
                  className="w-full sm:w-auto flex items-center justify-center px-8 py-3 text-base font-medium text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-colors"
                >
                  Masuk ke Dashboard
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
