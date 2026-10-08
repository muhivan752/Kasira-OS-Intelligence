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
              {shift.review?.length > 0 && (
                <div className="pt-1">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Rekap per kasir</p>
                  <ul className="mt-1 divide-y divide-gray-100">
                    {shift.review.map((r: any) => (
                      <li key={r.user_id} className="flex items-center justify-between py-1.5">
                        <span className="text-gray-900">{r.name} <span className="text-gray-400">· {r.orders} pesanan</span></span>
                        <span className="text-gray-700">tunai {rp(r.cash)} · QRIS {rp(r.qris)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Modal awal</p><p className="font-semibold text-gray-900">{rp(shift.starting_cash)}</p></div>
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Penjualan tunai</p><p className="font-semibold text-gray-900">{rp(shift.total_cash_sales)}</p></div>
                <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Penjualan QRIS</p><p className="font-semibold text-gray-900">{rp(shift.total_qris_sales)}</p></div>
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
