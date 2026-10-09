'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { getOutlets, updateOutlet, updateStockMode, getCurrentUser, getTaxConfig, updateTaxConfig, getReferralCode, getReferralStats, setupOutletWhatsApp } from '@/app/actions/api';
import { DeliveryHoursSettings } from '@/components/dashboard/delivery-hours-settings';
import { CourierSettings } from '@/components/dashboard/courier-settings';
import { Loader2 } from 'lucide-react';
import './settings.css';

/*
 * Pengaturan (disusun ulang 9 Okt 2026, mockup disetujui Ivan).
 *
 * Kelompok mengikuti cara pemilik berpikir: Toko, Kasir dan struk, Pesanan online
 * dan antar, Stok, Langganan. Semua pengaturan lama tetap ada, hanya dipindah.
 *
 * Satu aturan simpan:
 * - saklar dan pilihan langsung tersimpan (patch kecil ke outlet), tanda kecil di barisnya;
 * - isian teks/angka (profil, rekening, pajak dan struk) menandai "ada perubahan" dan
 *   disimpan bersama lewat bilah Simpan perubahan di bawah. Tidak ada alert() browser.
 *
 * Nomor toko digabung (keputusan Ivan): satu isian "Nomor WhatsApp toko" menulis ke
 * outlets.phone DAN outlets.whatsapp_number, karena backend membaca keduanya
 * (whatsapp_number dulu, phone cadangan). Teks bebas jam operasional hanya muncul
 * di mode Manual; di mode jadwal halaman toko memakai hours_today dari jadwal.
 *
 * Pengaturan berlaku per outlet: dulu hanya outlets[0], sekarang bisa dipilih.
 */

type Section = 'toko' | 'kasir' | 'online' | 'stok' | 'langganan';
const SECTIONS: { id: Section; label: string; icon: string }[] = [
  { id: 'toko', label: 'Toko', icon: 'M3 9l1.5-5h15L21 9M4 9v11h16V9M3 9h18M9 20v-6h6v6' },
  { id: 'kasir', label: 'Kasir dan struk', icon: 'M3 4h18v12H3zM7 20h10M12 16v4' },
  { id: 'online', label: 'Pesanan online dan antar', icon: 'M3 7h13v10H3zM16 10h3l2 3v4h-5M7 20a2 2 0 100-4 2 2 0 000 4zM18 20a2 2 0 100-4 2 2 0 000 4z' },
  { id: 'stok', label: 'Stok', icon: 'M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8' },
  { id: 'langganan', label: 'Langganan', icon: 'M3 6h18v13H3zM3 10h18' },
];
const DAY_KEYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
const rp = (n: number) => 'Rp' + Math.round(n || 0).toLocaleString('id-ID');
const digits = (v: string) => v.replace(/\D/g, '');

type Msg = { ok: boolean; text: string } | null;
type Profile = { name: string; whatsapp: string; address: string; opening_hours: string; cover_image_url: string };
type Tax = { pb1_enabled: boolean; tax_pct: number; service_charge_enabled: boolean; service_charge_pct: number; tax_inclusive: boolean; tax_number: string; receipt_footer: string; row_version: number };
type Bank = { bank_name: string; bank_account_number: string; bank_account_name: string };
const NO_TAX: Tax = { pb1_enabled: false, tax_pct: 10, service_charge_enabled: false, service_charge_pct: 5, tax_inclusive: false, tax_number: '', receipt_footer: '', row_version: 0 };

