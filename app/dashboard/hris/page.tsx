'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { InventoryDialog } from '@/components/inventory-dialog';
import { checkHrRequest, getHrEmployeeChoices, getHrSetup, getHrWorkspace, writeHr } from '@/app/actions/hris';
import { PasswordInput } from '@/components/auth/password-input';
import { addDays, hrDay, hrTime, localTime, outletDate, zonedIso, zoneLabel } from '@/lib/hris';
import type { HrEmployee, HrFilters, HrKind, HrPending, HrRecord, HrSetup, HrWorkspace } from '@/lib/hris';
import '../keuangan/finance.css';
import './hris.css';

const labels: Record<HrKind, string> = { employees: 'Karyawan', schedules: 'Jadwal', attendance: 'Absensi & izin' };
const actions: Record<HrKind, string> = { employees: 'Tambah karyawan', schedules: 'Atur jadwal', attendance: 'Catat kehadiran' };
type Dialog = { kind: HrKind; row?: HrEmployee | HrRecord } | { kind: 'void'; collection: 'schedules' | 'attendance'; row: HrRecord } | { kind: 'punch'; action: 'in' | 'out' };
const initial: HrFilters = { outlet_id: '', start: '', end: '', kind: 'employees', search: '', active: '', skip: 0 };

export default function HrisPage() {
  const [setup, setSetup] = useState<HrSetup | null>(null), [filters, setFilters] = useState(initial);
  const [data, setData] = useState<HrWorkspace | null>(null), [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [dialog, setDialog] = useState<Dialog | null>(null), [pending, setPending] = useState<HrPending | null>(null), [busy, setBusy] = useState(false), [saveError, setSaveError] = useState('');
  const key = useRef<string | null>(null), writing = useRef(false);
  const [retryPassword, setRetryPassword] = useState(''), [needsPassword, setNeedsPassword] = useState(false);
  useEffect(() => {
    let current = true; setLoading(true); setError(''); setSetup(null); setData(null);
    getHrSetup().then(result => { if (!current) return;
      if (!result.success) { setError(result.message); setLoading(false); return; }
      const value = result.data, storage = `selaris-hris-pending:${value.workspace_key}`;
      if (key.current !== storage) { key.current = storage; setPending(null); setDialog(null); setRetryPassword(''); setNeedsPassword(false);
        try { const raw = sessionStorage.getItem(storage); if (raw) { const p = JSON.parse(raw); if (p.payload?.client_request_id && p.path && p.method) setPending(p); } } catch { /* Keep requests in memory when browser storage is unavailable. */ }
      }
      setSetup(value);
      if (!value.outlets.length) setLoading(false);
      setFilters(old => { const outlet = value.outlets.find(o => o.id === old.outlet_id) || value.outlets.find(o => o.id === value.open_attendance?.outlet_id) || value.outlets.find(o => o.id === value.self_employee?.outlet_id) || value.outlets[0];
        if (!outlet) return old;
        const today = outletDate(new Date(), outlet.timezone);
        return { ...old, outlet_id: outlet.id, start: old.start || today, end: old.end || addDays(today, 6) }; });
    }).catch(() => { if (current) { setError('Data tim belum bisa dimuat. Periksa koneksi lalu coba lagi.'); setLoading(false); } }); return () => { current = false; };
  }, [revision]);
  useEffect(() => {
    if (!setup || !filters.outlet_id || !setup.outlets.some(o => o.id === filters.outlet_id)) return;
    let current = true; setLoading(true); setError(''); setData(null);
    getHrWorkspace(filters).then(result => { if (!current) return; if (result.success) setData(result.data); else setError(result.message); setLoading(false); }).catch(() => { if (current) { setError('Data tim belum bisa dimuat. Periksa koneksi lalu coba lagi.'); setLoading(false); } });
    return () => { current = false; };
  }, [setup, filters]);
  const persist = (value: HrPending | null) => {
    setPending(value);
    if (!value) { setRetryPassword(''); setNeedsPassword(false); }
    try { if (key.current) {
      if (value) {
        const account = value.payload.account as Record<string, unknown> | undefined;
        const stored = account ? { ...value, password_required: value.password_required || Boolean(account.password), payload: { ...value.payload, account: { ...account, password: undefined } } } : value;
        sessionStorage.setItem(key.current, JSON.stringify(stored));
      } else sessionStorage.removeItem(key.current);
    } } catch { /* The current page still retains the request. */ }
  };
  const retry = async (request: HrPending) => {
    if (busy || writing.current) return false;
    const account = request.payload.account as Record<string, unknown> | undefined;
    if (account) {
      setBusy(true); setSaveError('');
      try {
        const receipt = await checkHrRequest(request);
        if (!receipt.success) { setSaveError(receipt.message); return false; }
        if (receipt.data.state === 'saved') { persist(null); setNotice('Profil dan akun karyawan sudah tersimpan'); setRevision(v => v + 1); return true; }
        if (request.password_required && !account.password) {
          setNeedsPassword(true);
          if (retryPassword.length < 8) { setDialog(null); setSaveError('Belum tersimpan. Masukkan kembali password awal untuk melanjutkan permintaan yang sama.'); return false; }
          request = { ...request, payload: { ...request.payload, account: { ...account, password: retryPassword } } };
        }
      } finally { setBusy(false); }
    }
    return submit(request);
  };
  const submit = async (request: HrPending) => {
    if (writing.current || !setup) return false;
    writing.current = true;
    request = { ...request, workspace_key: request.workspace_key || setup.workspace_key };
    setBusy(true); setSaveError(''); persist(request);
    try {
      const result = await writeHr(request);
      if (result.success) { persist(null); setNotice(result.message || 'Data tim disimpan'); setRevision(v => v + 1); return true; }
      setSaveError(result.message); if (!result.uncertain) persist(null); return false;
    } catch { setSaveError('Koneksi terputus. Hasil penyimpanan belum pasti; periksa permintaan yang sama.'); return false; }
    finally { writing.current = false; setBusy(false); }
  };
  const change = <K extends keyof HrFilters>(field: K, value: HrFilters[K]) => setFilters(v => ({ ...v, [field]: value, skip: 0 }));
  const open = (value: Dialog) => { setSaveError(''); setDialog(value); };
  const selected = setup?.outlets.find(o => o.id === filters.outlet_id), zone = selected?.timezone || 'Asia/Jakarta';
  const mutationDisabled = busy || Boolean(pending) || !setup;
  const manager = setup?.permissions ? setup.permissions.includes(`hris.${filters.kind}.manage`) : Boolean(setup?.is_manager);
  return <div className="finance-workspace hris-workspace">
    <div className="finance-heading"><div><h1>Tim & absensi</h1><p className="f-explanation">Profil karyawan, jadwal kerja, dan catatan kehadiran.</p></div>
      {manager && <button className="f-button f-primary" disabled={mutationDisabled || !selected} onClick={() => open({ kind: filters.kind })}>{actions[filters.kind]}</button>}</div>
    <p className="f-footnote">Satu jadwal dan satu catatan kehadiran per karyawan per tanggal kerja. Jam mengikuti zona waktu outlet.</p>
    {setup?.permissions?.includes('access.manage') && <Link className="f-button" href="/dashboard/hris/access">Atur akun dan akses tim</Link>}
    {pending && <div className="f-notice"><p role="status">Penyimpanan belum selesai: {pending.title}. Periksa permintaan yang sama sebelum mencatat lagi.</p>{needsPassword && <PasswordInput label="Password awal untuk melanjutkan" minLength={8} maxLength={128} autoComplete="new-password" value={retryPassword} disabled={busy} onChange={e => setRetryPassword(e.target.value)} />}<button className="f-button" disabled={busy || !setup} onClick={async () => { if (await retry(pending)) setDialog(null); }}>{busy ? 'Memeriksa...' : 'Periksa penyimpanan'}</button></div>}
    {notice && <p className="f-notice" role="status">{notice}</p>}
    {saveError && !dialog && <p className="f-notice f-error" role="alert">{saveError}</p>}
    {setup && !manager && !setup.self_employee && <p className="f-notice">Akun ini belum terhubung ke profil karyawan. Minta pemilik menambahkan profil dan menghubungkan akunmu.</p>}
    {setup?.self_employee && <section className="f-panel"><h2>Kehadiran saya</h2><p>{setup.self_employee.name} · {setup.self_employee.code}</p>
      <p>{setup.open_attendance ? `Masuk ${hrTime(setup.open_attendance.clock_in, setup.outlets.find(o => o.id === setup.open_attendance?.outlet_id)?.timezone || zone)} · ${setup.outlets.find(o => o.id === setup.open_attendance?.outlet_id)?.name || 'Outlet'} · belum pulang` : 'Belum ada catatan masuk yang terbuka.'}</p>
      <div className="hr-actions">{setup.open_attendance ? <button className="f-button f-primary" disabled={mutationDisabled} onClick={() => open({ kind: 'punch', action: 'out' })}>Catat pulang sekarang</button>
        : <button className="f-button f-primary" disabled={mutationDisabled || !setup.self_employee.is_active || !selected} onClick={() => open({ kind: 'punch', action: 'in' })}>Catat masuk sekarang</button>}</div>
      {!manager && <p className="f-footnote">Daftar di bawah hanya menampilkan data kamu. Pengelola dapat mengoreksi catatan jika ada kesalahan.</p>}</section>}
    <div className="hr-tabs" aria-label="Bagian tim"><button className="f-button" aria-pressed={filters.kind === 'employees'} onClick={() => change('kind', 'employees')}>Karyawan</button><button className="f-button" aria-pressed={filters.kind === 'schedules'} onClick={() => change('kind', 'schedules')}>Jadwal</button><button className="f-button" aria-pressed={filters.kind === 'attendance'} onClick={() => change('kind', 'attendance')}>Absensi & izin</button></div>
    {setup && !setup.outlets.length && <div className="f-empty"><h2>Belum ada outlet aktif</h2><p>Aktifkan outlet lewat pengaturan untuk mulai mengelola tim.</p><a className="f-button" href="/dashboard/settings">Buka pengaturan</a></div>}
    {setup && selected && <form className="finance-toolbar" onSubmit={e => { e.preventDefault(); setFilters(v => ({ ...v, skip: 0 })); }}>
      <label>Outlet<select value={filters.outlet_id} onChange={e => change('outlet_id', e.target.value)}>{setup.outlets.map(o => <option value={o.id} key={o.id}>{o.name} · {zoneLabel(o.timezone)}</option>)}</select></label>
      <label>Dari tanggal<input type="date" required value={filters.start} onChange={e => change('start', e.target.value)} /></label><label>Sampai tanggal<input type="date" required value={filters.end} onChange={e => change('end', e.target.value)} /></label>
      <label>Cari nama atau kode<input type="search" maxLength={120} value={filters.search} onChange={e => change('search', e.target.value)} /></label>
      {filters.kind === 'employees' && <label>Status karyawan<select value={filters.active} onChange={e => change('active', e.target.value)}><option value="">Semua status</option><option value="active">Aktif</option><option value="inactive">Nonaktif</option></select></label>}
      <button type="button" className="f-button" disabled={loading} onClick={() => setRevision(v => v + 1)}>Muat ulang</button></form>}
    {error ? <div className="f-notice f-error" role="alert"><p>{error}</p><button className="f-button" onClick={() => setRevision(v => v + 1)}>Coba lagi</button></div> : loading ? <p className="f-notice" role="status">Memuat tim dan absensi...</p> : data && <>
      <section className="f-panel"><h2>{manager ? 'Ringkasan outlet' : 'Ringkasan saya'}</h2><p className="f-footnote">{selected?.name} · {hrDay(filters.start)} sampai {hrDay(filters.end)} · {zoneLabel(data.timezone)}. Filter nama dan status hanya mengubah daftar.</p>
        <div className="hr-summary"><div><span>Karyawan aktif di outlet</span><strong>{data.summary.active_employees ?? 'Tidak diizinkan'}</strong></div><div><span>Jadwal tercatat</span><strong>{data.summary.scheduled ?? 'Tidak diizinkan'}</strong></div><div><span>Kehadiran tercatat</span><strong>{data.summary.present ?? 'Tidak diizinkan'}</strong></div><div><span>Izin, sakit, cuti dan libur</span><strong>{data.summary.leave ?? 'Tidak diizinkan'}</strong></div></div>
        {data.summary.open != null && <p>{data.summary.open} catatan belum pulang{data.summary.unrecorded_started != null ? ` · ${data.summary.unrecorded_started} jadwal sudah mulai, belum ada catatan.` : ''}</p>}<p className="f-footnote">Belum ada catatan bukan berarti tidak hadir. Kehadiran mengikuti tanggal kerja, termasuk jadwal melewati tengah malam. Diperbarui {hrTime(data.generated_at, zone)}.</p></section>
      <section className="f-panel"><h2>{labels[filters.kind]}</h2><p>{data.total} catatan sesuai filter.</p>
        {!data.items.length ? <div className="f-empty"><h3>Belum ada {filters.kind === 'employees' ? 'karyawan' : filters.kind === 'schedules' ? 'jadwal' : 'kehadiran'} sesuai pilihan</h3><p>{filters.kind === 'employees' ? 'Tambahkan profil karyawan. Akun kasir boleh dihubungkan nanti.' : 'Periksa outlet dan periode, atau tambahkan catatan yang sudah dikonfirmasi.'}</p>{(filters.search || filters.active) && <button className="f-button" onClick={() => setFilters(v => ({ ...v, search: '', active: '', skip: 0 }))}>Reset filter</button>}</div>
          : <ul className="hr-list">{data.items.map(item => filters.kind === 'employees' ? <li key={item.id}><div><h3>{(item as HrEmployee).name}</h3><p>{(item as HrEmployee).code} · {(item as HrEmployee).position}</p><p>{(item as HrEmployee).is_active ? 'Aktif' : 'Nonaktif'} · Mulai {hrDay((item as HrEmployee).started_on)}{(item as HrEmployee).ended_on ? ` · Selesai ${hrDay((item as HrEmployee).ended_on!)}` : ''}</p>
              {manager && <p className="f-footnote">{(item as HrEmployee).phone || 'Nomor HP belum diisi'} · {(item as HrEmployee).user_id ? `Akun: ${setup?.accounts.find(a => a.id === (item as HrEmployee).user_id)?.name || 'Akun tidak aktif'}` : 'Belum terhubung akun kasir'}</p>}</div>
              {manager && <button className="f-button" disabled={mutationDisabled} aria-label={`Edit karyawan ${(item as HrEmployee).name}`} onClick={() => open({ kind: 'employees', row: item })}>Edit profil</button>}</li>
            : <li key={item.id}><div><h3>{(item as HrRecord).employee_name}</h3><p>{hrDay((item as HrRecord).work_date)}{filters.kind === 'attendance' ? ` · ${(item as HrRecord).status}` : ''}</p>
              <p>{filters.kind === 'schedules' ? `${hrTime((item as HrRecord).starts_at, zone)} → ${hrTime((item as HrRecord).ends_at, zone)}` : `${hrTime((item as HrRecord).clock_in, zone)}${(item as HrRecord).status === 'hadir' ? ` → ${(item as HrRecord).clock_out ? hrTime((item as HrRecord).clock_out, zone) : 'Belum pulang'}` : ''}`}</p>
              {filters.kind === 'attendance' && <p className="f-footnote">{(item as HrRecord).source === 'self' ? 'Awal dicatat dari akun karyawan' : 'Awal dicatat pengelola'}{(item as HrRecord).minutes != null ? ` · ${Math.floor((item as HrRecord).minutes! / 60)} jam ${(item as HrRecord).minutes! % 60} menit tercatat` : ''}</p>}
              {((item as HrRecord).notes || (item as HrRecord).reason) && <p className="hr-note">{(item as HrRecord).notes || (item as HrRecord).reason}</p>}</div>
              {manager && <div className="hr-actions"><button className="f-button" disabled={mutationDisabled} aria-label={`Edit ${labels[filters.kind]} ${(item as HrRecord).employee_name}`} onClick={() => open({ kind: filters.kind, row: item })}>{filters.kind === 'attendance' ? 'Koreksi' : 'Edit jadwal'}</button><button className="f-button" disabled={mutationDisabled} onClick={() => open({ kind: 'void', collection: filters.kind as 'schedules' | 'attendance', row: item as HrRecord })}>Batalkan</button></div>}</li>)}</ul>}
        {data.total > 0 && <div className="hr-pager"><p>{data.skip + (data.items.length ? 1 : 0)} sampai {data.skip + data.items.length} dari {data.total}</p><div className="hr-actions"><button className="f-button" disabled={filters.skip === 0} onClick={() => setFilters(v => ({ ...v, skip: Math.max(0, v.skip - 50) }))}>Sebelumnya</button><button className="f-button" disabled={data.skip + data.items.length >= data.total} onClick={() => setFilters(v => ({ ...v, skip: v.skip + 50 }))}>Berikutnya</button></div></div>}</section>
    </>}
    {dialog && setup && selected && <HrForm key={`${dialog.kind}:${'row' in dialog ? dialog.row?.id || 'new' : 'action' in dialog ? dialog.action : 'new'}`} dialog={dialog} setup={setup} outletId={selected.id} day={filters.start} zone={zone} pending={pending} busy={busy} error={saveError} submit={submit} retry={retry} close={() => setDialog(null)} />}
  </div>;
}

function EmployeeChoice({ row, frozen }: { row?: HrRecord; frozen: boolean }) {
  const [query, setQuery] = useState(''), [skip, setSkip] = useState(0), [choices, setChoices] = useState<{ id: string; name: string; code: string }[]>([]), [total, setTotal] = useState(0), [error, setError] = useState(''), [loading, setLoading] = useState(true), [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState('');
  useEffect(() => { if (row) return; let current = true; setLoading(true); setError(''); const timer = setTimeout(() => getHrEmployeeChoices(query, skip).then(result => { if (!current) return; if (result.success) { setChoices(result.data.items); setTotal(result.data.total); setSelected(''); } else setError(result.message); setLoading(false); }).catch(() => { if (current) { setError('Pilihan karyawan belum bisa dimuat. Coba lagi.'); setLoading(false); } }), 250); return () => { current = false; clearTimeout(timer); }; }, [query, skip, retry, row]);
  if (row) return <><p>Karyawan: {row.employee_name}</p><input type="hidden" name="employee_id" value={row.employee_id} /></>;
  return <div className="hr-choice"><label>Cari karyawan aktif<input type="search" value={query} disabled={frozen} maxLength={120} onChange={e => { setQuery(e.target.value); setSkip(0); }} /></label>
    {error ? <p className="f-error" role="alert">{error} <button type="button" className="f-button" onClick={() => setRetry(v => v + 1)}>Coba lagi</button></p> : loading ? <p role="status">Memuat pilihan karyawan...</p> : <><label>Karyawan<select aria-label="Karyawan" name="employee_id" required value={selected} disabled={frozen} onChange={e => setSelected(e.target.value)}><option value="">Pilih karyawan</option>{choices.map(c => <option key={c.id} value={c.id}>{c.name} · {c.code}</option>)}</select></label>
      <p className="f-footnote">{total ? `${skip + 1} sampai ${Math.min(skip + choices.length, total)} dari ${total} karyawan aktif dari seluruh outlet.` : 'Belum ada karyawan aktif sesuai pencarian. Tambahkan profil karyawan terlebih dahulu.'}</p>
      {total > 50 && <div className="hr-actions"><button type="button" className="f-button" disabled={skip === 0 || frozen} onClick={() => setSkip(v => Math.max(0, v - 50))}>Pilihan sebelumnya</button><button type="button" className="f-button" disabled={skip + choices.length >= total || frozen} onClick={() => setSkip(v => v + 50)}>Pilihan berikutnya</button></div>}</>}
  </div>;
}

function HrForm({ dialog, setup, outletId, day, zone, pending, busy, error, submit, retry, close }: { dialog: Dialog; setup: HrSetup; outletId: string; day: string; zone: string; pending: HrPending | null; busy: boolean; error: string; submit: (request: HrPending) => Promise<boolean>; retry: (request: HrPending) => Promise<boolean>; close: () => void }) {
  const employee = dialog.kind === 'employees' ? dialog.row as HrEmployee | undefined : undefined;
  const record = dialog.kind === 'schedules' || dialog.kind === 'attendance' ? dialog.row as HrRecord | undefined : undefined;
  const [status, setStatus] = useState(record?.status || 'hadir'), [localError, setLocalError] = useState('');
  const [accountMode, setAccountMode] = useState(employee?.user_id ? 'existing' : setup.account_admin && setup.shop_username ? 'new' : 'profile');
  const [accountId, setAccountId] = useState(employee?.user_id || ''), [placement, setPlacement] = useState(employee?.outlet_id || outletId);
  const [configureAccount, setConfigureAccount] = useState(false), [loginKind, setLoginKind] = useState('phone'), [resetPassword, setResetPassword] = useState(false);
  const linkedAccount = setup.accounts.find(a => a.id === accountId), newAccount = accountMode === 'new';
  const loginFields = setup.account_admin && (newAccount || accountMode === 'existing' && configureAccount && linkedAccount);
  const passwordNeeded = newAccount || !linkedAccount?.password_enabled || resetPassword;
  const frozen = Boolean(pending), title = dialog.kind === 'void' ? 'Batalkan catatan' : dialog.kind === 'punch' ? dialog.action === 'in' ? 'Catat masuk sekarang' : 'Catat pulang sekarang' : dialog.row ? dialog.kind === 'attendance' ? 'Koreksi kehadiran' : dialog.kind === 'employees' ? 'Edit profil karyawan' : 'Edit jadwal' : actions[dialog.kind];
  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (busy) return; setLocalError('');
    if (pending) { if (await retry(pending)) close(); return; }
    const f = new FormData(event.currentTarget), value = (key: string) => String(f.get(key) || '').trim();
    try {
      const payload: HrPending['payload'] = { client_request_id: crypto.randomUUID() };
      let path = '', method: 'POST' | 'PUT' = 'POST';
      if (dialog.kind === 'employees') {
        Object.assign(payload, { name: value('name'), position: value('position'), phone: value('phone') || null, outlet_id: value('outlet_id'), user_id: value('user_id') || null, started_on: value('started_on'), ended_on: value('ended_on') || null, is_active: value('is_active') === 'true', notes: value('notes') || null, row_version: employee?.row_version });
        if (loginFields) {
          const password = String(f.get('password') || '');
          if (passwordNeeded && password !== String(f.get('password_confirm') || '')) throw new Error('Ulangi password harus sama dengan password awal');
          payload.account = { use_phone: loginKind === 'phone', username: loginKind === 'username' ? value('username') : null, role_id: value('role_id') || null, user_row_version: linkedAccount?.row_version || null, password: passwordNeeded ? password : null };
        }
        path = employee ? `/employees/${employee.id}` : '/employees'; method = employee ? 'PUT' : 'POST';
      } else if (dialog.kind === 'void') { path = `/${dialog.collection}/${dialog.row.id}/void`; Object.assign(payload, { row_version: dialog.row.row_version, reason: value('reason') }); }
      else if (dialog.kind === 'punch') { path = '/punch'; Object.assign(payload, { action: dialog.action, outlet_id: dialog.action === 'out' ? setup.open_attendance?.outlet_id : outletId }); }
      else {
        Object.assign(payload, { employee_id: value('employee_id'), outlet_id: outletId, row_version: record?.row_version });
        if (dialog.kind === 'schedules') Object.assign(payload, { starts_at: zonedIso(value('starts_at'), zone), ends_at: zonedIso(value('ends_at'), zone), notes: value('notes') || null });
        else Object.assign(payload, { work_date: value('work_date'), status, clock_in: status === 'hadir' ? zonedIso(value('clock_in'), zone) : null, clock_out: status === 'hadir' ? zonedIso(value('clock_out'), zone) : null, reason: value('reason') || null, correction_reason: record ? value('correction_reason') : null });
        path = record ? `/${dialog.kind}/${record.id}` : `/${dialog.kind}`; method = record ? 'PUT' : 'POST';
      }
      if (await submit({ title, path, method, payload })) close();
    } catch (e) { setLocalError(e instanceof Error ? e.message : 'Periksa isian waktu'); }
  };
  return <InventoryDialog title={title} busy={busy} onClose={close}><form className="finance-form hr-form" onSubmit={save}>
    {(error || localError) && <p className="f-notice f-error" role="alert">{error || localError}</p>}
    {frozen && <p className="f-notice">Periksa penyimpanan data yang sama sebelum mengubah isinya.</p>}
    <fieldset disabled={busy || frozen}>
      {dialog.kind === 'employees' ? <>
        <label>Nama karyawan<input name="name" autoFocus required maxLength={120} defaultValue={employee?.name || ''} /></label><label>Jabatan / tugas<input name="position" required maxLength={100} defaultValue={employee?.position || ''} placeholder="Misalnya kasir atau barista" /></label>
        <label>Outlet penempatan<select name="outlet_id" required value={placement} onChange={e => setPlacement(e.target.value)}>{setup.outlets.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
        <label>Nomor HP<input name="phone" type="tel" required={Boolean(loginFields && loginKind === 'phone')} maxLength={40} defaultValue={employee?.phone || ''} placeholder="08 atau +62" /></label>
        {setup.account_admin && setup.shop_username ? <>
          <label>Akun karyawan<select aria-label="Akun karyawan" value={accountMode} onChange={e => { setAccountMode(e.target.value); setConfigureAccount(false); }}><option value="profile">Profil saja</option><option value="existing">Gunakan akun yang sudah ada</option>{!employee?.user_id && <option value="new">Buat akun baru</option>}</select></label>
          {accountMode === 'existing' && <><label>Hubungkan akun kasir<select name="user_id" required value={accountId} onChange={e => { setAccountId(e.target.value); setConfigureAccount(false); setResetPassword(false); }}><option value="">Pilih akun</option>{employee?.user_id && !linkedAccount && <option value={employee.user_id}>Akun terhubung (izin akun tidak dapat diatur)</option>}{setup.accounts.filter(a => !a.employee_id || a.employee_id === employee?.id).map(a => <option key={a.id} value={a.id}>{a.name}{a.username ? ` · ${a.username}` : ''}</option>)}</select></label>{linkedAccount && <label>Pengaturan login<select value={configureAccount ? 'configure' : 'keep'} onChange={e => setConfigureAccount(e.target.value === 'configure')}><option value="keep">Pertahankan login dan hak akses</option><option value="configure">Atur login akun ini</option></select></label>}<p className="f-footnote">Akun dan riwayat yang sudah ada tetap dipakai.</p></>}
          {accountMode !== 'existing' && <input type="hidden" name="user_id" value={accountMode === 'profile' ? employee?.user_id || '' : ''} />}
          {loginFields && <div className="hr-account-fields"><h3>Login karyawan</h3><p className="f-footnote">Username toko: {setup.shop_username}. Profil dan akun disimpan bersama.</p>
            <label>Masuk menggunakan<select aria-label="Masuk menggunakan" value={loginKind} onChange={e => setLoginKind(e.target.value)}><option value="phone">Nomor HP karyawan</option><option value="username">Username akun</option></select></label>
            {loginKind === 'username' && <><label>Username akun<input name="username" required minLength={3} maxLength={64} pattern="[A-Za-z0-9](?:[A-Za-z0-9_]|-){2,63}" defaultValue={linkedAccount?.username || ''} autoCapitalize="none" autoCorrect="off" spellCheck={false} /></label><p className="f-footnote">Minimal 3 karakter, tanpa spasi. Contoh: irfan.</p></>}
            <label>Hak akses<select aria-label="Hak akses" name="role_id" key={`${accountId}:${placement}`} defaultValue=""><option value="">{newAccount ? 'Absensi pribadi' : 'Pertahankan hak akses akun'}</option>{(setup.roles || []).filter(r => r.scope === 'tenant' || r.outlet_ids.includes(placement)).map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
            <p className="f-footnote">Absensi pribadi hanya memberi akses jadwal dan kehadiran sendiri. Pilih jabatan yang diberi akses kasir jika karyawan perlu bertransaksi.</p>
            {!newAccount && linkedAccount?.password_enabled && <label>Password<select aria-label="Password" value={resetPassword ? 'reset' : 'keep'} onChange={e => setResetPassword(e.target.value === 'reset')}><option value="keep">Pertahankan password</option><option value="reset">Tetapkan password baru</option></select></label>}
            {passwordNeeded && <><PasswordInput label="Password awal" name="password" required minLength={8} maxLength={128} autoComplete="new-password" /><PasswordInput label="Ulangi password awal" name="password_confirm" required minLength={8} maxLength={128} autoComplete="new-password" /><p className="f-footnote">Minimal 8 karakter. Berikan username toko, nomor HP atau username akun, dan password awal kepada karyawan.</p></>}
          </div>}
        </> : <><label>Hubungkan akun kasir<select name="user_id" defaultValue={employee?.user_id || ''} disabled={!setup.accounts.length}><option value="">Belum dihubungkan</option>{employee?.user_id && !setup.accounts.some(a => a.id === employee.user_id) && <option value={employee.user_id}>Akun terhubung</option>}{setup.accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>{!setup.accounts.length && <input type="hidden" name="user_id" value={employee?.user_id || ''} />}<p className="f-footnote">{setup.account_admin ? <>Tetapkan username toko di <Link href="/dashboard/hris/access">Akun saya</Link> untuk membuat akun dari form ini.</> : 'Profil dapat disimpan. Pembuatan akun memerlukan izin dari pemilik.'}</p></>}
        <div className="f-field-grid"><label>Tanggal mulai kerja<input name="started_on" type="date" required defaultValue={employee?.started_on || day} /></label><label>Tanggal selesai kerja<input name="ended_on" type="date" defaultValue={employee?.ended_on || ''} /></label></div>
        <label>Status karyawan<select name="is_active" defaultValue={employee?.is_active === false ? 'false' : 'true'}><option value="true">Aktif</option><option value="false">Nonaktif</option></select></label><p className="f-footnote">Menonaktifkan profil tetap menyimpan riwayat. Hak masuk akun kasir diatur di pengaturan akun.</p><label>Catatan pengelola<textarea name="notes" maxLength={2000} defaultValue={employee?.notes || ''} /></label>
      </> : dialog.kind === 'void' ? <><p>{dialog.row.employee_name} · {hrDay(dialog.row.work_date)}. Catatan akan dibatalkan dan riwayat koreksinya tetap disimpan.</p><label>Alasan pembatalan<textarea name="reason" autoFocus required maxLength={500} /></label></>
        : dialog.kind === 'punch' ? <><p>{setup.self_employee?.name} · {setup.outlets.find(o => o.id === (dialog.action === 'out' ? setup.open_attendance?.outlet_id : outletId))?.name}</p><p>Waktu {dialog.action === 'in' ? 'masuk' : 'pulang'} dicatat ketika tombol simpan ditekan. Periksa outlet sebelum menyimpan.</p></>
        : <><p>Outlet: {setup.outlets.find(o => o.id === outletId)?.name} · Semua jam dalam {zoneLabel(zone)}.</p><EmployeeChoice row={record} frozen={busy || frozen} />
          {dialog.kind === 'schedules' ? <><div className="f-field-grid"><label>Mulai kerja<input name="starts_at" type="datetime-local" required defaultValue={localTime(record?.starts_at, zone) || `${day}T08:00`} /></label><label>Selesai kerja<input name="ends_at" type="datetime-local" required defaultValue={localTime(record?.ends_at, zone) || `${day}T16:00`} /></label></div><p className="f-footnote">Untuk jadwal malam, pilih tanggal berikutnya pada jam selesai. Maksimal 24 jam.</p><label>Catatan jadwal<textarea name="notes" maxLength={1000} defaultValue={record?.notes || ''} /></label></>
            : <><label>Tanggal kerja<input name="work_date" type="date" required readOnly={Boolean(record)} defaultValue={record?.work_date || day} /></label><label>Status kehadiran<select name="status" value={status} onChange={e => setStatus(e.target.value)}><option value="hadir">Hadir</option><option value="izin">Izin</option><option value="sakit">Sakit</option><option value="cuti">Cuti</option><option value="libur">Libur</option></select></label>
              {status === 'hadir' && <div className="f-field-grid"><label>Jam masuk<input name="clock_in" type="datetime-local" required defaultValue={localTime(record?.clock_in, zone) || `${day}T08:00`} /></label><label>Jam pulang<input name="clock_out" type="datetime-local" defaultValue={localTime(record?.clock_out, zone)} /></label></div>}
              <label>{status === 'hadir' ? 'Catatan (opsional)' : 'Alasan'}<textarea name="reason" required={status !== 'hadir'} maxLength={1000} defaultValue={record?.reason || ''} /></label>{record && <label>Alasan koreksi<textarea name="correction_reason" required maxLength={500} /></label>}<p className="f-footnote">Kehadiran masa depan tidak dapat dicatat. Izin, sakit, cuti, dan libur boleh dicatat lebih awal setelah dikonfirmasi.</p></>}
        </>}
    </fieldset><div className="f-form-actions"><button className="f-button" type="button" disabled={busy} onClick={close}>Tutup</button><button className="f-button f-primary" disabled={busy}>{busy ? 'Menyimpan...' : frozen ? 'Periksa penyimpanan' : 'Simpan'}</button></div>
  </form></InventoryDialog>;
}
