'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getOutlets, getCurrentShift, getUncountedShifts, countShift } from '@/app/actions/api';
import { Users } from 'lucide-react';

export default function KasirPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState<string>('');

  // Sesi kas (shift otomatis, gelombang 2)
  const [shift, setShift] = useState<any>(null);
  const [uncounted, setUncounted] = useState<any[]>([]);
  const [counting, setCounting] = useState<any>(null);
  const [countValue, setCountValue] = useState('');
  const [countSaving, setCountSaving] = useState(false);

  async function loadShift(id: string) {
    const [cur, unc] = await Promise.all([getCurrentShift(id), getUncountedShifts(id)]);
    // Tanpa sesi server tetap kirim { status: null, shift_mode } — bukan sesi.
    setShift(cur && cur.id ? cur : null);
    setUncounted(unc || []);
  }

  const rp = (n: any) => n == null ? '-' : 'Rp ' + Math.round(Number(n)).toLocaleString('id-ID');
  const tgl = (iso?: string | null) => iso ? new Date(iso).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-';

  const submitCount = async () => {
    if (!counting) return;
    const val = Number(countValue);
    if (!Number.isFinite(val) || val < 0) return;
    setCountSaving(true);
    try {
      await countShift(counting.id, val);
      setCounting(null);
      setCountValue('');
      if (outletId) await loadShift(outletId);
    } catch (e: any) {
      alert(e?.message || 'Gagal mencatat hitungan');
    } finally {
      setCountSaving(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const id = outlets[0].id;
        setOutletId(id);
        await loadShift(id);
      }
    } catch (error) {
      console.error('Failed to load cash sessions', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Memuat...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Kas harian</h1>
        <p className="text-gray-500">Uang di laci kasir. Sesi terbuka sendiri di transaksi pertama dan ditutup sistem jam 04.00.</p>
      </div>

      {/* Sesi kas. Terbuka sendiri di transaksi pertama, tutup sendiri 04.00.
          Pemilik lihat semua angka; kasir di mode Standar menghitung tanpa
          melihat angka harapan, jadi selisihnya cuma kelihatan di sini. */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-gray-900">Sesi kas sekarang</h2>
            {shift && <span className="rounded-full bg-green-50 px-2.5 py-1 text-xs font-semibold text-green-700">Berjalan</span>}
          </div>
          {!shift ? (
            <p className="mt-3 text-sm text-gray-500">Belum ada sesi berjalan. Sesi terbuka sendiri di transaksi pertama.</p>
          ) : (
            <div className="mt-3 space-y-2 text-sm">
              <p className="text-gray-600">Dibuka {tgl(shift.start_time)}{shift.opened_by_name ? ` oleh ${shift.opened_by_name}` : ''}{shift.opened_by === 'auto' ? ' (otomatis)' : ''}</p>
              {shift.locked_to_name && (
                <p className="text-amber-700">Laci terkunci ke {shift.locked_to_name} (mode Ketat)</p>
              )}
              <div className="rounded-lg bg-gray-50 p-3">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Isi laci menurut sistem</p>
                <dl className="mt-2 space-y-1">
                  <div className="flex justify-between"><dt className="text-gray-600">Modal awal</dt><dd className="text-gray-900">{rp(shift.starting_cash)}</dd></div>
                  <div className="flex justify-between"><dt className="text-gray-600">Tunai diterima</dt><dd className="text-gray-900">+ {rp(shift.total_cash_sales)}</dd></div>
                  {Number(shift.cash_refunds) > 0 && (
                    <div className="flex justify-between"><dt className="text-gray-600">Refund tunai</dt><dd className="text-gray-900">− {rp(shift.cash_refunds)}</dd></div>
                  )}
                  {Number(shift.cash_income) > 0 && (
                    <div className="flex justify-between"><dt className="text-gray-600">Kas masuk lain</dt><dd className="text-gray-900">+ {rp(shift.cash_income)}</dd></div>
                  )}
                  {Number(shift.cash_expense) > 0 && (
                    <div className="flex justify-between"><dt className="text-gray-600">Kas keluar</dt><dd className="text-gray-900">− {rp(shift.cash_expense)}</dd></div>
                  )}
                  <div className="flex justify-between border-t border-gray-200 pt-1 font-semibold"><dt className="text-gray-900">Perkiraan isi laci</dt><dd className="text-gray-900">{rp(shift.expected_ending_cash)}</dd></div>
                </dl>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">QRIS diterima</p><p className="font-semibold text-gray-900">{rp(shift.total_qris_sales)}</p></div>
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Mode kas</p><p className="font-semibold text-gray-900 capitalize">{shift.shift_mode || 'ringan'}</p></div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h2 className="font-bold text-gray-900">Kas belum dihitung</h2>
          {uncounted.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">Semua sesi 14 hari terakhir sudah dihitung.</p>
          ) : (
            <ul className="mt-3 divide-y divide-gray-100">
              {uncounted.map((u) => (
                <li key={u.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <div>
                    <p className="font-medium text-gray-900">{tgl(u.start_time)}{u.opened_by_name ? ` · ${u.opened_by_name}` : ''}</p>
                    <p className="text-xs text-gray-500">{u.status === 'paused' ? 'Dijeda' : 'Ditutup sistem 04.00'} · perkiraan {rp(u.expected_ending_cash)}</p>
                  </div>
                  <button onClick={() => { setCounting(u); setCountValue(''); }} className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">Catat hitungan</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {shift?.review?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h2 className="font-bold text-gray-900">Rekap per akun</h2>
          <p className="mt-1 text-sm text-gray-500">Pesanan dihitung dari akun yang menginput. Uang dihitung dari akun yang menerima pembayaran. Jumlah tunai bersih semua baris sama dengan tunai diterima dikurangi refund di atas.</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs text-gray-500">
                  <th className="py-2 pr-3 font-medium">Akun</th>
                  <th className="py-2 pr-3 font-medium text-right">Pesanan</th>
                  <th className="py-2 pr-3 font-medium text-right">Tunai bersih</th>
                  <th className="py-2 pr-3 font-medium text-right">QRIS</th>
                  <th className="py-2 font-medium text-right">Lainnya</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {shift.review.map((r: any) => (
                  <tr key={r.user_id || 'none'}>
                    <td className="py-2 pr-3 text-gray-900">{r.name}</td>
                    <td className="py-2 pr-3 text-right text-gray-700">{r.orders}</td>
                    <td className="py-2 pr-3 text-right text-gray-700">
                      {rp(r.cash_net)}
                      {Number(r.cash_refunds) > 0 && <span className="block text-xs text-gray-400">terima {rp(r.cash)}, refund {rp(r.cash_refunds)}</span>}
                    </td>
                    <td className="py-2 pr-3 text-right text-gray-700">{rp(r.qris)}</td>
                    <td className="py-2 text-right text-gray-700">{rp(r.other)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {counting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl">
            <h3 className="font-bold text-gray-900">Hitungan kas sesi {tgl(counting.start_time)}</h3>
            <p className="mt-1 text-sm text-gray-500">Perkiraan sistem {rp(counting.expected_ending_cash)}. Masukkan uang yang benar-benar ada.</p>
            <input type="number" min="0" value={countValue} onChange={(e) => setCountValue(e.target.value)} placeholder="0"
              className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setCounting(null)} className="rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">Batal</button>
              <button onClick={submitCount} disabled={countSaving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{countSaving ? 'Menyimpan…' : 'Simpan'}</button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-start gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm">
        <Users className="mt-0.5 h-5 w-5 shrink-0 text-gray-500" />
        <p className="text-gray-600">
          Akun kasir dan karyawan sekarang diatur di{' '}
          <Link href="/dashboard/hris" className="font-semibold text-blue-600 hover:underline">Tim &amp; absensi</Link>.
          Di sana Anda bisa membuat akun, memberi hak akses, dan menonaktifkan karyawan.
        </p>
      </div>
    </div>
  );
}
