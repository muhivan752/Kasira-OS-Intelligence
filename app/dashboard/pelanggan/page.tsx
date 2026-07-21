'use client';

import { useCallback, useEffect, useState } from 'react';
import { Search, Users, RefreshCw, Download, X, Star, Loader2 } from 'lucide-react';
import { getCrmCustomers, getCrmCustomerDetail, refreshCrmStats } from '@/app/actions/api';

type Customer = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  notes: string | null;
  total_visits: number;
  total_spent: number;
  avg_spent: number;
  first_visit_at: string | null;
  last_visit_at: string | null;
  wa_marketing_consent: boolean;
};

type Detail = Customer & {
  orders: {
    id: string;
    order_number: string;
    created_at: string | null;
    total_amount: number;
    order_type: string;
    items: { name: string; qty: number }[];
  }[];
  favourites: { name: string; qty: number }[];
};

const SORTS = [
  { key: 'last_visit', label: 'Terakhir mampir' },
  { key: 'spent', label: 'Belanja terbesar' },
  { key: 'visits', label: 'Paling sering' },
  { key: 'newest', label: 'Terbaru' },
  { key: 'name', label: 'Nama' },
];

const rp = (n: number) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n || 0);

function daysSince(iso: string | null): number | null {
  if (!iso) return null;
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
}

function tanggal(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function PelangganPage() {
  const [items, setItems] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [repeat, setRepeat] = useState(0);
  const [spentAll, setSpentAll] = useState(0);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('last_visit');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async (opts: { silent?: boolean } = {}) => {
    if (!opts.silent) setLoading(true);
    try {
      const data = await getCrmCustomers({ search, sort });
      setItems(data?.items ?? []);
      setTotal(data?.total ?? 0);
      setRepeat(data?.repeat_customers ?? 0);
      setSpentAll(data?.total_spent_all ?? 0);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [sort, search]);

  // Debounce pencarian — tiap ketikan jangan langsung nembak server.
  useEffect(() => {
    const t = setTimeout(() => load(), search ? 350 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  async function openDetail(id: string) {
    setDetailLoading(true);
    setDetail(null);
    try {
      setDetail(await getCrmCustomerDetail(id));
    } finally {
      setDetailLoading(false);
    }
  }

  async function recompute() {
    setRefreshing(true);
    try {
      await refreshCrmStats();
      await load({ silent: true });
    } finally {
      setRefreshing(false);
    }
  }

  function exportCsv() {
    const head = ['Nama', 'No HP', 'Email', 'Kunjungan', 'Total Belanja', 'Rata-rata', 'Kunjungan Pertama', 'Terakhir Mampir', 'Catatan'];
    const rows = items.map((c) => [
      c.name, c.phone ?? '', c.email ?? '', c.total_visits,
      Math.round(c.total_spent), Math.round(c.avg_spent),
      tanggal(c.first_visit_at), tanggal(c.last_visit_at), (c.notes ?? '').replace(/\n/g, ' '),
    ]);
    const esc = (v: any) => `"${String(v).replace(/"/g, '""')}"`;
    const csv = [head, ...rows].map((r) => r.map(esc).join(',')).join('\n');
    // BOM biar Excel Indonesia baca UTF-8 dengan benar (nama sering pakai é/ñ).
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `pelanggan-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pelanggan</h1>
          <p className="text-gray-500">Siapa yang balik lagi, dan seberapa sering.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={recompute}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Hitung ulang
          </button>
          <button
            onClick={exportCsv}
            disabled={!items.length}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Total pelanggan" value={String(total)} />
        <Stat label="Pelanggan balik lagi" value={String(repeat)} hint={total ? `${Math.round((repeat / total) * 100)}% dari total` : undefined} />
        <Stat label="Total belanja tercatat" value={rp(spentAll)} />
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari nama, HP, atau email…"
            className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-emerald-500"
          />
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        >
          {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {loading ? (
          <div className="p-10 text-center text-gray-500">Memuat…</div>
        ) : !items.length ? (
          <div className="p-10 text-center">
            <Users className="mx-auto h-8 w-8 text-gray-300" />
            <p className="mt-3 font-semibold text-gray-700">Belum ada pelanggan tercatat</p>
            <p className="mx-auto mt-1 max-w-md text-sm text-gray-500">
              Pelanggan tercatat otomatis saat kasir memilih pelanggan di transaksi, atau saat struk dikirim
              lewat WhatsApp. Semakin sering dipakai, semakin kelihatan siapa yang balik lagi.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">Nama</th>
                  <th className="px-4 py-3">No HP</th>
                  <th className="px-4 py-3 text-right">Kunjungan</th>
                  <th className="px-4 py-3 text-right">Total belanja</th>
                  <th className="px-4 py-3">Terakhir mampir</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((c) => {
                  const d = daysSince(c.last_visit_at);
                  return (
                    <tr key={c.id} onClick={() => openDetail(c.id)} className="cursor-pointer hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="font-medium text-gray-900">{c.name}</span>
                        {c.total_visits > 1 && (
                          <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                            balik lagi
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{c.phone || '—'}</td>
                      <td className="px-4 py-3 text-right text-gray-900">{c.total_visits}×</td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900">{rp(c.total_spent)}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {tanggal(c.last_visit_at)}
                        {d !== null && d > 30 && (
                          <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                            {d} hari lalu
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(detail || detailLoading) && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" onClick={() => setDetail(null)}>
          <div
            onClick={(e) => e.stopPropagation()}
            className="max-h-[85vh] w-full overflow-y-auto rounded-t-2xl bg-white p-6 sm:max-w-lg sm:rounded-2xl"
          >
            {detailLoading || !detail ? (
              <div className="py-10 text-center text-gray-500">Memuat…</div>
            ) : (
              <>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{detail.name}</h2>
                    <p className="text-sm text-gray-500">{detail.phone || 'Nomor belum ada'}</p>
                  </div>
                  <button onClick={() => setDetail(null)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100">
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3">
                  <MiniStat label="Kunjungan" value={`${detail.total_visits}×`} />
                  <MiniStat label="Total" value={rp(detail.total_spent)} />
                  <MiniStat label="Rata-rata" value={rp(detail.avg_spent)} />
                </div>

                {detail.favourites.length > 0 && (
                  <div className="mt-5">
                    <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-gray-500">
                      <Star className="h-3.5 w-3.5" /> Sering dipesan
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {detail.favourites.map((f) => (
                        <span key={f.name} className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                          {f.name} · {f.qty}×
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-5">
                  <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Riwayat belanja</p>
                  {detail.orders.length === 0 ? (
                    <p className="mt-2 text-sm text-gray-500">Belum ada transaksi lunas yang tercatat.</p>
                  ) : (
                    <ul className="mt-2 divide-y divide-gray-100">
                      {detail.orders.map((o) => (
                        <li key={o.id} className="flex items-start justify-between gap-3 py-2.5">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900">{tanggal(o.created_at)}</p>
                            <p className="truncate text-xs text-gray-500">
                              {o.items.map((i) => `${i.name}${i.qty > 1 ? ` ×${i.qty}` : ''}`).join(', ') || o.order_number}
                            </p>
                          </div>
                          <span className="shrink-0 text-sm font-semibold text-gray-900">{rp(o.total_amount)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 p-3">
      <p className="text-[11px] font-medium text-gray-500">{label}</p>
      <p className="mt-0.5 truncate text-sm font-bold text-gray-900">{value}</p>
    </div>
  );
}
