'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { cancelAccountDeletion, getAccountDeletion, requestAccountDeletion } from '@/app/actions/accounts';

// Aturan pemilik vs karyawan dan masa tenggang ada di backend
// (services/account_deletion.py); layar ini hanya menampilkan status.
const tanggal = (iso: string) => new Date(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' });

export function AccountDeletion() {
  const router = useRouter();
  const [status, setStatus] = useState<any>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false), [word, setWord] = useState('');
  async function load() {
    const result = await getAccountDeletion();
    if (result.success) setStatus(result.data); else setError(result.message);
  }
  useEffect(() => { void load(); }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError('');
    try {
      const result = await requestAccountDeletion(word);
      if (!result.success) { setError(result.message); return; }
      if (result.data.deleted) { router.replace('/login'); return; }
      setOpen(false); setWord(''); await load();
    } finally { setBusy(false); }
  }
  async function cancel() {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const result = await cancelAccountDeletion();
      if (!result.success) { setError(result.message); return; }
      await load();
    } finally { setBusy(false); }
  }
  if (!status) return error ? <section className="f-panel"><h2>Hapus akun</h2><p className="f-notice f-error" role="alert">{error}</p></section> : null;
  const business = status.scope === 'business';
  return <section className="f-panel" aria-labelledby="hapus-akun-judul"><h2 id="hapus-akun-judul">Hapus akun</h2>
    {error && <p className="f-notice f-error" role="alert">{error}</p>}
    {status.scheduled_at ? <>
      <p className="f-notice" role="status">Usaha {status.business_name} dijadwalkan dihapus pada <strong>{tanggal(status.scheduled_at)}</strong>. Sampai tanggal itu Selaris tetap berjalan normal.</p>
      {status.can_cancel && <button className="f-button" onClick={cancel} disabled={busy}>Batalkan penghapusan</button>}
    </> : <>
      <p>{business
        ? `Menghapus akun pemilik akan menghapus seluruh data usaha ${status.business_name}: outlet, menu, stok, transaksi, pelanggan, karyawan, dan akun kasir. Penghapusan dijalankan ${status.grace_days} hari setelah permintaan dan dapat dibatalkan selama masa itu.`
        : 'Akun login Anda akan dihapus sekarang dan Anda keluar dari semua perangkat. Transaksi yang pernah Anda catat tetap tersimpan di usaha tempat Anda bekerja.'}</p>
      {!open ? <button className="f-button f-delete" onClick={() => setOpen(true)}>Hapus akun</button>
      : <form className="finance-form" onSubmit={submit} aria-busy={busy}>
        <label htmlFor="hapus-akun-konfirmasi">Ketik {status.confirm_word} untuk mengonfirmasi</label>
        <input id="hapus-akun-konfirmasi" value={word} onChange={(e) => setWord(e.target.value)} autoComplete="off" autoCapitalize="characters" />
        <div className="f-form-actions">
          <button type="submit" className="f-button f-delete" disabled={busy || word.trim().toUpperCase() !== status.confirm_word}>{business ? 'Jadwalkan penghapusan' : 'Hapus akun saya'}</button>
          <button type="button" className="f-button" onClick={() => { setOpen(false); setWord(''); }} disabled={busy}>Batal</button>
        </div>
      </form>}
    </>}
  </section>;
}
