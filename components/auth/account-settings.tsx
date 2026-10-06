'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { claimPassword, getAccountAccess, getAccountInfo, getAccountSessions, revokeAccountSessions } from '@/app/actions/accounts';

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
    const body = { shop_username: values.shop_username, username: info.username || 'owner', password: values.password, ...(info.password_enabled ? { current_password: values.current_password } : {}) };
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
        <label>Username toko<input name="shop_username" defaultValue={info.shop_username || ''} readOnly={Boolean(info.shop_username)} autoCapitalize="none" minLength={3} maxLength={64} required /></label>
        {info.password_enabled && <label>Password saat ini<input name="current_password" type="password" autoComplete="current-password" required /></label>}
        <label>Password baru<input name="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required /></label><label>Ulangi password<input name="confirm" type="password" autoComplete="new-password" minLength={8} maxLength={128} required /></label>
        <button className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan…' : info.password_enabled ? 'Ganti password' : 'Tetapkan username dan password'}</button>
      </form>}
      <h3>Perangkat yang masih masuk</h3><ul>{sessions.map(row => <li key={row.id}>{row.current ? 'Perangkat ini' : 'Perangkat lain'} · Masuk {new Date(row.created_at).toLocaleString('id-ID')}</li>)}</ul>
      {!sessions.length && <p>Sesi akun lama belum tercatat sebagai sesi perangkat. Masuk ulang untuk memperbaruinya.</p>}
      <button className="f-button" disabled={busy} onClick={async () => { setBusy(true); const result = await revokeAccountSessions({ client_request_id: crypto.randomUUID() }); if (result.success) { router.push('/login'); router.refresh(); } else { setError(result.message); setBusy(false); } }}>Keluar semua perangkat</button>
    </>}
  </section>;
}
