'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { sendOtp, registerTenant } from '@/app/actions/auth';
import { Logo } from '@/components/ui/logo';
import { Loader2, ArrowLeft } from 'lucide-react';

type Step = 'phone' | 'otp' | 'details';

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const normalized = phone.startsWith('0') ? '62' + phone.slice(1) : phone;
    setLoading(true);
    const res = await sendOtp(normalized);
    setLoading(false);
    if (!res.success) { setError(res.message || 'Gagal kirim OTP'); return; }
    setPhone(normalized);
    setStep('otp');
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (otp.length !== 6) { setError('OTP harus 6 digit'); return; }
    // Lanjut ke detail — OTP akan diverifikasi saat submit register
    setStep('details');
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (pin !== pinConfirm) { setError('PIN tidak cocok'); return; }
    if (pin.length !== 6) { setError('PIN harus 6 digit'); return; }
    setLoading(true);
    const res = await registerTenant(phone, businessName, ownerName, pin, otp);
    setLoading(false);
    if (!res.success) { setError(res.message || 'Registrasi gagal'); return; }
    router.push('/onboarding');
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Logo size="lg" variant="light" />
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          {/* STEP 1: Phone */}
          {step === 'phone' && (
            <>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Daftar Kasira</h1>
              <p className="text-gray-500 mb-6">Masukkan nomor WhatsApp aktif kamu</p>
              <form onSubmit={handleSendOtp} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nomor WhatsApp</label>
                  <input
                    type="tel"
                    required
                    placeholder="08xx atau 628xx"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none text-lg"
                  />
                </div>
                {error && <p className="text-red-500 text-sm">{error}</p>}
                <button
                  type="submit"
                  disabled={loading || !phone}
                  className="w-full py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  Kirim OTP via WhatsApp
                </button>
              </form>
              <p className="mt-6 text-center text-sm text-gray-500">
                Sudah punya akun?{' '}
                <Link href="/login" className="text-emerald-600 font-semibold hover:underline">Login</Link>
              </p>
            </>
          )}

          {/* STEP 2: OTP */}
          {step === 'otp' && (
            <>
              <button onClick={() => setStep('phone')} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
                <ArrowLeft className="w-4 h-4" /> Ganti nomor
              </button>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Masukkan OTP</h1>
              <p className="text-gray-500 mb-6">Kode OTP dikirim ke WhatsApp <span className="font-semibold text-gray-800">{phone}</span></p>
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  required
                  placeholder="6 digit OTP"
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none text-2xl tracking-widest text-center font-mono"
                />
                {error && <p className="text-red-500 text-sm">{error}</p>}
                <button
                  type="submit"
                  disabled={otp.length !== 6}
                  className="w-full py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 disabled:opacity-50 transition-colors"
                >
                  Verifikasi OTP
                </button>
              </form>
            </>
          )}

          {/* STEP 3: Details */}
          {step === 'details' && (
            <>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Info Bisnis</h1>
              <p className="text-gray-500 mb-6">Lengkapi data untuk membuat akun</p>
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nama Bisnis</label>
                  <input
                    type="text"
                    required
                    placeholder="Contoh: Kopi Nusantara"
                    value={businessName}
                    onChange={e => setBusinessName(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nama Pemilik</label>
                  <input
                    type="text"
                    required
                    placeholder="Nama lengkap"
                    value={ownerName}
                    onChange={e => setOwnerName(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">PIN (6 digit)</label>
                  <input
                    type="password"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    placeholder="••••••"
                    value={pin}
                    onChange={e => setPin(e.target.value.replace(/\D/g, ''))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none text-center tracking-widest text-xl font-mono"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Konfirmasi PIN</label>
                  <input
                    type="password"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    placeholder="••••••"
                    value={pinConfirm}
                    onChange={e => setPinConfirm(e.target.value.replace(/\D/g, ''))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none text-center tracking-widest text-xl font-mono"
                  />
                </div>
                {error && <p className="text-red-500 text-sm">{error}</p>}
                <button
                  type="submit"
                  disabled={loading || !businessName || !ownerName || pin.length !== 6}
                  className="w-full py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  Buat Akun
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
