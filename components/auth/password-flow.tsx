'use client';

import { POS_WORKSPACE_PERMISSIONS } from '@/lib/pos-access';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { consumeAccountCode, loginPassword, registerPassword } from '@/app/actions/accounts';
import { AuthShell } from './auth-shell';
import { PasswordInput } from './password-input';

export function PasswordFlow({ mode }: { mode: 'login' | 'register' | 'activation' | 'recovery' }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [staff, setStaff] = useState(false), [saved, setSaved] = useState(false);
  const [recovery, setRecovery] = useState(''), [target, setTarget] = useState('/dashboard');
  const request = useRef<{ value: string; id: string } | null>(null);
  const isCode = mode === 'activation' || mode === 'recovery';
  const title = { login: 'Masuk ke usaha Anda.', register: 'Daftarkan usaha Anda.', activation: 'Aktifkan akun karyawan.', recovery: 'Pulihkan password Anda.' }[mode];
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    setError('');
    if (mode !== 'login' && values.password !== values.confirm) { setError('Konfirmasi password belum cocok.'); return; }
    const body: Record<string, unknown> = { shop_username: values.shop_username, username: values.username || 'owner', password: values.password };
    if (mode === 'register') Object.assign(body, { business_name: values.business_name, owner_name: values.owner_name, business_type: values.business_type });
    if (isCode) Object.assign(body, { code: String(values.code || '').trim(), purpose: mode });
    const value = JSON.stringify(body);
    if (request.current?.value !== value) request.current = { value, id: crypto.randomUUID() };
    if (mode !== 'login') body.client_request_id = request.current.id;
    setBusy(true);
    try {
      const result = mode === 'login' ? await loginPassword(body) : mode === 'register' ? await registerPassword(body) : await consumeAccountCode(body);
      if (!result.success) { setError(result.message); return; }
      request.current = null;
      const requested = new URLSearchParams(window.location.search).get('redirect');
      const destination = result.data.access?.enforcement_mode === 'managed' ? result.data.access?.permissions?.some((p: string) => POS_WORKSPACE_PERMISSIONS.includes(p)) ? '/dashboard/operasional' : '/dashboard/hris' : mode === 'register' ? '/onboarding' : requested && /^\/dashboard(?:\/|$)/.test(requested) ? requested : '/dashboard';
      if (result.data.recovery_code) { setRecovery(result.data.recovery_code); setTarget(destination); }
      else { router.push(destination); router.refresh(); }
    } finally { setBusy(false); }
  }
  return <AuthShell>
    <div className="auth-heading"><p className="auth-kicker">Selaris</p><h1>{recovery ? 'Simpan kode pemulihan.' : title}</h1><p>{recovery ? 'Kode ini dipakai sekali untuk mengganti password saat Anda kehilangan akses. Simpan di tempat pribadi. Setelah dipakai, Anda mendapat kode pengganti.' : mode === 'register' ? 'Gunakan username toko dan password yang sama di web dan aplikasi kasir.' : isCode ? 'Masukkan identitas akun, kode Anda, lalu buat password baru.' : 'Pemilik memakai username toko. Karyawan memakai akun pribadi dari pemilik.'}</p></div>
    {error && <p className="auth-error" role="alert">{error}</p>}
    {recovery ? <div className="auth-form"><label htmlFor="owner-recovery">Kode pemulihan</label><textarea id="owner-recovery" readOnly value={recovery} rows={3} /><label className="account-check"><input type="checkbox" checked={saved} onChange={e => setSaved(e.target.checked)} />Saya sudah menyimpan kode ini</label><button className="ks-btn ks-btn-lg" disabled={!saved} onClick={() => { setRecovery(''); router.push(target); router.refresh(); }}>Lanjut ke usaha</button></div>
    : <form className="auth-form" onSubmit={submit} aria-busy={busy}>
      <label>Username toko<input name="shop_username" autoComplete="organization" autoCapitalize="none" spellCheck={false} pattern="[A-Za-z0-9](?:[A-Za-z0-9_]|-){2,63}" minLength={3} maxLength={64} required /></label>
      {mode === 'login' && <label className="account-check"><input type="checkbox" checked={staff} onChange={e => setStaff(e.target.checked)} />Saya masuk sebagai karyawan</label>}
      {(staff || isCode) && <label>{staff && !isCode ? 'Username akun atau nomor HP' : 'Username akun'}<input aria-label="Username akun" name="username" defaultValue={isCode ? 'owner' : ''} autoComplete="username" autoCapitalize="none" spellCheck={false} minLength={3} maxLength={64} required /></label>}
      {isCode && <label>{mode === 'activation' ? 'Kode aktivasi dari pemilik' : 'Kode pemulihan'}<textarea name="code" autoComplete="off" required minLength={32} maxLength={128} rows={3} /></label>}
      {mode === 'register' && <><label>Nama pemilik<input name="owner_name" autoComplete="name" minLength={2} maxLength={120} required /></label><label>Nama usaha<input name="business_name" minLength={2} maxLength={100} required /></label><label>Jenis usaha<select name="business_type"><option value="cafe">Kafe</option><option value="warung">Warung</option><option value="resto">Restoran</option><option value="other">Usaha lain</option></select></label></>}
      <PasswordInput label={mode === 'login' ? 'Password' : 'Password baru'} name="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'login' ? 1 : 8} maxLength={128} required />
      {mode !== 'login' && <><p className="auth-note">Minimal 8 karakter. Password boleh berupa rangkaian kata.</p><PasswordInput label="Ulangi password" name="confirm" autoComplete="new-password" minLength={8} maxLength={128} required /></>}
      <button className="ks-btn ks-btn-lg" disabled={busy}>{busy ? 'Memproses…' : mode === 'login' ? 'Masuk ke usaha' : mode === 'register' ? 'Buat usaha' : 'Simpan password'}</button>
      {mode === 'login' && <><Link className="auth-text-button" href="/recover">Lupa password</Link><Link className="auth-text-button" href="/activate">Aktivasi akun karyawan</Link><Link className="auth-text-button" href="/login/legacy">Masuk akun lama dengan kode atau Google</Link></>}
      <p className="auth-switch">{mode === 'register' ? 'Sudah punya akun?' : 'Belum punya usaha?'} <Link href={mode === 'register' ? '/login' : '/register'}>{mode === 'register' ? 'Masuk' : 'Daftarkan usaha'}</Link></p>
      {isCode && <Link className="auth-text-button" href="/login">Kembali ke halaman masuk</Link>}
    </form>}
  </AuthShell>;
}
