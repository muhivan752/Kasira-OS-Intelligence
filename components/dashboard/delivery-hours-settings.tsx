'use client';

import { useEffect, useRef, useState } from 'react';
import { Bike, Clock, Loader2, Check, MapPin, Search } from 'lucide-react';
import { updateOutlet, setOutletLocation } from '@/app/actions/api';
import { geoAutocomplete, geoPlace } from '@/app/actions/storefront';

/**
 * Pengaturan antar + jam buka (delivery gelombang 1, 4 Sep 2026).
 *
 * Dua kartu, disimpan lewat tombol Simpan masing masing (bukan per ketukan,
 * karena angka tarif diketik). Rumus ongkir hidup di server
 * (services/delivery_service): base + per km di atas km gratis, dibulatkan
 * ke atas ke Rp 500. Jadwal: 7 hari, satu rentang per hari (rentang kedua
 * belum ada di UI, servernya sudah dukung). Tutup < buka = lewat tengah malam.
 */
const DAYS: { key: string; label: string }[] = [
  { key: 'mon', label: 'Senin' }, { key: 'tue', label: 'Selasa' }, { key: 'wed', label: 'Rabu' },
  { key: 'thu', label: 'Kamis' }, { key: 'fri', label: 'Jumat' }, { key: 'sat', label: 'Sabtu' }, { key: 'sun', label: 'Minggu' },
];
type Hours = Record<string, [string, string][]>;

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm';

function rp(n: number) { return 'Rp ' + Math.round(n || 0).toLocaleString('id-ID'); }
function contohOngkir(base: number, perKm: number, freeKm: number, km: number) {
  const extra = Math.max(0, km - freeKm);
  const fee = base + (perKm > 0 && extra > 0 ? perKm * Math.ceil(extra - 1e-9) : 0);
  return fee <= 0 ? 0 : Math.ceil(fee / 500) * 500;
}

