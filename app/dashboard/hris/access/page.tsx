'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { getAccountSetup, issueStaffActivation, saveAccessRole, saveStaffAccount, type AccountResult } from '@/app/actions/accounts';
import { AccountSettings } from '@/components/auth/account-settings';
import '../../keuangan/finance.css';
import '../hris.css';

const labels: Record<string, string> = {
  'hris.self': 'Lihat jadwal dan catat kehadiran sendiri', 'hris.employees.manage': 'Kelola profil karyawan',
  'hris.schedules.manage': 'Kelola jadwal kerja', 'hris.attendance.manage': 'Kelola dan koreksi absensi',
  'pos.sell': 'Buat pesanan dan terima pembayaran', 'pos.refund': 'Ajukan refund',
  'pos.refund.approve': 'Setujui atau tolak refund', 'pos.discount.override': 'Ubah harga transaksi dan diskon di atas 20%',
  'pos.shift.manage': 'Buka, jeda dan hitung sesi kas', 'pos.cash.manage': 'Catat kas masuk dan keluar',
  'pos.kitchen': 'Lihat pesanan dan ubah status dapur', 'sales.detail.view': 'Lihat riwayat seluruh kasir dan rincian penjualan',
  'stock.view': 'Lihat stok', 'stock.receive': 'Terima barang dan tambah stok', 'stock.adjust': 'Catat hasil stok opname',
  'customers.lookup': 'Cari pelanggan untuk transaksi (nama dan nomor tersamar)',
  'finance.view': 'Lihat laporan keuangan outlet, termasuk ringkasan HPP dan laba',
  'finance.manage': 'Catat, ubah dan hapus pengeluaran',
  'purchasing.view': 'Lihat nota dan supplier', 'purchasing.manage': 'Kelola supplier, catat nota dan pembayaran',
  'supplier.price.view': 'Lihat harga pembelian dan nominal nota supplier',
  'customers.view': 'Lihat profil bersama bisnis dan riwayat belanja outlet yang diizinkan',
  'customers.manage': 'Kelola profil dan catatan pelanggan bersama bisnis', 'customers.export': 'Ekspor halaman pelanggan ke CSV',
  'hpp.view': 'Lihat resep dan harga modal katalog bersama brand',
  'hpp.manage': 'Kelola bahan dan resep', 'hpp.approve': 'Setujui penyimpanan langsung bahan dan resep',
  'ai.chat': 'Gunakan AI sesuai izin data akun',
};

