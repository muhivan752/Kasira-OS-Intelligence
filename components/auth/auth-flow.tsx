'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { getAuthProviders, registerTenant, sendOtp, signInGoogle, verifyGooglePhone, verifyOtp, verifyRegistrationOtp } from '@/app/actions/auth';
import { SEFREKUENSI_PLAY_URL, type OtpChannel } from '@/lib/brand';
import { googleIdToken, prepareGoogleAuth, type FirebaseWebConfig } from '@/lib/google-auth';
import { AuthShell } from './auth-shell';
import { GoogleButton } from './google-button';

type Step = 'choice' | 'phone' | 'otp' | 'business';
const businesses = [{ value: 'cafe', label: 'Kafe' }, { value: 'warung', label: 'Warung' }, { value: 'resto', label: 'Restoran' }, { value: 'other', label: 'Usaha lain' }];

export function AuthFlow({ mode }: { mode: 'login' | 'register' }) {
  const router = useRouter();
  const search = useSearchParams();
  const [step, setStep] = useState<Step>('choice');
  const [config, setConfig] = useState<FirebaseWebConfig | null>(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [channel, setChannel] = useState<OtpChannel>('sefrekuensi');
  const [countdown, setCountdown] = useState(0);
  const [idToken, setIdToken] = useState('');
  const [googleProof, setGoogleProof] = useState('');
  const [otpProof, setOtpProof] = useState('');
  const [email, setEmail] = useState('');
  const [owner, setOwner] = useState('');
  const [business, setBusiness] = useState('');
  const [businessType, setBusinessType] = useState('cafe');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [referral, setReferral] = useState(search.get('ref') || '');

  useEffect(() => {
    let active = true;
    getAuthProviders().then(async result => {
      const next = result.data?.google?.web_config || null;
      if (next) await prepareGoogleAuth(next);
      if (active) { setConfig(next); setChecking(false); }
    }).catch(() => { if (active) { setConfig(null); setChecking(false); } });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(value => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  function enterDashboard() {
    const target = search.get('redirect');
    router.push(target?.startsWith('/dashboard') ? target : '/dashboard');
    router.refresh();
  }
  async function google() {
    if (!config) return;
    setBusy(true); setError('');
    try {
      const token = await googleIdToken(config);
      const result = await signInGoogle(token);
      if (!result.success) { setError(result.message || 'Login Google gagal.'); return; }
      if (result.data.registered) { enterDashboard(); return; }
      setIdToken(token); setOwner(result.data.name || ''); setEmail(result.data.email || ''); setStep('phone');
    } catch (caught) {
      const code = (caught as { code?: string }).code;
      if (!['auth/popup-closed-by-user', 'auth/cancelled-popup-request'].includes(code || '')) {
        setError(code === 'auth/popup-blocked' ? 'Izinkan jendela login Google di browser, lalu coba lagi.' : 'Google belum dapat digunakan. Coba lagi atau gunakan kode Sefrekuensi.');
      }
    } finally { setBusy(false); }
  }
  async function send(via: OtpChannel) {
    const digits = phone.replace(/\D/g, '');
    const normalized = digits.startsWith('0') ? `62${digits.slice(1)}` : digits.startsWith('8') ? `62${digits}` : digits;
    if (!/^628\d{7,12}$/.test(normalized)) { setError('Masukkan nomor HP yang valid, misalnya 081234567890.'); return; }
    setBusy(true); setError(''); setNotFound(false);
    const result = await sendOtp(normalized, idToken ? 'google' : mode, via, idToken || undefined);
    if (result.success) { setPhone(normalized); setChannel(result.channel); setOtp(''); setStep('otp'); setCountdown(60); }
    else { setError(result.message); setNotFound(result.code === 'SEFREKUENSI_NOT_FOUND'); }
    setBusy(false);
  }
  async function verify(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    if (idToken) {
      const result = await verifyGooglePhone(idToken, phone, otp);
      if (!result.success) setError(result.message || 'Kode tidak valid.');
      else if (result.data.registered) enterDashboard();
      else { setGoogleProof(result.data.google_proof); setStep('business'); }
    } else if (mode === 'register') {
      const result = await verifyRegistrationOtp(phone, otp);
      if (!result.success) setError(result.message || 'Kode tidak valid.');
      else { setOtpProof(result.data.otp_proof); setStep('business'); }
    } else {
      const result = await verifyOtp(phone, otp);
      if (result.success) enterDashboard(); else setError(result.message || 'Kode tidak valid.');
    }
    setBusy(false);
  }
  async function finish(event: React.FormEvent) {
    event.preventDefault(); setError('');
    if (pin !== confirmPin) { setError('Konfirmasi PIN belum cocok.'); return; }
    setBusy(true);
    const result = await registerTenant(phone, business.trim(), owner.trim(), pin, '', businessType, referral || undefined, googleProof || undefined, otpProof || undefined);
    if (result.success) { router.push('/onboarding'); router.refresh(); }
    else setError(result.message || 'Usaha belum tersimpan. Coba lagi.');
    setBusy(false);
  }
  function back() {
    setError(''); setNotFound(false);
    if (step === 'otp') { setStep('phone'); setOtp(''); }
    else if (step === 'business') { setStep('phone'); setGoogleProof(''); setOtpProof(''); }
    else { setStep('choice'); setIdToken(''); setEmail(''); }
  }
  const titles: Record<Step, string> = {
    choice: mode === 'register' ? 'Mulai usaha Anda di Selaris.' : 'Selamat datang kembali.',
    phone: idToken ? 'Hubungkan nomor Anda.' : 'Masuk dengan kode.',
    otp: channel === 'sefrekuensi' ? 'Periksa Sefrekuensi.' : 'Periksa WhatsApp.',
    business: 'Kenalkan usaha Anda.',
  };
  return <AuthShell>
    {step !== 'choice' && <button className="auth-back" type="button" onClick={back} disabled={busy}><ArrowLeft size={18} /> Kembali</button>}
    <div className="auth-heading">
      <p className="auth-kicker">{step === 'choice' ? 'Selaris bersama Sefrekuensi' : step === 'business' ? 'Langkah terakhir' : 'Akun Anda'}</p>
      <h1>{titles[step]}</h1>
      <p>{step === 'choice' ? 'Satu tempat untuk mengelola penjualan dan usaha Anda.' : step === 'phone' ? idToken ? `${email}. Verifikasi nomor sekali untuk menghubungkan akun dan usaha Anda.` : 'Gunakan nomor yang terdaftar di Sefrekuensi.' : step === 'otp' ? `Masukkan kode 6 digit untuk +${phone}${channel === 'sefrekuensi' ? ', dari pesan Yasmin.' : '.'}` : 'Isi informasi dasar. Menu, printer, dan pembayaran bisa diatur setelahnya.'}</p>
    </div>
    {error && <div className="auth-error" role="alert">{error}</div>}
    {step === 'choice' && <div className="auth-actions">
      <GoogleButton onClick={google} disabled={checking || !config} busy={busy} />
      {checking ? <p className="auth-note" role="status">Menyiapkan pilihan login…</p> : !config && <p className="auth-note">Login Google sedang disiapkan. Kode Sefrekuensi tersedia di bawah.</p>}
      <div className="auth-divider"><span>atau</span></div>
      <button className="ks-btn ks-btn-outline" type="button" onClick={() => { setError(''); setStep('phone'); }} disabled={busy}>Gunakan kode Sefrekuensi</button>
      <p className="auth-note">Kode datang sebagai pesan di aplikasi Sefrekuensi.</p>
      <p className="auth-switch">{mode === 'login' ? 'Belum punya usaha di Selaris?' : 'Sudah punya akun?'} <Link href={mode === 'login' ? '/register' : '/login'}>{mode === 'login' ? 'Daftarkan usaha' : 'Masuk'}</Link></p>
    </div>}
    {step === 'phone' && <form className="auth-form" onSubmit={event => { event.preventDefault(); void send('sefrekuensi'); }}>
      <label htmlFor="auth-phone">Nomor HP<input id="auth-phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="081234567890" value={phone} onChange={event => setPhone(event.target.value)} required autoFocus /></label>
      <button className="ks-btn" disabled={busy || !phone}>{busy ? <><Loader2 size={18} className="animate-spin" /> Mengirim kode…</> : 'Kirim kode ke Sefrekuensi'}</button>
      {notFound && <a className="ks-btn ks-btn-outline" href={SEFREKUENSI_PLAY_URL} target="_blank" rel="noopener noreferrer">Pasang Sefrekuensi</a>}
      <button className="auth-text-button" type="button" onClick={() => send('whatsapp')} disabled={busy || !phone}>Gunakan WhatsApp sebagai alternatif</button>
    </form>}
    {step === 'otp' && <form className="auth-form" onSubmit={verify}>
      <label htmlFor="auth-otp">Kode verifikasi<input id="auth-otp" className="auth-otp" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={event => setOtp(event.target.value.replace(/\D/g, ''))} autoFocus required /></label>
      <button className="ks-btn" disabled={busy || otp.length !== 6}>{busy ? 'Memeriksa kode…' : 'Verifikasi dan lanjut'}</button>
      <button className="auth-text-button" type="button" disabled={busy || countdown > 0} onClick={() => send(channel)}>{countdown > 0 ? `Kirim ulang dalam ${countdown} detik` : 'Kirim ulang kode'}</button>
    </form>}
    {step === 'business' && <form className="auth-form" onSubmit={finish}>
      <label htmlFor="owner-name">Nama pemilik<input id="owner-name" autoComplete="name" value={owner} onChange={event => setOwner(event.target.value)} minLength={2} required /></label>
      <label htmlFor="business-name">Nama usaha<input id="business-name" autoFocus value={business} onChange={event => setBusiness(event.target.value)} minLength={2} maxLength={100} required placeholder="Nama yang dikenal pelanggan" /></label>
      <fieldset className="auth-businesses"><legend>Jenis usaha</legend>{businesses.map(option => <label key={option.value}><input type="radio" name="business-type" value={option.value} checked={businessType === option.value} onChange={() => setBusinessType(option.value)} /><span>{option.label}</span></label>)}</fieldset>
      <div className="auth-pair"><label htmlFor="pin">PIN kasir<input id="pin" type="password" inputMode="numeric" autoComplete="new-password" pattern="[0-9]{6}" maxLength={6} value={pin} onChange={event => setPin(event.target.value.replace(/\D/g, ''))} required /></label><label htmlFor="pin-confirm">Ulangi PIN<input id="pin-confirm" type="password" inputMode="numeric" autoComplete="new-password" pattern="[0-9]{6}" maxLength={6} value={confirmPin} onChange={event => setConfirmPin(event.target.value.replace(/\D/g, ''))} required /></label></div>
      <p className="auth-note">PIN 6 digit untuk akses kasir pada perangkat Anda.</p>
      <details><summary>Punya kode referral?</summary><label htmlFor="referral">Kode referral<input id="referral" value={referral} onChange={event => setReferral(event.target.value.toUpperCase())} /></label></details>
      <button className="ks-btn" disabled={busy || pin.length !== 6 || confirmPin.length !== 6}>{busy ? 'Menyiapkan usaha…' : 'Buat usaha saya'}</button>
    </form>}
  </AuthShell>;
}