function Switch({ on, label, disabled, onChange }: { on: boolean; label: string; disabled?: boolean; onChange: (v: boolean) => void }) {
  return <button type="button" className="st-switch" role="switch" aria-checked={on} aria-label={label} disabled={disabled} onClick={() => onChange(!on)} />;
}
function Seg<T extends string | number>({ value, options, label, disabled, onChange }: { value: T; options: [T, string][]; label: string; disabled?: boolean; onChange: (v: T) => void }) {
  return <div className="st-seg" role="group" aria-label={label}>{options.map(([v, text]) =>
    <button key={String(v)} type="button" aria-pressed={value === v} disabled={disabled} onClick={() => value !== v && onChange(v)}>{text}</button>)}</div>;
}
function Note({ msg }: { msg: Msg }) {
  return msg ? <span className={`st-msg ${msg.ok ? 'ok' : 'err'}`} role="status">{msg.text}</span> : null;
}
function Row({ title, hint, children, block }: { title?: string; hint?: React.ReactNode; children?: React.ReactNode; block?: boolean }) {
  return <div className={`st-row${block ? ' st-block' : ''}`}>
    {title !== undefined && <div className="st-t"><b>{title}</b>{hint && <small>{hint}</small>}</div>}
    {children !== undefined && (block ? children : <div className="st-v">{children}</div>)}
  </div>;
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true), [loadError, setLoadError] = useState('');
  const [outlets, setOutlets] = useState<any[]>([]), [outletId, setOutletId] = useState('');
  const [outlet, setOutlet] = useState<any>(null);
  const [section, setSection] = useState<Section>('toko');
  const [tier, setTier] = useState('starter');
  const isPro = ['pro', 'business', 'enterprise'].includes(tier);

  // Isian yang disimpan lewat bilah Simpan perubahan.
  const [profile, setProfile] = useState<Profile>({ name: '', whatsapp: '', address: '', opening_hours: '', cover_image_url: '' });
  const [tax, setTax] = useState<Tax>(NO_TAX);
  const [bank, setBank] = useState<Bank>({ bank_name: '', bank_account_number: '', bank_account_name: '' });
  const [base, setBase] = useState<{ profile: Profile; tax: Tax; bank: Bank } | null>(null);
  const [saving, setSaving] = useState(false), [saveMsg, setSaveMsg] = useState<Msg>(null);

  // Saklar dan pilihan yang langsung tersimpan.
  const [quick, setQuick] = useState<Record<string, any>>({});
  const [rowMsg, setRowMsg] = useState<Record<string, Msg>>({});
  const [busyKey, setBusyKey] = useState('');
  const [uploading, setUploading] = useState(''), coverInput = useRef<HTMLInputElement>(null), qrisInput = useRef<HTMLInputElement>(null);

  const [referral, setReferral] = useState<{ code: string; url: string; text: string; stats: any } | null>(null);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    const fromHash = window.location.hash.slice(1) as Section;
    if (SECTIONS.some(s => s.id === fromHash)) setSection(fromHash);
  }, []);
  const go = (id: Section) => { setSection(id); history.replaceState(null, '', `#${id}`); };

  const apply = useCallback(async (data: any) => {
    setOutlet(data);
    const p: Profile = { name: data.name || '', whatsapp: data.whatsapp_number || data.phone || '', address: data.address || '',
      opening_hours: typeof data.opening_hours === 'string' ? data.opening_hours : '', cover_image_url: data.cover_image_url || '' };
    const b: Bank = { bank_name: data.bank_name || '', bank_account_number: data.bank_account_number || '', bank_account_name: data.bank_account_name || '' };
    let t: Tax = NO_TAX;
    try {
      const tc = await getTaxConfig(data.id);
      if (tc) t = { pb1_enabled: tc.pb1_enabled ?? false, tax_pct: tc.tax_pct ?? 10, service_charge_enabled: tc.service_charge_enabled ?? false,
        service_charge_pct: tc.service_charge_pct ?? 5, tax_inclusive: tc.tax_inclusive ?? false, tax_number: tc.tax_number ?? '',
        receipt_footer: tc.receipt_footer ?? '', row_version: tc.row_version ?? 0 };
    } catch { /* Pajak tetap bisa diisi; simpan akan memberi tahu kalau gagal. */ }
    setProfile(p); setBank(b); setTax(t); setBase({ profile: p, tax: t, bank: b });
    setQuick({
      is_open: data.is_open !== false, hours_mode: data.hours_mode === 'schedule' ? 'schedule' : 'manual',
      payment_methods: Array.isArray(data.payment_methods) && data.payment_methods.length ? data.payment_methods : ['cash', 'qris'],
      qris_channel: data.qris_channel || 'manual', qris_static_image_url: data.qris_static_image_url || '',
      online_orders_enabled: data.online_orders_enabled ?? true, online_notify_owner_wa: data.online_notify_owner_wa ?? true,
      online_auto_cancel_minutes: data.online_auto_cancel_minutes ?? 10, kitchen_mode: data.kitchen_mode === 'display' ? 'display' : 'off',
      shift_mode: data.shift_mode || 'ringan', stock_mode: data.stock_mode || 'simple', wa_connected: !!data.wa_connected,
    });
    setRowMsg({}); setSaveMsg(null);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const list = await getOutlets();
        if (!list?.length) { setLoadError('Belum ada outlet. Buat outlet dulu di aplikasi kasir.'); return; }
        setOutlets(list); setOutletId(list[0].id); await apply(list[0]);
        const user = await getCurrentUser();
        if (user) setTier(user.subscription_tier || 'starter');
        try {
          const ref = await getReferralCode();
          if (ref?.referral_code) setReferral({ code: ref.referral_code, url: ref.share_url, text: ref.share_text, stats: await getReferralStats().catch(() => null) });
        } catch { /* Kartu ajak usaha lain cukup disembunyikan. */ }
      } catch { setLoadError('Pengaturan belum bisa dimuat. Periksa koneksi lalu muat ulang.'); }
      finally { setLoading(false); }
    })();
  }, [apply]);

  const dirty = useMemo(() => {
    const s = base;
    if (!s) return [] as string[];
    const out: string[] = [];
    if (JSON.stringify(profile) !== JSON.stringify(s.profile)) out.push('profil toko');
    if (JSON.stringify(bank) !== JSON.stringify(s.bank)) out.push('rekening');
    if (JSON.stringify(tax) !== JSON.stringify(s.tax)) out.push('pajak dan struk');
    return out;
  }, [base, profile, bank, tax]);

  const switchOutlet = async (id: string) => {
    if (dirty.length) { setSaveMsg({ ok: false, text: 'Simpan atau batalkan perubahan dulu sebelum pindah outlet.' }); return; }
    const next = outlets.find(o => o.id === id);
    if (!next) return;
    setOutletId(id); setLoading(true);
    const fresh = (await getOutlets().catch(() => null))?.find((o: any) => o.id === id) || next;
    await apply(fresh); setLoading(false);
  };

  // Patch kecil yang langsung tersimpan. Kalau gagal, nilai lama dikembalikan.
  async function quickSave(key: string, patch: Record<string, any>, ok = 'Tersimpan') {
    if (!outlet) return false;
    const prev = { ...quick };
    setQuick(q => ({ ...q, ...patch })); setBusyKey(key); setRowMsg(m => ({ ...m, [key]: null }));
    const res = await updateOutlet(outlet.id, patch);
    setBusyKey('');
    if (res?.success) { setOutlet((o: any) => ({ ...o, ...patch })); setRowMsg(m => ({ ...m, [key]: { ok: true, text: ok } })); return true; }
    setQuick(prev); setRowMsg(m => ({ ...m, [key]: { ok: false, text: res?.message || 'Belum tersimpan. Coba lagi.' } }));
    return false;
  }

  async function saveAll() {
    if (!outlet || !base || saving) return;
    setSaving(true); setSaveMsg(null);
    const s = base;
    try {
      if (JSON.stringify(profile) !== JSON.stringify(s.profile) || JSON.stringify(bank) !== JSON.stringify(s.bank)) {
        const wa = digits(profile.whatsapp);
        const patch: Record<string, any> = { name: profile.name.trim(), address: profile.address, cover_image_url: profile.cover_image_url,
          phone: wa, whatsapp_number: wa, ...bank };
        if (quick.hours_mode !== 'schedule') patch.opening_hours = profile.opening_hours;
        if (!patch.name) throw new Error('Nama toko wajib diisi.');
        const res = await updateOutlet(outlet.id, patch);
        if (!res?.success) throw new Error(res?.message || 'Profil toko belum tersimpan.');
        setOutlet((o: any) => ({ ...o, ...patch }));
        setBase(v => v && { ...v, profile, bank });
      }
      if (JSON.stringify(tax) !== JSON.stringify(s.tax)) {
        const updated = await updateTaxConfig(outlet.id, { pb1_enabled: tax.pb1_enabled, tax_pct: tax.tax_pct, service_charge_enabled: tax.service_charge_enabled,
          service_charge_pct: tax.service_charge_pct, tax_inclusive: tax.tax_inclusive, tax_number: tax.tax_number.trim() || null,
          receipt_footer: tax.receipt_footer.trim() || null, expected_row_version: tax.row_version });
        const next = { ...tax, row_version: updated?.row_version ?? tax.row_version + 1 };
        setTax(next); setBase(v => v && { ...v, tax: next });
      }
      setSaveMsg({ ok: true, text: 'Perubahan tersimpan.' });
    } catch (e) {
      setSaveMsg({ ok: false, text: e instanceof Error ? e.message : 'Belum tersimpan. Coba lagi.' });
    } finally { setSaving(false); }
  }
  const undo = () => { if (base) { setProfile(base.profile); setTax(base.tax); setBank(base.bank); setSaveMsg(null); } };

  async function upload(kind: 'cover' | 'qris', file?: File) {
    if (!file) return;
    setUploading(kind);
    try {
      const fd = new FormData(); fd.append('file', file);
      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok || !data.url) throw new Error(data.detail || 'Unggah gagal. Coba foto lain.');
      const url = `${process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || ''}${data.url}`;
      if (kind === 'cover') setProfile(p => ({ ...p, cover_image_url: url }));
      else await quickSave('qris', { qris_static_image_url: url }, 'Gambar QRIS tersimpan');
    } catch (e) {
      setRowMsg(m => ({ ...m, [kind]: { ok: false, text: e instanceof Error ? e.message : 'Unggah gagal' } }));
    } finally { setUploading(''); if (coverInput.current) coverInput.current.value = ''; if (qrisInput.current) qrisInput.current.value = ''; }
  }

  // Pindah mode stok butuh konfirmasi dan bisa ditolak server (resep belum lengkap).
  const [stockConfirm, setStockConfirm] = useState<'simple' | 'recipe' | null>(null);
  const [stockMsg, setStockMsg] = useState<{ ok: boolean; text: string; recipes?: boolean } | null>(null);
  async function changeStockMode() {
    const mode = stockConfirm;
    if (!mode || !outlet) return;
    setStockConfirm(null); setBusyKey('stock'); setStockMsg(null);
    try {
      const r = await updateStockMode(outlet.id, mode);
      if (!r.success) { setStockMsg({ ok: false, text: r.message, recipes: r.needsRecipeSetup }); return; }
      setQuick(q => ({ ...q, stock_mode: mode }));
      setStockMsg({ ok: true, text: mode === 'recipe' ? 'Stok sekarang dihitung dari resep dan bahan baku.' : 'Stok kembali dihitung per produk.' });
    } catch { setStockMsg({ ok: false, text: 'Belum tersimpan. Muat ulang halaman lalu coba lagi.' }); }
    finally { setBusyKey(''); }
  }

  const copy = async (key: string, text: string) => {
    try { await navigator.clipboard.writeText(text); setCopied(key); setTimeout(() => setCopied(''), 2000); } catch { setCopied(''); }
  };

  if (loading && !outlet) return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-[var(--brand-primary)]" /></div>;
  if (loadError) return <p className="text-[var(--danger)]" role="alert">{loadError}</p>;

  const storefront = outlet?.slug ? `${window.location.origin}/${outlet.slug}` : '';
  const methods: string[] = quick.payment_methods || ['cash'];
  const toggleMethod = (m: string, on: boolean) => {
    const set = new Set(methods); if (on) set.add(m); else set.delete(m); set.add('cash');
    void quickSave(`pay-${m}`, { payment_methods: ['cash', 'qris', 'transfer', 'card'].filter(x => set.has(x)) }, on ? 'Aktif' : 'Nonaktif');
  };
  const today = (() => {
    const slots = outlet?.business_hours?.[DAY_KEYS[new Date().getDay()]];
    if (!Array.isArray(slots)) return null;
    return slots.length ? slots.map((s: string[]) => `${s[0].replace(':', '.')} sampai ${s[1].replace(':', '.')}`).join(', ') : 'tutup';
  })();
  const open = quick.is_open !== false;
  const statusSub = !open ? 'Pelanggan masih bisa melihat menu, tapi belum bisa memesan.'
    : quick.hours_mode === 'schedule' ? (today === 'tutup' ? 'Ikut jadwal. Hari ini jadwalnya tutup.' : today ? `Ikut jadwal. Hari ini ${today}.` : 'Ikut jadwal.')
    : 'Manual. Toko buka sampai Anda menutupnya.';

  return <div className="space-y-4">
    <div className="st">
      <nav className="st-rail" aria-label="Kelompok pengaturan">
        <div className="st-outlet">
          <b>{outlet?.name || 'Outlet'}</b>
          {outlets.length > 1 && <select aria-label="Pilih outlet" value={outletId} onChange={e => switchOutlet(e.target.value)}>{outlets.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select>}
        </div>
        {SECTIONS.map(s => <button key={s.id} type="button" className="st-nav" aria-current={section === s.id} onClick={() => go(s.id)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={s.icon} /></svg>{s.label}</button>)}
        <p className="st-rail-note">{outlets.length > 1 ? 'Pengaturan berlaku per outlet. Pilih outlet di atas.' : 'Pengaturan berlaku untuk outlet ini.'}</p>
      </nav>

      <main className="st-main" aria-busy={loading}>
        {section === 'toko' && <section className="st-section">
          <div className="st-head"><h1>Toko</h1><p>Yang dilihat pelanggan: nama, foto, alamat, dan kapan toko buka.</p></div>
          <div className="st-status" data-open={open}>
            <div className="st-dot" />
            <div><strong>{open ? 'Buka, menerima pesanan' : 'Tutup sementara'}</strong><span>{statusSub}{open && quick.online_orders_enabled === false ? ' Pesanan online sedang dimatikan.' : ''}</span> <Note msg={rowMsg.open} /></div>
            <Switch on={open} label="Toko buka" disabled={busyKey === 'open'} onChange={v => quickSave('open', { is_open: v }, v ? 'Toko dibuka' : 'Toko ditutup sementara')} />
          </div>

          <div className="st-group"><h2>Profil</h2>
            <div className="st-list">
              <Row block>
                <div className="st-cover">
                  {profile.cover_image_url ? <img src={profile.cover_image_url} alt="Foto sampul toko" /> : <span>Belum ada foto sampul. Ukuran ideal 800 x 300.</span>}
                  <div className="st-cover-acts">
                    <button type="button" className="st-btn" disabled={uploading === 'cover'} onClick={() => coverInput.current?.click()}>{uploading === 'cover' ? 'Mengunggah…' : profile.cover_image_url ? 'Ganti foto' : 'Pilih foto'}</button>
                    {profile.cover_image_url && <button type="button" className="st-btn danger" onClick={() => setProfile(p => ({ ...p, cover_image_url: '' }))}>Hapus</button>}
                  </div>
                </div>
                <input ref={coverInput} type="file" accept="image/*" hidden onChange={e => upload('cover', e.target.files?.[0])} />
                <Note msg={rowMsg.cover} />
              </Row>
              <Row block><div className="st-field"><label htmlFor="st-name">Nama toko</label><input id="st-name" required maxLength={120} value={profile.name} onChange={e => setProfile(p => ({ ...p, name: e.target.value }))} /></div></Row>
              <Row block><div className="st-field"><label htmlFor="st-address">Alamat</label><textarea id="st-address" rows={2} value={profile.address} onChange={e => setProfile(p => ({ ...p, address: e.target.value }))} /></div></Row>
              <Row block><div className="st-field"><label htmlFor="st-wa">Nomor WhatsApp toko</label><input id="st-wa" type="tel" inputMode="tel" placeholder="0812..." value={profile.whatsapp} onChange={e => setProfile(p => ({ ...p, whatsapp: digits(e.target.value) }))} />
                <small>Dipakai untuk tombol WhatsApp di halaman toko dan kabar pesanan ke Anda.</small></div></Row>
            </div>
          </div>

          <div className="st-group"><h2>Jam buka</h2>
            <div className="st-embed"><DeliveryHoursSettings key={`hours-${outlet?.id}`} part="hours" outlet={outlet} onSaved={patch => { setOutlet((o: any) => ({ ...o, ...patch })); if (patch.hours_mode) setQuick(q => ({ ...q, hours_mode: patch.hours_mode })); }} /></div>
            {quick.hours_mode !== 'schedule' && <div className="st-list"><Row block><div className="st-field"><label htmlFor="st-hours">Jam buka yang ditampilkan di halaman toko</label>
              <input id="st-hours" placeholder="Contoh: Setiap hari 08.00 sampai 22.00" value={profile.opening_hours} onChange={e => setProfile(p => ({ ...p, opening_hours: e.target.value }))} />
              <small>Hanya untuk mode Manual. Kalau memakai jadwal, halaman toko menulis jam dari jadwal.</small></div></Row></div>}
          </div>

          <div className="st-group"><h2>Halaman toko online</h2>
            <div className="st-list">
              {storefront ? <Row title={storefront.replace(/^https?:\/\//, '')} hint="Bagikan tautan ini ke pelanggan, atau cetak QR untuk meja.">
                <button type="button" className="st-btn" onClick={() => copy('link', storefront)}>{copied === 'link' ? 'Tersalin' : 'Salin'}</button>
                <a className="st-btn" href={storefront} target="_blank" rel="noopener noreferrer">Buka</a>
                <Link className="st-btn" href="/dashboard/toko">QR dan stiker</Link>
              </Row> : <Row title="Tautan toko belum tersedia" hint="Simpan nama toko terlebih dahulu." />}
            </div>
          </div>
        </section>}

        {section === 'kasir' && <section className="st-section">
          <div className="st-head"><h1>Kasir dan struk</h1><p>Cara pelanggan membayar, apa yang tercetak di struk, dan seberapa ketat hitungan laci.</p></div>
          <div className="st-group"><h2>Pembayaran</h2>
            <div className="st-list">
              <Row title="Tunai" hint="Selalu aktif. Kembalian dihitung otomatis."><span className="st-pill on">Aktif</span></Row>
              <Row title="QRIS" hint={quick.qris_channel === 'xendit' ? 'QRIS dinamis lewat Xendit, lunas terkonfirmasi otomatis.' : quick.qris_static_image_url ? 'Kasir menampilkan gambar QRIS toko dan menekan Konfirmasi setelah uang masuk.' : 'Unggah gambar QRIS dari aplikasi bank atau dompet digital Anda.'}>
                <Note msg={rowMsg['pay-qris'] || rowMsg.qris} /><Switch on={methods.includes('qris')} label="QRIS" disabled={busyKey.startsWith('pay')} onChange={v => toggleMethod('qris', v)} />
              </Row>
              {methods.includes('qris') && quick.qris_channel !== 'xendit' && <Row block>
                <div className="flex flex-wrap items-center gap-4">
                  {quick.qris_static_image_url ? <img className="st-qris" src={quick.qris_static_image_url} alt="QRIS toko" /> : null}
                  <div className="grid gap-2">
                    <button type="button" className="st-btn" disabled={uploading === 'qris'} onClick={() => qrisInput.current?.click()}>{uploading === 'qris' ? 'Mengunggah…' : quick.qris_static_image_url ? 'Ganti gambar QRIS' : 'Unggah gambar QRIS'}</button>
                    <Link className="text-sm font-semibold text-[var(--brand-primary)]" href="/dashboard/settings/payment">Ingin lunas otomatis? Hubungkan Xendit</Link>
                  </div>
                  <input ref={qrisInput} type="file" accept="image/*" hidden onChange={e => upload('qris', e.target.files?.[0])} />
                </div>
              </Row>}
              <Row title="Transfer bank" hint={bank.bank_name ? `${bank.bank_name} ${bank.bank_account_number} a.n. ${bank.bank_account_name}` : 'Isi rekening tujuan setelah dinyalakan.'}>
                <Note msg={rowMsg['pay-transfer']} /><Switch on={methods.includes('transfer')} label="Transfer bank" disabled={busyKey.startsWith('pay')} onChange={v => toggleMethod('transfer', v)} />
              </Row>
              {methods.includes('transfer') && <Row block><div className="st-grid3">
                <div className="st-field"><label htmlFor="st-bank">Bank</label><input id="st-bank" placeholder="BCA, BRI, Mandiri" value={bank.bank_name} onChange={e => setBank(b => ({ ...b, bank_name: e.target.value }))} /></div>
                <div className="st-field"><label htmlFor="st-acc">Nomor rekening</label><input id="st-acc" inputMode="numeric" value={bank.bank_account_number} onChange={e => setBank(b => ({ ...b, bank_account_number: e.target.value.replace(/[^0-9-]/g, '') }))} /></div>
                <div className="st-field"><label htmlFor="st-accname">Atas nama</label><input id="st-accname" value={bank.bank_account_name} onChange={e => setBank(b => ({ ...b, bank_account_name: e.target.value }))} /></div>
              </div></Row>}
              <Row title="Kartu EDC" hint="Debit atau kredit lewat mesin EDC bank Anda.">
                <Note msg={rowMsg['pay-card']} /><Switch on={methods.includes('card')} label="Kartu EDC" disabled={busyKey.startsWith('pay')} onChange={v => toggleMethod('card', v)} />
              </Row>
            </div>
          </div>

          <div className="st-group"><h2>Pajak dan struk</h2>
            <div className="st-split">
              <div className="st-list">
                <Row title="Pajak restoran (PB1)">
                  {tax.pb1_enabled && <><input className="st-num" type="number" min={0} max={100} step={0.5} aria-label="Persen pajak" value={tax.tax_pct} onChange={e => setTax(t => ({ ...t, tax_pct: parseFloat(e.target.value) || 0 }))} /> %</>}
                  <Switch on={tax.pb1_enabled} label="Pajak restoran" onChange={v => setTax(t => ({ ...t, pb1_enabled: v }))} />
                </Row>
                {tax.pb1_enabled && <Row title="Harga menu sudah termasuk pajak"><Switch on={tax.tax_inclusive} label="Harga termasuk pajak" onChange={v => setTax(t => ({ ...t, tax_inclusive: v }))} /></Row>}
                <Row title="Service charge">
                  {tax.service_charge_enabled && <><input className="st-num" type="number" min={0} max={100} step={0.5} aria-label="Persen service" value={tax.service_charge_pct} onChange={e => setTax(t => ({ ...t, service_charge_pct: parseFloat(e.target.value) || 0 }))} /> %</>}
                  <Switch on={tax.service_charge_enabled} label="Service charge" onChange={v => setTax(t => ({ ...t, service_charge_enabled: v }))} />
                </Row>
                <Row block><div className="st-field"><label htmlFor="st-npwp">NPWP di kepala struk</label><input id="st-npwp" maxLength={30} placeholder="01.234.567.8-901.000" value={tax.tax_number} onChange={e => setTax(t => ({ ...t, tax_number: e.target.value }))} /><small>Kosongkan kalau belum PKP.</small></div></Row>
                <Row block><div className="st-field"><label htmlFor="st-foot">Pesan di bawah struk</label><textarea id="st-foot" rows={2} maxLength={200} placeholder="Ikuti IG toko, promo kopi tiap Jumat" value={tax.receipt_footer} onChange={e => setTax(t => ({ ...t, receipt_footer: e.target.value }))} /><small>{tax.receipt_footer.length}/200. Kosong berarti tulisan Powered by Selaris.</small></div></Row>
              </div>
              <div><Receipt name={profile.name} address={profile.address} tax={tax} /><p className="st-cap">Pratinjau struk, ikut berubah saat Anda mengetik</p></div>
            </div>
          </div>

          <div className="st-group"><h2>Laci kas dan dapur</h2>
            <div className="st-list">
              <Row title="Ketatnya hitungan laci" hint={{ ringan: 'Hitung kas opsional, kasir melihat angka sistem. Cocok kalau toko dijaga sendiri.', standar: 'Kasir mengetik hitungan tanpa melihat angka sistem. Selisih hanya terlihat oleh Anda.', ketat: 'Kasir wajib membuka dengan modal awal. Laci terkunci ke kasir itu sampai serah terima.' }[quick.shift_mode as string]}>
                <Note msg={rowMsg.shift} />
                <Seg label="Mode kas" value={quick.shift_mode} disabled={busyKey === 'shift'} options={[['ringan', 'Ringan'], ['standar', 'Standar'], ['ketat', 'Ketat']]} onChange={v => quickSave('shift', { shift_mode: v }, 'Mode kas tersimpan')} />
              </Row>
              <Row title="Layar dapur" hint={isPro ? 'Antrean pesanan di aplikasi Dapur, dengan bunyi saat pesanan baru masuk. Kasir tetap berjalan walau dapur belum menandai selesai.' : 'Tersedia di paket Pro.'}>
                <Note msg={rowMsg.kitchen} />{!isPro && <span className="st-pill pro">Pro</span>}
                <Switch on={quick.kitchen_mode === 'display'} label="Layar dapur" disabled={!isPro || busyKey === 'kitchen'} onChange={v => quickSave('kitchen', { kitchen_mode: v ? 'display' : 'off' }, v ? 'Aktif. Masuk di aplikasi Dapur.' : 'Nonaktif')} />
              </Row>
            </div>
            <p className="st-cap" style={{ textAlign: 'left' }}>Sesi kas yang tertinggal ditutup sistem pukul 04.00, apa pun modenya.</p>
          </div>
        </section>}

        {section === 'online' && <section className="st-section">
          <div className="st-head"><h1>Pesanan online dan antar</h1><p>Pesanan dari halaman toko, ongkir, kurir, dan kabar WhatsApp ke pelanggan.</p></div>
          <div className="st-group"><h2>Menerima pesanan</h2>
            <div className="st-list">
              <Row title="Terima pesanan online" hint="Matikan saat tidak ada yang menjaga kasir. Menu tetap bisa dilihat, tombol pesan dinonaktifkan.">
                <Note msg={rowMsg.online} /><Switch on={quick.online_orders_enabled} label="Terima pesanan online" disabled={busyKey === 'online'} onChange={v => quickSave('online', { online_orders_enabled: v }, v ? 'Pesanan online dibuka' : 'Pesanan online dihentikan sementara')} />
              </Row>
              <Row title="Batal otomatis kalau tidak dikonfirmasi" hint="Pembayaran QRIS dikembalikan ke pelanggan.">
                <Note msg={rowMsg.cancel} /><Seg label="Batas konfirmasi" value={quick.online_auto_cancel_minutes} disabled={busyKey === 'cancel'} options={[[5, '5'], [10, '10'], [15, '15'], [20, '20'], [30, '30 menit']]} onChange={v => quickSave('cancel', { online_auto_cancel_minutes: v })} />
              </Row>
              <Row title="Kabari saya lewat WhatsApp" hint="Cadangan kalau aplikasi kasir tertutup. Dikirim ke nomor WhatsApp toko.">
                <Note msg={rowMsg.notify} /><Switch on={quick.online_notify_owner_wa} label="Kabar WhatsApp ke pemilik" disabled={busyKey === 'notify'} onChange={v => quickSave('notify', { online_notify_owner_wa: v })} />
              </Row>
            </div>
          </div>
          <div className="st-group"><h2>Antar</h2>
            <div className="st-embed"><DeliveryHoursSettings key={`delivery-${outlet?.id}`} part="delivery" outlet={outlet} onSaved={patch => setOutlet((o: any) => ({ ...o, ...patch }))} /></div>
            <div className="st-embed"><CourierSettings key={`courier-${outlet?.id}`} outletId={outlet?.id} /></div>
          </div>
          <div className="st-group"><h2>Kabar ke pelanggan</h2>
            <WhatsAppToko key={`wa-${outlet?.id}`} outletId={outlet?.id} connected={!!quick.wa_connected} onChanged={v => setQuick(q => ({ ...q, wa_connected: v }))} />
          </div>
        </section>}

        {section === 'stok' && <section className="st-section">
          <div className="st-head"><h1>Stok</h1><p>Jarang diubah. Mengganti cara hitung stok memengaruhi kasir dan laporan.</p></div>
          {!isPro ? <div className="st-list"><Row title="Stok per produk" hint="Stok berkurang per menu yang terjual. Hitung dari resep dan bahan baku tersedia di paket Pro."><span className="st-pill on">Dipakai</span></Row></div>
          : <div className="st-group"><h2>Cara menghitung stok</h2>
            <div className="st-list">
              {([['simple', 'Per produk', 'Stok berkurang per menu yang terjual. Paling sederhana.'], ['recipe', 'Dari resep dan bahan baku', 'Stok bahan berkurang mengikuti resep, modal (HPP) terhitung otomatis. Semua menu harus punya resep dulu.']] as const).map(([m, title, hint]) =>
                <Row key={m} title={title} hint={hint}>{quick.stock_mode === m ? <span className="st-pill on">Dipakai</span> : <button type="button" className="st-btn" disabled={busyKey === 'stock'} onClick={() => setStockConfirm(m)}>Pakai cara ini</button>}</Row>)}
            </div>
            {stockMsg && <p className={`st-msg ${stockMsg.ok ? 'ok' : 'err'}`} role="status">{stockMsg.text}{stockMsg.recipes && <> Lengkapi resep di <Link className="underline" href="/dashboard/hpp">Atur HPP</Link> atau <Link className="underline" href="/dashboard/bahan-baku">Bahan Baku</Link>, lalu coba lagi.</>}</p>}
            <div className="st-list"><Row title="Siapkan resep dulu" hint="Mode resep ditolak kalau ada menu yang belum punya resep."><Link className="st-btn" href="/dashboard/hpp">Buka Atur HPP</Link></Row></div>
          </div>}
        </section>}

        {section === 'langganan' && <section className="st-section">
          <div className="st-head"><h1>Langganan</h1><p>Paket, pembayaran otomatis, dan program ajak usaha lain.</p></div>
          <div className="st-group"><h2>Paket</h2>
            <div className="st-list">
              <Row title={`Paket ${tier.charAt(0).toUpperCase()}${tier.slice(1)}`} hint="Lihat tagihan, ganti paket, atau bayar langganan."><Link className="st-btn primary" href="/dashboard/settings/billing">Kelola langganan</Link></Row>
              <Row title="QRIS otomatis lewat Xendit" hint="Pembayaran QRIS lunas terkonfirmasi tanpa cek notifikasi.">{quick.qris_channel === 'xendit' ? <span className="st-pill on">Tersambung</span> : <span className="st-pill">Belum</span>}<Link className="st-btn" href="/dashboard/settings/payment">Atur</Link></Row>
            </div>
          </div>
          {referral && <div className="st-group"><h2>Ajak usaha lain</h2>
            <div className="st-list">
              <Row title={`Kode ${referral.code}`} hint="Anda mendapat 20% dari langganan usaha yang bergabung lewat kode ini, setiap bulan.">
                <button type="button" className="st-btn" onClick={() => copy('ref', referral.url)}>{copied === 'ref' ? 'Tersalin' : 'Salin tautan'}</button>
                <a className="st-btn" href={`https://wa.me/?text=${encodeURIComponent(referral.text)}`} target="_blank" rel="noopener noreferrer">Kirim lewat WhatsApp</a>
              </Row>
              {referral.stats && <Row title={`${referral.stats.total_referrals || 0} usaha bergabung`} hint={`Komisi menunggu ${rp(referral.stats.pending_balance || 0)}, sudah dicairkan ${rp(referral.stats.total_earned || 0)}.`} />}
              {(referral.stats?.referrals || []).map((r: any) => <Row key={r.id} title={r.referred_name} hint={`Paket ${r.referred_tier}`}>{rp(r.total_commission || 0)}</Row>)}
            </div>
          </div>}
        </section>}

        {(dirty.length > 0 || saveMsg) && <div className="st-savebar" role="region" aria-label="Simpan perubahan">
          <span>{dirty.length ? `Ada perubahan ${dirty.join(', ')} yang belum disimpan.` : saveMsg?.text}{dirty.length > 0 && saveMsg && !saveMsg.ok ? ` ${saveMsg.text}` : ''}</span>
          {dirty.length > 0 ? <span className="flex gap-2"><button type="button" className="st-btn" disabled={saving} onClick={undo}>Batalkan</button><button type="button" className="st-btn primary" disabled={saving} onClick={saveAll}>{saving ? 'Menyimpan…' : 'Simpan perubahan'}</button></span>
            : <button type="button" className="st-btn" onClick={() => setSaveMsg(null)}>Tutup</button>}
        </div>}
      </main>
    </div>

    {stockConfirm && <div className="st-modal" role="dialog" aria-modal="true" aria-labelledby="st-stock-title"><div>
      <h3 id="st-stock-title">{stockConfirm === 'recipe' ? 'Hitung stok dari resep?' : 'Kembali ke stok per produk?'}</h3>
      {stockConfirm === 'recipe' ? <ul><li>Stok dihitung dari bahan baku, bukan per produk.</li><li>Setiap menu perlu resep. Kalau ada yang belum, peralihan ditolak.</li><li>Catat stok fisik bahan sebelum mulai berjualan.</li></ul>
        : <ul><li>Stok kembali dihitung per produk.</li><li>Resep dan bahan tetap tersimpan, tapi tidak mengurangi stok.</li></ul>}
      <div className="flex gap-2 justify-end"><button type="button" className="st-btn" onClick={() => setStockConfirm(null)}>Batal</button><button type="button" className="st-btn primary" onClick={changeStockMode}>Ganti cara hitung</button></div>
    </div></div>}
  </div>;
}

function Receipt({ name, address, tax }: { name: string; address: string; tax: Tax }) {
  const items: [string, number, number][] = [['Es Kopi Susu', 2, 22000], ['Croissant', 1, 26000]];
  const sub = items.reduce((a, [, q, p]) => a + q * p, 0);
  const svc = tax.service_charge_enabled ? sub * tax.service_charge_pct / 100 : 0;
  const pb1 = tax.pb1_enabled ? (tax.tax_inclusive ? sub - sub / (1 + tax.tax_pct / 100) : sub * tax.tax_pct / 100) : 0;
  const total = sub + svc + (tax.pb1_enabled && !tax.tax_inclusive ? pb1 : 0);
  return <div className="st-receipt" aria-label="Pratinjau struk">
    <div className="c big">{(name || 'Nama toko').toUpperCase()}</div>
    {address && <div className="c">{address}</div>}
    {tax.tax_number.trim() && <div className="c">NPWP {tax.tax_number.trim()}</div>}
    <hr />
    {items.map(([n, q, p]) => <div key={n}><div>{n}</div><div className="r"><span>{q} x {rp(p)}</span><span>{rp(q * p)}</span></div></div>)}
    <hr />
    <div className="r"><span>Subtotal</span><span>{rp(sub)}</span></div>
    {svc > 0 && <div className="r"><span>Service {tax.service_charge_pct}%</span><span>{rp(svc)}</span></div>}
    {tax.pb1_enabled && <div className="r"><span>PB1 {tax.tax_pct}%{tax.tax_inclusive ? ' (termasuk)' : ''}</span><span>{rp(pb1)}</span></div>}
    <div className="r big"><span>TOTAL</span><span>{rp(total)}</span></div>
    <hr />
    <div className="c">{tax.receipt_footer.trim() || 'Powered by Selaris'}</div>
  </div>;
}

/** Nomor WhatsApp toko sendiri lewat Fonnte. Token dicek ke Fonnte saat disimpan. */
function WhatsAppToko({ outletId, connected, onChanged }: { outletId?: string; connected: boolean; onChanged: (v: boolean) => void }) {
  const [token, setToken] = useState(''), [busy, setBusy] = useState(false), [msg, setMsg] = useState<Msg>(null);
  const [open, setOpen] = useState(false), [confirmOff, setConfirmOff] = useState(false);
  const save = async (value: string) => {
    if (!outletId) return;
    setBusy(true); setMsg(null);
    try { const r = await setupOutletWhatsApp(outletId, value); onChanged(r.connected); setToken(''); setOpen(false); setConfirmOff(false); setMsg({ ok: true, text: r.message }); }
    catch (e: any) { setMsg({ ok: false, text: e.message }); }
    finally { setBusy(false); }
  };
  return <div className="st-list">
    <Row title="Kirim dari nomor WhatsApp toko sendiri" hint={<>Opsional. Tanpa ini, kabar pesanan dikirim dari nomor Selaris. Daftar di <a className="underline" href="https://fonnte.com" target="_blank" rel="noopener noreferrer">fonnte.com</a>, sambungkan nomor toko, lalu tempel tokennya di sini.</>}>
      <span className={`st-pill ${connected ? 'on' : ''}`}>{connected ? 'Tersambung' : 'Belum tersambung'}</span>
    </Row>
    {(open || !connected) && <Row block><div className="flex gap-2">
      <input className="st-input" type="password" aria-label="Token Fonnte" placeholder="Tempel token Fonnte" value={token} onChange={e => setToken(e.target.value)} />
      <button type="button" className="st-btn primary" disabled={busy || !token.trim()} onClick={() => save(token.trim())}>{busy ? 'Mengecek…' : 'Sambungkan'}</button>
    </div></Row>}
    {connected && !open && <Row block><div className="flex flex-wrap gap-2 items-center">
      <button type="button" className="st-btn" onClick={() => setOpen(true)}>Ganti token</button>
      {confirmOff ? <><span className="text-sm">Kabar pesanan akan dikirim dari nomor Selaris.</span><button type="button" className="st-btn danger" disabled={busy} onClick={() => save('')}>Ya, putuskan</button><button type="button" className="st-btn" onClick={() => setConfirmOff(false)}>Batal</button></>
        : <button type="button" className="st-btn danger" onClick={() => setConfirmOff(true)}>Putuskan</button>}
    </div></Row>}
    {msg && <Row block><Note msg={msg} /></Row>}
  </div>;
}