export default function TeamAccess() {
  const [setup, setSetup] = useState<any>(null), [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false);
  const [roleId, setRoleId] = useState(''), [employeeId, setEmployeeId] = useState(''), [code, setCode] = useState<any>(null);
  const pending = useRef<{ value: string; id: string } | null>(null), roleUuid = useRef('');
  async function load() { const result = await getAccountSetup(); if (result.success) setSetup(result.data); else setError(result.message); }
  useEffect(() => { void load(); }, []);
  const role = setup?.roles.find((r: any) => r.id === roleId);
  const employee = setup?.employees.find((r: any) => r.id === employeeId);
  const account = setup?.accounts.find((r: any) => r.id === employee?.user_id);
  async function write(value: unknown, perform: (id: string) => Promise<AccountResult>) {
    if (busy) return; const serialized = JSON.stringify(value);
    if (pending.current?.value !== serialized) pending.current = { value: serialized, id: crypto.randomUUID() };
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await perform(pending.current.id);
      if (!result.success) { setError(result.message); return; }
      pending.current = null; setNotice('Perubahan tersimpan'); await load(); return result.data;
    } finally { setBusy(false); }
  }
  async function roleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    if (!roleUuid.current) roleUuid.current = crypto.randomUUID();
    const body = { id: roleId || roleUuid.current, name: form.get('name'), row_version: role?.row_version || 0,
      scope: form.get('scope'), outlet_ids: form.get('scope') === 'tenant' ? [] : form.getAll('outlet_ids'),
      permissions: Object.fromEntries(Object.keys(labels).map(p => [p, form.getAll('permissions').includes(p)])) };
    const result = await write(body, client_request_id => saveAccessRole({ ...body, client_request_id }));
    if (result) { setRoleId(result.id); roleUuid.current = ''; }
  }
  async function accountSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const body = { row_version: employee.row_version, user_row_version: account?.row_version || null,
      username: form.get('username'), role_id: form.get('role_id') || null, is_active: form.get('is_active') === 'on' };
    await write({ employeeId, ...body }, client_request_id => saveStaffAccount(employeeId, { ...body, client_request_id }));
  }
  return <div className="finance-workspace"><div className="finance-heading"><div><h1>Akun dan akses tim</h1><p>Atur akun individual dan jabatan melalui profil karyawan.</p></div><Link className="f-button" href="/dashboard/hris">Kembali ke tim</Link></div>
    {error && <div className="f-notice f-error" role="alert"><p>{error}</p><button className="f-button" disabled={busy} onClick={() => { setError(''); void load(); }}>Muat ulang</button></div>}{notice && <p className="f-notice" role="status">{notice}</p>}
    {!setup ? <p role="status">{error ? 'Akses belum dapat dimuat.' : 'Memuat akun tim…'}</p> : <>
      <AccountSettings onSaved={() => { void load(); }} />
      <section className="f-panel"><h2>Jabatan dengan pengaturan izin</h2><p>Pilih hak lihat dan tindakan secara terpisah. Akun staf memakai POS saat online. Pelanggan dan supplier dipakai bersama bisnis; laporan mengikuti outlet. Bahan dan resep dipakai bersama brand. Menyimpan bahan/resep langsung membutuhkan hak kelola dan persetujuan; mencatat nota barang membutuhkan hak penerimaan stok. Percakapan AI belum tersedia. Antrean lama tetap disimpan.</p>
        <label className="finance-form">Pilih jabatan<select value={roleId} onChange={e => { setRoleId(e.target.value); roleUuid.current = ''; }}><option value="">Buat jabatan baru</option>{setup.roles.filter((r: any) => r.editable).map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
        <form key={roleId} className="finance-form" onSubmit={roleSubmit} aria-busy={busy}><label>Nama jabatan<input name="name" defaultValue={role?.name || ''} required minLength={2} maxLength={100} /></label>
          <label>Cakupan akses<select name="scope" defaultValue={role?.scope || 'outlet'}><option value="outlet">Outlet yang dipilih</option><option value="tenant">Seluruh bisnis, termasuk outlet baru</option></select></label>
          <p>Cakupan seluruh bisnis juga mencakup biaya tanpa outlet dan perubahan akun kas bersama. Untuk cakupan outlet, pilih minimal satu outlet di bawah.</p>
          <fieldset><legend>Outlet yang diizinkan</legend>{setup.outlets.map((o: any) => <label className="account-option" key={o.id}><input type="checkbox" name="outlet_ids" value={o.id} defaultChecked={role?.policy.outlet_ids.includes(o.id)} />{o.name}</label>)}</fieldset>
          <fieldset><legend>Hak lihat dan tindakan</legend>{Object.entries(labels).map(([p, text]) => <label className="account-option" key={p}><input type="checkbox" name="permissions" value={p} defaultChecked={role ? role.policy.permissions[p] === true : p === 'hris.self'} />{text}</label>)}</fieldset>
          <button className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan…' : 'Simpan jabatan'}</button>
        </form></section>
      <section className="f-panel"><h2>Akun karyawan</h2><label className="finance-form">Pilih karyawan<select value={employeeId} onChange={e => { setEmployeeId(e.target.value); setCode(null); }}><option value="">Pilih profil</option>{setup.employees.map((e: any) => <option key={e.id} value={e.id}>{e.name}{e.is_active ? '' : ' (nonaktif)'}</option>)}</select></label>
        {!setup.employees.length && <p>Tambahkan profil karyawan di halaman Tim terlebih dahulu.</p>}
        {employee && (account?.is_owner ? <p>Akun pemilik tidak diubah melalui profil karyawan.</p> : <form key={`${employeeId}:${account?.row_version}`} className="finance-form" onSubmit={accountSubmit} aria-busy={busy}>
          <p>Perubahan akun membatalkan sesi perangkat karyawan. Pengaktifan akun tetap memerlukan profil karyawan aktif.</p>
          <label>Username karyawan<input name="username" defaultValue={account?.username || ''} autoCapitalize="none" minLength={3} maxLength={64} required /></label>
          <label>Jabatan akses<select name="role_id" defaultValue={setup.roles.some((r: any) => r.editable && r.id === account?.role_id) ? account.role_id : ''} required={!account}><option value="">{account ? 'Pertahankan akses lama' : 'Pilih jabatan'}</option>{setup.roles.filter((r: any) => r.editable).map((r: any) => <option value={r.id} key={r.id}>{r.name}</option>)}</select></label>
          <label className="account-option"><input type="checkbox" name="is_active" defaultChecked={account ? account.is_active : employee.is_active} />Akun boleh masuk</label>
          <button className="f-button f-primary" disabled={busy || !setup.shop_username}>{busy ? 'Menyimpan…' : account ? 'Simpan akun karyawan' : 'Buat akun karyawan'}</button>
        </form>)}
        {account && !account.is_owner && <button className="f-button" disabled={busy || !account.is_active || !employee?.is_active || !account.username} onClick={async () => {
          const result = await write({ employeeId, action: 'activation' }, client_request_id => issueStaffActivation(employeeId, { client_request_id })); if (result) setCode(result);
        }}>Buat kode aktivasi atau reset password</button>}
        {code && <div className="finance-form"><p>Bagikan kode secara pribadi kepada karyawan. Password lama dan sesi terdahulu telah dibatalkan. Kode berlaku sampai {new Date(code.expires_at).toLocaleString('id-ID')}.</p><p>Username toko: {code.shop_username} · Username akun: {code.username}</p><label htmlFor="staff-activation">Kode aktivasi</label><textarea id="staff-activation" readOnly value={code.code} rows={3} /><Link className="f-button" href="/activate">Buka halaman aktivasi</Link><button className="f-button" onClick={() => setCode(null)}>Tutup kode</button></div>}
      </section>
    </>}
  </div>;
}
