'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { claimPassword, getAccountAccess, getAccountInfo, getAccountSessions, revokeAccountSessions } from '@/app/actions/accounts';
import { PasswordInput } from './password-input';

export function AccountSettings({ onSaved }: { onSaved?: () => void } = {}) {
  const router = useRouter();
  const [info, setInfo] = useState<any>(null), [owner, setOwner] = useState(false), [sessions, setSessions] = useState<any[]>([]);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [recovery, setRecovery] = useState('');
  const pending = useRef<{ value: string; id: string } | null>(null);
  async function load() {
    setError('');
    const [account, access, devices] = await Promise.all([getAccountInfo(), getAccountAccess(), getAccountSessions()]);
    if (!account.success) { setError(account.message); return; }
    setInfo(account.data); setOwner(access.success && access.data.enforcement_mode === 'owner');
    if (devices.success) setSessions(devices.data); else setError(devices.message);
  }
  useEffect(() => { void load(); }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    if (values.password !== values.confirm) { setError('Konfirmasi password belum cocok.'); return; }
    const body = { shop_username: String(values.shop_username || '').trim(), username: info.username || 'owner', password: values.password, ...(info.password_enabled ? { current_password: values.current_password } : {}) };
    const value = JSON.stringify(body);
    if (pending.current?.value !== value) pending.current = { value, id: crypto.randomUUID() };
    setBusy(true); setError('');
    try {
      const result = await claimPassword({ ...body, client_request_id: pending.current.id });
      if (!result.success) { setError(result.message); return; }
      pending.current = null; setRecovery(result.data.recovery_code || ''); await load(); onSaved?.();
    } finally { setBusy(false); }
  }
  return <section className="f-panel"><h2>Akun dan perangkat</h2>
    {error && <p className="f-notice f-error" role="alert">{error}</p>}
    {!info ? <><p role="status">Memuat akun…</p>{error && <button className="f-button" onClick={load}>Coba lagi</button>}</> : <>
      <p>Username toko: {info.shop_username || 'Belum ditetapkan'} · Username akun: {info.username || 'Belum ditetapkan'}</p>
      {recovery ? <div className="finance-form"><label htmlFor="account-recovery">Kode pemulihan baru</label><textarea id="account-recovery" readOnly value={recovery} rows={3} /><p>Simpan kode di tempat pribadi. Password lama dan sesi perangkat lain sudah berakhir.</p><button className="f-button" onClick={() => setRecovery('')}>Saya sudah menyimpan kode</button></div>
      : owner && <form className="finance-form" onSubmit={submit} aria-busy={busy}>
        <p>{info.password_enabled ? 'Ganti password akun pemilik. Perangkat lain akan diminta masuk kembali.' : 'Migrasikan akun lama dengan username toko dan password. Usaha dan riwayat tetap memakai akun yang sama. Masuk ulang melalui akun lama jika sesi sudah lebih dari 15 menit.'}</p>
        <label>Username toko<input name="shop_username" defaultValue={info.shop_username || ''} readOnly={Boolean(info.shop_username)} autoCapitalize="none" autoCorrect="off" spellCheck={false} pattern="[A-Za-z0-9](?:[A-Za-z0-9_]|-){2,63}" title="Gunakan 3 sampai 64 huruf atau angka, tanda hubung (-) atau garis bawah (_), tanpa spasi. Awali dengan huruf atau angka." aria-describedby={info.shop_username ? undefined : 'account-shop-rule'} minLength={3} maxLength={64} required /></label>
        {!info.shop_username && <p id="account-shop-rule">Username untuk masuk, tanpa spasi. Contoh: kasira_coffee. Nama usaha Anda tetap sama.</p>}
        {info.password_enabled && <PasswordInput label="Password saat ini" name="current_password" autoComplete="current-password" required />}
        <PasswordInput label="Password baru" name="password" autoComplete="new-password" minLength={8} maxLength={128} required />
        <PasswordInput label="Ulangi password" name="confirm" autoComplete="new-password" minLength={8} maxLength={128} required />
        <button className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan…' : info.password_enabled ? 'Ganti password' : 'Tetapkan username dan password'}</button>
      </form>}
      <h3>Perangkat yang masih masuk</h3><ul>{sessions.map(row => <li key={row.id}>{row.current ? 'Perangkat ini' : 'Perangkat lain'} · Masuk {new Date(row.created_at).toLocaleString('id-ID')}</li>)}</ul>
      {!sessions.length && <p>Sesi akun lama belum tercatat sebagai sesi perangkat. Masuk ulang untuk memperbaruinya.</p>}
      <button className="f-button" disabled={busy} onClick={async () => { setBusy(true); const result = await revokeAccountSessions({ client_request_id: crypto.randomUUID() }); if (result.success) { router.push('/login'); router.refresh(); } else { setError(result.message); setBusy(false); } }}>Keluar semua perangkat</button>
    </>}
  </section>;
}