export function DeliveryHoursSettings({ outlet, onSaved }: { outlet: any; onSaved?: (patch: any) => void }) {
  // ── Antar ──
  const [enabled, setEnabled] = useState(true);
  const [cod, setCod] = useState(true);
  const [base, setBase] = useState('0');
  const [perKm, setPerKm] = useState('0');
  const [freeKm, setFreeKm] = useState('0');
  const [minOrder, setMinOrder] = useState('0');
  const [radius, setRadius] = useState('5');
  const [dSaving, setDSaving] = useState(false);
  const [dMsg, setDMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // ── Titik lokasi toko ──
  // Dulu cuma bisa dari GPS app kasir, dan GPS nyetel titik di mana HP-nya
  // berada (rumah pemilik), bukan tokonya. Di sini pemilik cari alamat lewat
  // Google Places (proxy backend, kunci nggak ke browser) lalu simpan.
  const [pin, setPin] = useState<{ lat: number; lng: number } | null>(null);
  const [pinQ, setPinQ] = useState('');
  const [pinSug, setPinSug] = useState<any[]>([]);
  const [pinPick, setPinPick] = useState<{ lat: number; lng: number; address: string } | null>(null);
  const [pinBusy, setPinBusy] = useState(false);
  const [pinMsg, setPinMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const pinSession = useRef(`dash-${Date.now()}`);

  // ── Jam buka ──
  const [mode, setMode] = useState<'manual' | 'schedule'>('manual');
  const [hours, setHours] = useState<Record<string, { open: string; close: string; closed: boolean }>>({});
  const [hSaving, setHSaving] = useState(false);
  const [hMsg, setHMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const initFor = useRef<string | null>(null);
  useEffect(() => {
    if (!outlet || initFor.current === outlet.id) return;
    initFor.current = outlet.id;
    setEnabled(outlet.delivery_enabled !== false);
    setCod(outlet.delivery_cod_enabled !== false);
    setBase(String(Math.round(outlet.delivery_fee_base || 0)));
    setPerKm(String(Math.round(outlet.delivery_fee_per_km || 0)));
    setFreeKm(String(outlet.delivery_free_km || 0));
    setMinOrder(String(Math.round(outlet.delivery_min_order || 0)));
    setRadius(String(outlet.delivery_radius_km ?? 5));
    setPin(outlet.latitude != null && outlet.longitude != null ? { lat: Number(outlet.latitude), lng: Number(outlet.longitude) } : null);
    setMode(outlet.hours_mode === 'schedule' ? 'schedule' : 'manual');
    const h: Hours | null = outlet.business_hours && typeof outlet.business_hours === 'object' ? outlet.business_hours : null;
    const next: typeof hours = {};
    for (const d of DAYS) {
      const r = h?.[d.key]?.[0];
      next[d.key] = r ? { open: r[0], close: r[1], closed: false } : { open: '08:00', close: '22:00', closed: !!h };
    }
    setHours(next);
  }, [outlet]);

  const num = (s: string) => Math.max(0, Number(String(s).replace(/[^\d.]/g, '')) || 0);

  const saveDelivery = async () => {
    if (!outlet) return;
    setDSaving(true); setDMsg(null);
    const patch = {
      delivery_enabled: enabled,
      delivery_cod_enabled: cod,
      delivery_fee_base: num(base),
      delivery_fee_per_km: num(perKm),
      delivery_free_km: num(freeKm),
      delivery_min_order: num(minOrder),
      delivery_radius_km: num(radius),
    };
    const res = await updateOutlet(outlet.id, patch);
    setDSaving(false);
    if (res?.success) { setDMsg({ ok: true, text: 'Tersimpan. Halaman toko mengikuti dalam 1 menit.' }); onSaved?.(patch); }
    else setDMsg({ ok: false, text: res?.message || 'Gagal menyimpan' });
  };

  const saveHours = async () => {
    if (!outlet) return;
    setHSaving(true); setHMsg(null);
    const bh: Hours = {};
    for (const d of DAYS) {
      const v = hours[d.key];
      bh[d.key] = !v || v.closed ? [] : [[v.open, v.close]];
    }
    const patch = { hours_mode: mode, business_hours: mode === 'schedule' ? bh : outlet.business_hours ?? null };
    const res = await updateOutlet(outlet.id, patch);
    setHSaving(false);
    if (res?.success) { setHMsg({ ok: true, text: mode === 'schedule' ? 'Tersimpan. Toko buka dan tutup sendiri mengikuti jadwal.' : 'Tersimpan. Buka tutup diatur manual dari saklar Status Operasional.' }); onSaved?.(patch); }
    else setHMsg({ ok: false, text: res?.message || 'Gagal menyimpan' });
  };

  useEffect(() => {
    if (!outlet?.slug || pinQ.trim().length < 3 || pinPick) { setPinSug([]); return; }
    const t = setTimeout(async () => {
      const r = await geoAutocomplete(outlet.slug, pinQ, pinSession.current);
      setPinSug(Array.isArray(r) ? r.slice(0, 5) : []);
    }, 350);
    return () => clearTimeout(t);
  }, [pinQ, pinPick, outlet?.slug]);

  const pickPlace = async (placeId: string) => {
    setPinBusy(true); setPinMsg(null);
    const r = await geoPlace(outlet.slug, { place_id: placeId, session: pinSession.current });
    setPinBusy(false);
    pinSession.current = `dash-${Date.now()}`;
    if (r?.success && r.data?.lat != null) { setPinPick({ lat: r.data.lat, lng: r.data.lng, address: r.data.address || pinQ }); setPinSug([]); }
    else setPinMsg({ ok: false, text: r?.message || 'Alamat tidak ditemukan' });
  };

  const pakaiAlamatToko = async () => {
    if (!outlet?.address) { setPinMsg({ ok: false, text: 'Isi alamat toko dulu di kartu Informasi Toko.' }); return; }
    setPinBusy(true); setPinMsg(null);
    const r = await geoAutocomplete(outlet.slug, outlet.address, pinSession.current);
    if (!Array.isArray(r) || r.length === 0) { setPinBusy(false); setPinMsg({ ok: false, text: 'Alamat toko tidak ketemu di peta. Cari manual di bawah.' }); return; }
    setPinQ(r[0].description || outlet.address);
    await pickPlace(r[0].place_id);
  };

  const savePin = async () => {
    if (!outlet || !pinPick) return;
    setPinBusy(true); setPinMsg(null);
    const res = await setOutletLocation(outlet.id, pinPick.lat, pinPick.lng);
    setPinBusy(false);
    if (res?.success) {
      setPin({ lat: pinPick.lat, lng: pinPick.lng });
      setPinPick(null); setPinQ('');
      setPinMsg({ ok: true, text: 'Titik toko tersimpan. Jarak antar dan Google membaca titik ini.' });
      onSaved?.({ latitude: pinPick.lat, longitude: pinPick.lng });
    } else setPinMsg({ ok: false, text: res?.message || 'Gagal menyimpan' });
  };

  const applyAll = () => {
    const first = hours[DAYS[0].key] || { open: '08:00', close: '22:00', closed: false };
    const next: typeof hours = {};
    for (const d of DAYS) next[d.key] = { ...first };
    setHours(next);
  };

  const b = num(base), p = num(perKm), f = num(freeKm);

  return (
    <>
      {/* ── Antar ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bike className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-bold text-gray-900">Antar dan Ongkir</h2>
          </div>
          <button type="button" onClick={() => setEnabled(v => !v)} role="switch" aria-checked={enabled}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enabled ? 'bg-blue-600' : 'bg-gray-200'}`}>
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${enabled ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-gray-600">Ongkir dihitung dari jarak alamat pelanggan ke toko, ditagih terpisah dari harga menu, dan tidak masuk laporan penjualan.</p>

          <div className="rounded-lg border border-gray-200 p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-gray-900 flex items-center gap-1.5"><MapPin className="w-4 h-4 text-gray-500" /> Titik lokasi toko</p>
                <p className="text-xs text-gray-500 mt-0.5">Semua jarak antar dihitung dari titik ini. Pastikan pin ada di tokonya, bukan di rumah atau posisi HP saat login.</p>
              </div>
              <button type="button" onClick={pakaiAlamatToko} disabled={pinBusy} className="shrink-0 text-xs font-semibold text-blue-600 hover:underline disabled:opacity-50">Pakai alamat toko</button>
            </div>
            {(pinPick || pin) && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`/api/v1/connect/geo/static?lat=${(pinPick || pin)!.lat}&lng=${(pinPick || pin)!.lng}&zoom=16&w=640&h=200`} alt="Peta titik toko" className="w-full h-40 object-cover rounded-lg border border-gray-200 bg-gray-50" />
            )}
            {!pin && !pinPick && <p className="text-xs text-amber-600">Titik belum diatur. Tanpa titik, ongkir per km tidak bisa dihitung dan jangkauan tidak ditegakkan.</p>}
            <div className="relative">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-gray-400 shrink-0" />
                <input value={pinQ} onChange={e => { setPinQ(e.target.value); setPinPick(null); }} placeholder="Cari nama tempat atau alamat toko" className={inputCls} />
              </div>
              {pinSug.length > 0 && (
                <ul className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden">
                  {pinSug.map((sg: any) => (
                    <li key={sg.place_id}>
                      <button type="button" onClick={() => { setPinQ(sg.description); pickPlace(sg.place_id); }} className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">{sg.description}</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {pinPick && (
              <div className="flex items-center justify-between gap-3 rounded-lg bg-blue-50 px-3 py-2">
                <p className="text-xs text-blue-800 truncate">{pinPick.address}</p>
                <button type="button" onClick={savePin} disabled={pinBusy} className="shrink-0 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-60 inline-flex items-center gap-1">
                  {pinBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Simpan titik
                </button>
              </div>
            )}
            {pinMsg && <p className={`text-xs ${pinMsg.ok ? 'text-green-600' : 'text-red-600'}`}>{pinMsg.text}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ongkir dasar (Rp)</label>
              <input inputMode="numeric" value={base} onChange={e => setBase(e.target.value)} className={inputCls} placeholder="5000" />
              <p className="text-xs text-gray-400 mt-1">Dikenakan untuk semua pesanan antar. Isi 0 kalau gratis.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tambahan per km (Rp)</label>
              <input inputMode="numeric" value={perKm} onChange={e => setPerKm(e.target.value)} className={inputCls} placeholder="2000" />
              <p className="text-xs text-gray-400 mt-1">Dihitung per km di atas km gratis, dibulatkan ke atas.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Km gratis</label>
              <input inputMode="decimal" value={freeKm} onChange={e => setFreeKm(e.target.value)} className={inputCls} placeholder="2" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Jangkauan antar (km)</label>
              <input inputMode="decimal" value={radius} onChange={e => setRadius(e.target.value)} className={inputCls} placeholder="5" />
              <p className="text-xs text-gray-400 mt-1">Alamat di luar ini ditolak. Butuh titik lokasi toko.</p>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Minimal pesanan untuk antar (Rp)</label>
              <input inputMode="numeric" value={minOrder} onChange={e => setMinOrder(e.target.value)} className={inputCls} placeholder="20000" />
            </div>
          </div>
          <div className="flex items-start justify-between gap-4 rounded-lg border border-gray-200 p-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Terima bayar di tempat (COD)</p>
              <p className="text-xs text-gray-500 mt-0.5">Pelanggan boleh bayar tunai ke kurir saat pesanan sampai. Matikan kalau mau semua pesanan antar dibayar dulu lewat QRIS atau transfer.</p>
            </div>
            <button type="button" onClick={() => setCod(v => !v)} role="switch" aria-checked={cod}
              className={`relative mt-0.5 inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors ${cod ? 'bg-blue-600' : 'bg-gray-200'}`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${cod ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
          <div className="rounded-lg bg-gray-50 px-4 py-3 text-xs text-gray-600">
            Contoh dengan angka di atas: 1 km {rp(contohOngkir(b, p, f, 1))}, 3 km {rp(contohOngkir(b, p, f, 3))}, 5 km {rp(contohOngkir(b, p, f, 5))}.
            Ongkir selalu dibulatkan ke atas ke kelipatan Rp 500.
          </div>
          <div className="flex items-center justify-between">
            <span className={`text-sm ${dMsg ? (dMsg.ok ? 'text-green-600' : 'text-red-600') : 'text-transparent'}`}>{dMsg?.text || '.'}</span>
            <button type="button" onClick={saveDelivery} disabled={dSaving} className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-60 inline-flex items-center gap-2">
              {dSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Simpan tarif
            </button>
          </div>
        </div>
      </div>

      {/* ── Jam buka ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-bold text-gray-900">Jam Buka</h2>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-2">
            {(['manual', 'schedule'] as const).map(m => (
              <button key={m} type="button" onClick={() => setMode(m)}
                className={`rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ${mode === m ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'}`}>
                <p className="font-semibold">{m === 'manual' ? 'Manual' : 'Ikut jadwal'}</p>
                <p className="text-xs opacity-80">{m === 'manual' ? 'Buka tutup dari saklar Status Operasional.' : 'Toko buka dan tutup sendiri tiap hari. Saklar tetap bisa menutup mendadak.'}</p>
              </button>
            ))}
          </div>
          {mode === 'schedule' && (
            <div className="space-y-2">
              <div className="flex justify-end">
                <button type="button" onClick={applyAll} className="text-xs font-semibold text-blue-600 hover:underline">Samakan semua hari dengan Senin</button>
              </div>
              {DAYS.map(d => {
                const v = hours[d.key] || { open: '08:00', close: '22:00', closed: false };
                const set = (patch: Partial<typeof v>) => setHours(h => ({ ...h, [d.key]: { ...v, ...patch } }));
                return (
                  <div key={d.key} className="flex items-center gap-3">
                    <span className="w-16 text-sm text-gray-700">{d.label}</span>
                    <input type="time" value={v.open} disabled={v.closed} onChange={e => set({ open: e.target.value })} className={`${inputCls} w-28 disabled:opacity-40`} />
                    <span className="text-xs text-gray-400">sampai</span>
                    <input type="time" value={v.close} disabled={v.closed} onChange={e => set({ close: e.target.value })} className={`${inputCls} w-28 disabled:opacity-40`} />
                    <label className="ml-auto inline-flex items-center gap-1.5 text-xs text-gray-600">
                      <input type="checkbox" checked={v.closed} onChange={e => set({ closed: e.target.checked })} /> Tutup
                    </label>
                  </div>
                );
              })}
              <p className="text-xs text-gray-400">Jam tutup lebih kecil dari jam buka berarti lewat tengah malam (misal 18:00 sampai 02:00).</p>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className={`text-sm ${hMsg ? (hMsg.ok ? 'text-green-600' : 'text-red-600') : 'text-transparent'}`}>{hMsg?.text || '.'}</span>
            <button type="button" onClick={saveHours} disabled={hSaving} className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-60 inline-flex items-center gap-2">
              {hSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Simpan jam buka
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
