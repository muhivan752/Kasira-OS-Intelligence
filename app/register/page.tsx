'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { sendOtp, registerTenant } from '@/app/actions/auth';
import { SefrekuensiOtpCard } from '@/components/auth/sefrekuensi-otp-card';
import { SEFREKUENSI_NAME, type OtpChannel } from '@/lib/brand';
import { Logo } from '@/components/ui/logo';
import { Loader2, ArrowLeft, Coffee, Utensils, Store, ShoppingBag, Gift, Phone, User, Lock, Ticket } from 'lucide-react';

type Step = 'phone' | 'otp' | 'details';

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-[var(--text-muted)]" /></div>}>
      <RegisterContent />
    </Suspense>
  );
}

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState<Step>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  // Kanal dipilih user di langkah 1. Kode nggak loncat kanal.
  const [channel, setChannel] = useState<OtpChannel>('whatsapp');
  const [sefreNotFound, setSefreNotFound] = useState(false);
  const [sefreLoading, setSefreLoading] = useState(false);
  const [businessName, setBusinessName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [businessType, setBusinessType] = useState('cafe');

  // Referral
  const [referralCode, setReferralCode] = useState('');
  const [referrerName, setReferrerName] = useState('');

  useEffect(() => {
    const ref = searchParams.get('ref');
    if (ref) {
      setReferralCode(ref.toUpperCase());
      fetch(`/api/v1/referrals/validate/${ref}`)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            setReferrerName(data.data.referrer_name);
          }
        })
        .catch(() => {});
    }
  }, [searchParams]);

  async function kirimKode(via: OtpChannel) {
    setError('');
    setSefreNotFound(false);
    const normalized = phone.startsWith('0') ? '62' + phone.slice(1) : phone;
    if (via === 'sefrekuensi') setSefreLoading(true); else setLoading(true);
    const res = await sendOtp(normalized, 'register', via);
    setLoading(false);
    setSefreLoading(false);
    if (!res.success) {
      if (res.code === 'SEFREKUENSI_NOT_FOUND') { setSefreNotFound(true); return; }
      setError(res.message || 'Gagal kirim OTP');
      return;
    }
    setChannel(res.channel);
    setPhone(normalized);
    setStep('otp');
  }

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    await kirimKode('whatsapp');
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (otp.length !== 6) { setError('OTP harus 6 digit'); return; }
    setStep('details');
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (pin !== pinConfirm) { setError('PIN tidak cocok'); return; }
    if (pin.length !== 6) { setError('PIN harus 6 digit'); return; }
    setLoading(true);
    const res = await registerTenant(phone, businessName, ownerName, pin, otp, businessType, referralCode || undefined);
    setLoading(false);
    if (!res.success) { setError(res.message || 'Registrasi gagal'); return; }
    router.push('/onboarding');
  }

  const stepLabel = step === 'phone' ? '// Langkah 1 dari 3' : step === 'otp' ? '// Langkah 2 dari 3' : '// Langkah 3 dari 3';

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center px-4 py-10 overflow-hidden">
      {/* Aurora glow backdrop */}
      <div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: 'var(--gradient-glow)' }} />
      <div aria-hidden className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-[420px] w-[620px] rounded-full blur-3xl opacity-40" style={{ background: 'var(--gradient-aurora)' }} />

      <div className="relative w-full max-w-[440px]">
        <div className="flex flex-col items-center text-center mb-6">
          <Logo size="lg" variant="brand" />
          <p className="ks-eyebrow mt-2">{stepLabel}</p>
        </div>

        {referrerName && (
          <div
            className="mb-4 rounded-[var(--radius-lg)] p-4 flex items-start gap-3"
            style={{ background: 'var(--brand-tint-2)', border: '1px solid color-mix(in srgb, var(--brand-secondary) 25%, transparent)' }}
          >
            <Gift className="w-5 h-5 text-[var(--brand-secondary)] mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-[var(--text-strong)]">Diundang oleh {referrerName}</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5 ks-mono">{referralCode}</p>
            </div>
          </div>
        )}

        <div className="ks-card p-7 sm:p-8">
          {/* STEP 1: Phone */}
          {step === 'phone' && (
            <>
              <h1 className="ks-display text-[28px] font-extrabold text-[var(--text-strong)] leading-tight mb-1">Daftar Selaris</h1>
              <p className="text-sm text-[var(--text-muted)] mb-6">Masukkan nomor HP aktif kamu. Kode masuk dikirim ke WhatsApp atau {SEFREKUENSI_NAME}.</p>
              <form onSubmit={handleSendOtp} className="space-y-4">
                <div>
                  <label className="ks-field-label">Nomor HP</label>
                  <div className="ks-field">
                    <span className="ks-field-icon"><Phone className="h-[18px] w-[18px]" /></span>
                    <input
                      type="tel"
                      inputMode="numeric"
                      required
                      autoFocus
                      placeholder="08xx atau 628xx"
                      value={phone}
                      onChange={e => setPhone(e.target.value)}
                      className="ks-mono"
                    />
                  </div>
                </div>
                {!referrerName && (
                  <div>
                    <label className="ks-field-label">Kode Referral <span className="normal-case font-normal text-[var(--text-muted)]">(opsional)</span></label>
                    <div className="ks-field">
                      <span className="ks-field-icon"><Ticket className="h-[18px] w-[18px]" /></span>
                      <input
                        type="text"
                        placeholder="Contoh: KAS-XXXXX"
                        value={referralCode}
                        onChange={e => setReferralCode(e.target.value.toUpperCase())}
                        className="ks-mono uppercase"
                      />
                    </div>
                  </div>
                )}
                {error && <p className="text-[var(--danger)] text-sm">{error}</p>}
                <button type="submit" disabled={loading || !phone} className="ks-btn ks-btn-lg">
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  Kirim kode ke WhatsApp
                </button>
                <SefrekuensiOtpCard
                  loading={sefreLoading || loading}
                  notFound={sefreNotFound}
                  onPick={() => kirimKode('sefrekuensi')}
                  onFallbackWhatsapp={() => kirimKode('whatsapp')}
                />
              </form>
              <p className="mt-6 text-center text-sm text-[var(--text-muted)]">
                Sudah punya akun?{' '}
                <Link href="/login" className="text-[var(--brand-secondary)] font-semibold hover:underline">Login</Link>
              </p>
            </>
          )}

          {/* STEP 2: OTP */}
          {step === 'otp' && (
            <>
              <button onClick={() => { setStep('phone'); setSefreNotFound(false); setError(''); }} className="inline-flex items-center gap-1 text-sm text-[var(--text-muted)] hover:text-[var(--text-body)] mb-4 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Ganti nomor
              </button>
              <h1 className="ks-display text-[28px] font-extrabold text-[var(--text-strong)] leading-tight mb-1">
                {channel === 'sefrekuensi' ? `Periksa ${SEFREKUENSI_NAME}` : 'Periksa WhatsApp'}
              </h1>
              <p className="text-sm text-[var(--text-muted)] mb-6">
                {channel === 'sefrekuensi'
                  ? <>Kode dikirim sebagai pesan di {SEFREKUENSI_NAME} ke <span className="ks-mono text-[var(--text-body)]">{phone}</span>. Cek pesan dari Yasmin.</>
                  : <>Kode dikirim ke WhatsApp <span className="ks-mono text-[var(--text-body)]">{phone}</span></>}
              </p>
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <div className="ks-field">
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    autoFocus
                    placeholder="••••••"
                    value={otp}
                    onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                    className="ks-mono text-center !text-2xl tracking-[0.5em]"
                  />
                </div>
                {error && <p className="text-[var(--danger)] text-sm">{error}</p>}
                <button type="submit" disabled={otp.length !== 6} className="ks-btn ks-btn-lg">
                  Verifikasi OTP
                </button>
              </form>
            </>
          )}

          {/* STEP 3: Details */}
          {step === 'details' && (
            <>
              <h1 className="ks-display text-[28px] font-extrabold text-[var(--text-strong)] leading-tight mb-1">Info Bisnis</h1>
              <p className="text-sm text-[var(--text-muted)] mb-6">Lengkapi data untuk membuat akun.</p>
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="ks-field-label">Tipe Bisnis</label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'cafe', name: 'Cafe', icon: Coffee },
                      { id: 'resto', name: 'Restoran', icon: Utensils },
                      { id: 'warung', name: 'Warung', icon: Store },
                      { id: 'other', name: 'Lainnya', icon: ShoppingBag },
                    ].map((t) => {
                      const active = businessType === t.id;
                      return (
                        <label
                          key={t.id}
                          className="flex items-center gap-2 p-3 cursor-pointer rounded-[var(--radius-md)] border-2 transition-all"
                          style={{
                            borderColor: active ? 'var(--brand-primary)' : 'var(--border-subtle)',
                            background: active ? 'var(--brand-tint)' : 'transparent',
                          }}
                        >
                          <input type="radio" name="btype" value={t.id} checked={active} onChange={e => setBusinessType(e.target.value)} className="sr-only" />
                          <t.icon className="w-5 h-5" style={{ color: active ? 'var(--brand-primary)' : 'var(--text-muted)' }} />
                          <span className="text-sm font-medium" style={{ color: active ? 'var(--text-strong)' : 'var(--text-body)' }}>{t.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
                <div>
                  <label className="ks-field-label">Nama Bisnis</label>
                  <div className="ks-field">
                    <span className="ks-field-icon"><Store className="h-[18px] w-[18px]" /></span>
                    <input type="text" required placeholder="Contoh: Kopi Nusantara" value={businessName} onChange={e => setBusinessName(e.target.value)} />
                  </div>
                </div>
                <div>
                  <label className="ks-field-label">Nama Pemilik</label>
                  <div className="ks-field">
                    <span className="ks-field-icon"><User className="h-[18px] w-[18px]" /></span>
                    <input type="text" required placeholder="Nama lengkap" value={ownerName} onChange={e => setOwnerName(e.target.value)} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="ks-field-label">PIN (6 digit)</label>
                    <div className="ks-field">
                      <input type="password" inputMode="numeric" maxLength={6} required placeholder="••••••" value={pin} onChange={e => setPin(e.target.value.replace(/\D/g, ''))} className="ks-mono text-center tracking-[0.35em]" />
                    </div>
                  </div>
                  <div>
                    <label className="ks-field-label">Konfirmasi PIN</label>
                    <div className="ks-field">
                      <input type="password" inputMode="numeric" maxLength={6} required placeholder="••••••" value={pinConfirm} onChange={e => setPinConfirm(e.target.value.replace(/\D/g, ''))} className="ks-mono text-center tracking-[0.35em]" />
                    </div>
                  </div>
                </div>
                {error && <p className="text-[var(--danger)] text-sm">{error}</p>}
                <button type="submit" disabled={loading || !businessName || !ownerName || pin.length !== 6} className="ks-btn ks-btn-lg">
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  Buat Akun
                </button>
                <p className="text-center text-xs text-[var(--text-muted)] leading-relaxed pt-1">
                  Dengan mendaftar, kamu setuju pada <Link href="/terms" className="font-semibold text-[var(--text-body)] hover:underline">Syarat</Link> &amp; <Link href="/privacy" className="font-semibold text-[var(--text-body)] hover:underline">Privasi</Link> Selaris.
                </p>
              </form>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
