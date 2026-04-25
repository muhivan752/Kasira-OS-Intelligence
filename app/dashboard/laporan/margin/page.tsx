'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { TrendingUp, AlertTriangle, ArrowLeft, Wallet, BookOpen } from 'lucide-react';
import { getOutlets, getMarginReport } from '@/app/actions/api';

interface MarginProduct {
  id: string;
  name: string;
  sku: string | null;
  base_price: number;
  buy_price: number | null;
  margin: number | null;
  margin_pct: number | null;
  stock_qty: number;
  stock_enabled: boolean;
  sold_total: number;
  missing_buy_price: boolean;
  negative_margin: boolean;
  last_restock_at: string | null;
}

interface MarginSummary {
  total_products: number;
  with_buy_price: number;
  missing_buy_price: number;
  avg_margin_pct: number | null;
  stock_mode: string;
}

export default function MarginReportPage() {
  const [loading, setLoading] = useState(true);
  const [outlets, setOutlets] = useState<any[]>([]);
  const [outletId, setOutletId] = useState<string>('');
  const [summary, setSummary] = useState<MarginSummary | null>(null);
  const [products, setProducts] = useState<MarginProduct[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isRecipeMode, setIsRecipeMode] = useState(false);

  useEffect(() => {
    (async () => {
      const list = await getOutlets();
      setOutlets(list || []);
      if (list && list.length > 0) {
        setOutletId(list[0].id);
      } else {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!outletId) return;
    (async () => {
      setLoading(true);
      setError(null);
      setIsRecipeMode(false);
      const { data, error: err, isRecipeMode: recipeMode } = await getMarginReport(outletId);
      if (err) {
        setError(err);
        setIsRecipeMode(recipeMode);
        setSummary(null);
        setProducts([]);
      } else {
        setSummary(data?.summary || null);
        setProducts(data?.products || []);
      }
      setLoading(false);
    })();
  }, [outletId]);

  const fmt = (n: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n || 0);

  const marginColor = (negative: boolean, missing: boolean) => {
    if (missing) return 'text-amber-600';
    if (negative) return 'text-red-600';
    return 'text-green-600';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/dashboard/laporan"
          className="p-2 -ml-2 rounded-lg hover:bg-gray-100 text-gray-500"
          aria-label="Kembali"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Laporan Untung-Rugi</h1>
          <p className="text-gray-500 text-sm">
            Margin per produk untuk mode Stok Sederhana. Update otomatis tiap restock dengan harga beli.
          </p>
        </div>
        <select
          value={outletId}
          onChange={(e) => setOutletId(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white font-medium text-gray-700 text-sm"
        >
          {outlets.map((o) => (
            <option key={o.id} value={o.id}>{o.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">Memuat laporan...</div>
      ) : error ? (
        <div className={`rounded-xl border p-8 ${isRecipeMode ? 'bg-blue-50 border-blue-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-start gap-3">
            {isRecipeMode ? (
              <BookOpen className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className={`font-semibold ${isRecipeMode ? 'text-blue-900' : 'text-red-900'}`}>
                {isRecipeMode ? 'Outlet pakai mode Resep' : 'Gagal memuat laporan'}
              </p>
              <p className={`text-sm mt-1 ${isRecipeMode ? 'text-blue-700' : 'text-red-700'}`}>{error}</p>
              {isRecipeMode && (
                <Link
                  href="/dashboard/laporan/hpp"
                  className="inline-block mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Buka Laporan HPP →
                </Link>
              )}
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Rata-rata Margin</p>
                  <p className={`text-lg font-bold ${
                    summary?.avg_margin_pct == null
                      ? 'text-gray-400'
                      : summary.avg_margin_pct < 20
                      ? 'text-red-600'
                      : summary.avg_margin_pct < 40
                      ? 'text-amber-600'
                      : 'text-green-600'
                  }`}>
                    {summary?.avg_margin_pct != null ? `${summary.avg_margin_pct.toFixed(1)}%` : '—'}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
                  <Wallet className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Total Produk</p>
                  <p className="text-lg font-bold text-gray-900">{summary?.total_products ?? 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Sudah ada Modal</p>
                  <p className="text-lg font-bold text-gray-900">{summary?.with_buy_price ?? 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  (summary?.missing_buy_price ?? 0) > 0 ? 'bg-amber-50 text-amber-600' : 'bg-gray-50 text-gray-400'
                }`}>
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Belum diisi</p>
                  <p className={`text-lg font-bold ${
                    (summary?.missing_buy_price ?? 0) > 0 ? 'text-amber-600' : 'text-gray-900'
                  }`}>
                    {summary?.missing_buy_price ?? 0}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Action focus banner */}
          {(summary?.missing_buy_price ?? 0) > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-amber-900">
                  {summary?.missing_buy_price} produk belum punya harga modal
                </p>
                <p className="text-sm text-amber-700 mt-1">
                  Edit harga beli via halaman <Link href="/dashboard/menu" className="underline font-medium">Menu</Link>{' '}
                  atau dari aplikasi Kasir saat restock. Margin gak bisa dihitung selama harga beli kosong.
                </p>
              </div>
            </div>
          )}

          {/* Products table */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-bold text-gray-900">Produk per Margin</h2>
              <p className="text-xs text-gray-500 mt-1">
                Diurutkan: belum-isi-modal dulu (perlu di-isi), lalu margin terkecil → terbesar.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Produk</th>
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase text-right">Harga Jual</th>
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase text-right">Modal</th>
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase text-right">Margin</th>
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase text-center">Margin %</th>
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase text-right hidden lg:table-cell">Stok</th>
                    <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase text-right hidden lg:table-cell">Terjual</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {products.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                        Belum ada produk di outlet ini.
                      </td>
                    </tr>
                  ) : (
                    products.map((p) => (
                      <tr
                        key={p.id}
                        className={`hover:bg-gray-50 transition-colors ${
                          p.missing_buy_price ? 'bg-amber-50/30' : p.negative_margin ? 'bg-red-50/30' : ''
                        }`}
                      >
                        <td className="px-6 py-3">
                          <div className="text-sm font-medium text-gray-900">{p.name}</div>
                          {p.sku && <div className="text-xs text-gray-500">{p.sku}</div>}
                          {p.missing_buy_price && (
                            <div className="text-xs text-amber-700 italic mt-0.5">Modal belum diisi</div>
                          )}
                          {p.negative_margin && !p.missing_buy_price && (
                            <div className="text-xs text-red-700 italic mt-0.5">Rugi — modal &gt; jual</div>
                          )}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-900 text-right">{fmt(p.base_price)}</td>
                        <td className="px-6 py-3 text-sm text-right">
                          {p.buy_price != null ? (
                            <span className="text-gray-900">{fmt(p.buy_price)}</span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className={`px-6 py-3 text-sm font-semibold text-right ${marginColor(p.negative_margin, p.missing_buy_price)}`}>
                          {p.margin != null ? fmt(p.margin) : '—'}
                        </td>
                        <td className="px-6 py-3 text-center">
                          {p.margin_pct != null ? (
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                p.margin_pct < 0
                                  ? 'bg-red-100 text-red-800'
                                  : p.margin_pct < 20
                                  ? 'bg-amber-100 text-amber-800'
                                  : p.margin_pct < 40
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-green-100 text-green-800'
                              }`}
                            >
                              {p.margin_pct.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-gray-400 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600 text-right hidden lg:table-cell">
                          {p.stock_enabled ? p.stock_qty : '—'}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600 text-right hidden lg:table-cell">{p.sold_total}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
