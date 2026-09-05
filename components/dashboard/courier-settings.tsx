'use client';

import { useEffect, useState } from 'react';
import { Bike, Loader2, Plus, Trash2, Check, X } from 'lucide-react';
import { getCouriers, createCourier, updateCourier, deleteCourier } from '@/app/actions/api';

/**
 * Daftar kurir toko (delivery gelombang 2, 5 Sep 2026).
 *
 * Kurir di Selaris itu ORANG TOKO: anak pemilik, karyawan, atau pemiliknya
 * sendiri. Bukan armada agregator, jadi nggak ada akun kurir, nggak ada
 * aplikasi kurir, nggak ada bagi hasil. Toko cuma nyatet siapa saja yang
 * biasa nganter, kasir tinggal pilih waktu menyerahkan pesanan, dan
 * pelanggan lihat nama plus nomornya di halaman lacak. Nomor WA-nya yang
 * bikin ini berguna: pelanggan bisa nanya langsung waktu alamatnya susah.
 */
const VEHICLES: { key: string; label: string }[] = [
  { key: 'motor', label: 'Motor' },
  { key: 'mobil', label: 'Mobil' },
  { key: 'sepeda', label: 'Sepeda' },
  { key: 'jalan_kaki', label: 'Jalan kaki' },
];

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm';

export function CourierSettings({ outletId }: { outletId?: string }) {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [vehicle, setVehicle] = useState('motor');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function load() {
    setLoading(true);
    setRows(await getCouriers(outletId, true));
    setLoading(false);
  }

  useEffect(() => {
    if (outletId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [outletId]);

  async function onAdd() {
    if (!name.trim()) return;
    setBusy(true);
    const res = await createCourier({ name: name.trim(), phone: phone.trim() || null, vehicle, outlet_id: outletId || null });
    setBusy(false);
    if (!res.success) { setMsg({ ok: false, text: res.message || 'Gagal menambah kurir' }); return; }
    setName(''); setPhone(''); setVehicle('motor'); setAdding(false);
    setMsg({ ok: true, text: 'Kurir ditambahkan' });
    load();
  }

  async function onToggle(c: any) {
    const res = await updateCourier(c.id, { is_active: !c.is_active, row_version: c.row_version });
    if (!res.success) { setMsg({ ok: false, text: res.message || 'Gagal menyimpan' }); return; }
    load();
  }

  async function onDelete(c: any) {
    if (!confirm(`Hapus ${c.name} dari daftar kurir? Pesanan lama tetap mencatat namanya.`)) return;
    const res = await deleteCourier(c.id);
    if (!res.success) { setMsg({ ok: false, text: res.message || 'Gagal menghapus' }); return; }
    load();
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
        <Bike className="w-5 h-5 text-gray-500" />
        <h2 className="text-lg font-bold text-gray-900">Kurir Toko</h2>
      </div>

      <div className="p-6 space-y-4">
        <p className="text-sm text-gray-600">
          Daftarkan orang yang biasa mengantar pesanan. Kasir tinggal memilih namanya saat menyerahkan
          pesanan, dan pelanggan melihat siapa yang mengantar beserta nomornya di halaman pesanan.
        </p>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500"><Loader2 className="w-4 h-4 animate-spin" /> Memuat</div>
        ) : rows.length === 0 && !adding ? (
          <div className="rounded-lg border border-dashed border-gray-300 px-4 py-6 text-center">
            <p className="text-sm text-gray-500">Belum ada kurir terdaftar.</p>
            <p className="mt-1 text-xs text-gray-400">Tanpa daftar pun kasir tetap bisa mengetik nama pengantar sekali jalan.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {rows.map((c) => (
              <div key={c.id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className={`font-semibold ${c.is_active ? 'text-gray-900' : 'text-gray-400'}`}>{c.name}</p>
                  <p className="text-xs text-gray-500">
                    {VEHICLES.find((v) => v.key === c.vehicle)?.label || c.vehicle}
                    {c.phone ? ` · ${c.phone}` : ' · nomor belum diisi'}
                    {c.is_active ? '' : ' · tidak aktif'}
                  </p>
                </div>
                <button
                  onClick={() => onToggle(c)}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
                >
                  {c.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                </button>
                <button onClick={() => onDelete(c)} className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600" aria-label="Hapus">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {adding ? (
          <div className="space-y-3 rounded-lg border border-gray-200 p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Nama</label>
                <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Budi" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Nomor WhatsApp</label>
                <input className={inputCls} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="0812xxxxxxx" inputMode="numeric" />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Kendaraan</label>
              <div className="flex flex-wrap gap-2">
                {VEHICLES.map((v) => (
                  <button
                    key={v.key}
                    onClick={() => setVehicle(v.key)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${vehicle === v.key ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}
                  >
                    {v.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={onAdd}
                disabled={busy || !name.trim()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Simpan
              </button>
              <button
                onClick={() => { setAdding(false); setName(''); setPhone(''); }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
              >
                <X className="h-4 w-4" /> Batal
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => { setAdding(true); setMsg(null); }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Plus className="h-4 w-4" /> Tambah kurir
          </button>
        )}

        {msg && (
          <p className={`text-sm ${msg.ok ? 'text-green-700' : 'text-red-600'}`}>{msg.text}</p>
        )}
      </div>
    </div>
  );
}
