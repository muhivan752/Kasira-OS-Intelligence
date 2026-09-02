'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { sendOtp, verifyOtp } from '@/app/actions/auth';
import { Loader2, ArrowLeft, ArrowRight, Phone } from 'lucide-react';
import { Logo } from '@/components/ui/logo';

export default function LoginPage() {
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(0);
  const router = useRouter();

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown > 0) {
      timer = setInterval(() => setCountdown(c => c - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [countdown]);

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.startsWith('628')) {
      setError('Nomor HP harus diawali dengan 628');
      return;
    }

    setLoading(true);
    setError('');

    const res = await sendOtp(phone);
    if (res.success) {
      setStep('otp');
      setCountdown(60);
    } else {
      setError(res.message);
    }
    setLoading(false);
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length !== 6) {
      setError('OTP harus 6 digit');
      return;
    }

    setLoading(true);
    setError('');

    const res = await verifyOtp(phone, otp);
    if (res.success) {
      router.push('/dashboard');
    } else {
      setError(res.message);
      setLoading(false);
    }
  };

  const backToPhone = () => {
    setStep('phone');
    setOtp('');
    setError('');
  };

  return (
    <main className="relative min-h-screen flex items-center justify-center px-4 py-10 overflow-hidden">
      {/* Aurora glow backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{ background: 'var(--gradient-glow)' }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-[420px] w-[620px] rounded-full blur-3xl opacity-40"
        style={{ background: 'var(--gradient-aurora)' }}
      />

      <div className="relative w-full max-w-[420px]">
        {/* Brand */}
        <div className="flex flex-col items-center text-center mb-7">
          <Logo size="lg" variant="brand" className="justify-center" />
          <p className="mt-3 text-[15px] ks-display font-bold text-[var(--text-strong)]">
            Kasir yang ngerti bisnismu
          </p>
        </div>

        {/* Card */}
        <div className="ks-card p-7 sm:p-8">
          <div className="mb-6">
            <h1 className="ks-display text-[30px] font-extrabold text-[var(--text-strong)] leading-tight">
              {step === 'phone' ? 'Masuk' : 'Verifikasi'}
            </h1>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {step === 'phone'
                ? 'Masuk ke dashboard owner lewat WhatsApp.'
                : (
                  <>Kode 6 digit dikirim ke{' '}
                    <span className="ks-mono text-[var(--text-body)]">{phone}</span>
                  </>
                )}
            </p>
          </div>

          {error && (
            <div
              className="mb-5 flex items-start gap-2 rounded-[var(--radius-md)] px-3.5 py-3 text-sm"
              style={{
                background: 'color-mix(in srgb, var(--danger) 12%, transparent)',
                color: 'var(--danger)',
                border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)',
              }}
            >
              <span>{error}</span>
            </div>
          )}

          {step === 'phone' ? (
            <form className="space-y-4" onSubmit={handleSendOtp}>
              <div>
                <label htmlFor="phone" className="ks-field-label">Nomor WhatsApp</label>
                <div className="ks-field">
                  <span className="ks-field-icon"><Phone className="h-[18px] w-[18px]" /></span>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    inputMode="numeric"
                    required
                    autoFocus
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                    placeholder="628123456789"
                    className="ks-mono"
                  />
                </div>
              </div>

              <button type="submit" disabled={loading || phone.length < 10} className="ks-btn ks-btn-lg">
                {loading ? (
                  <Loader2 className="animate-spin h-5 w-5" />
                ) : (
                  <>Kirim OTP <ArrowRight className="h-[18px] w-[18px]" /></>
                )}
              </button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handleVerifyOtp}>
              <div>
                <label htmlFor="otp" className="ks-field-label">Kode OTP</label>
                <div className="ks-field">
                  <input
                    id="otp"
                    name="otp"
                    type="text"
                    inputMode="numeric"
                    required
                    autoFocus
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="••••••"
                    className="ks-mono text-center !text-2xl tracking-[0.5em]"
                  />
                </div>
              </div>

              <button type="submit" disabled={loading || otp.length !== 6} className="ks-btn ks-btn-lg">
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Verifikasi'}
              </button>

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={backToPhone}
                  className="inline-flex items-center gap-1 text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text-body)] transition-colors"
                >
                  <ArrowLeft className="h-4 w-4" /> Ganti nomor
                </button>
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={countdown > 0 || loading}
                  className="text-sm font-semibold text-[var(--brand-secondary)] hover:text-[var(--brand-secondary-hover)] disabled:text-[var(--text-muted)] disabled:cursor-not-allowed transition-colors"
                >
                  {countdown > 0 ? `Kirim ulang ${countdown}s` : 'Kirim ulang'}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-[var(--text-muted)] leading-relaxed">
          Dengan masuk, kamu setuju pada{' '}
          <a href="/terms" className="font-semibold text-[var(--text-body)] hover:underline">Syarat</a> &amp;{' '}
          <a href="/privacy" className="font-semibold text-[var(--text-body)] hover:underline">Privasi</a> Selaris.
        </p>
      </div>
    </main>
  );
}
