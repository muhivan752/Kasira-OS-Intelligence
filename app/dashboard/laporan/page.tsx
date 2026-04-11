'use client';

import { useState, useEffect } from 'react';
import { getOutlets, getReportSummary, getOrders } from '@/app/actions/api';
import { Calendar, Download, Banknote, CreditCard, TrendingUp, BarChart3, ShoppingCart } from 'lucide-react';

export default function LaporanPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState<string>('');
  const [filter, setFilter] = useState('week'); // today, week, month
  const [summary, setSummary] = useState<any>(null);
  const [orders, setOrders] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, [filter]);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const id = outlets[0].id;
        setOutletId(id);

        const today = new Date();
        let startDate = new Date(today);
        const endDateStr = today.toISOString().split('T')[0];

        if (filter === 'today') {
          // same day
        } else if (filter === 'week') {
          startDate.setDate(today.getDate() - 6);
        } else if (filter === 'month') {
          startDate.setDate(today.getDate() - 29);
        }
        const startDateStr = startDate.toISOString().split('T')[0];

        const [summaryData, ordersData] = await Promise.all([
          getReportSummary(id, startDateStr, endDateStr),
          getOrders(id, startDateStr, endDateStr),
        ]);

        setSummary(summaryData);
        setOrders(ordersData || []);
      }
    } catch (error) {
      console.error('Gagal memuat laporan', error);
    } finally {
      setLoading(false);
    }
  }

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(amount || 0);

  const formatCurrencyShort = (amount: number) => {
    if (amount >= 1_000_000) return `Rp${(amount / 1_000_000).toFixed(1)}jt`;
    if (amount >= 1_000) return `Rp${(amount / 1_000).toFixed(0)}rb`;
    return `Rp${amount}`;
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleString('id-ID', {
      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });

  const formatDayDate = (dateString: string) => {
    const d = new Date(dateString + 'T00:00:00');
    return d.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const totalRevenue = summary?.total?.revenue || 0;
  const totalCash = summary?.total?.cash || 0;
  const totalQris = summary?.total?.qris || 0;
  const totalOrders = summary?.total?.orders || 0;
  const avgPerDay = summary?.total?.avg_per_day || 0;
  const days = summary?.days || [];

  // Chart: find max revenue for scaling
  const maxRevenue = Math.max(...days.map((d: any) => d.revenue), 1);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Memuat laporan...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Laporan Penjualan</h1>
          <p className="text-gray-500">Pantau performa bisnis dan riwayat transaksi.</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white font-medium text-gray-700"
          >
            <option value="today">Hari Ini</option>
            <option value="week">7 Hari Terakhir</option>
            <option value="month">30 Hari Terakhir</option>
          </select>
          <button
            onClick={() => {
              if (!orders.length) return;
              const header = 'No Order,Waktu,Tipe,Metode,Status,Total\n';
              const rows = orders
                .map((o: any) =>
                  `${o.order_number},${o.created_at},${o.order_type},${o.payment_method || '-'},${o.status},${o.total_amount}`
                )
                .join('\n');
              const blob = new Blob([header + rows], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `laporan-${filter}-${new Date().toISOString().split('T')[0]}.csv`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download className="w-5 h-5" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">Total Pendapatan</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(totalRevenue)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-50 rounded-lg flex items-center justify-center text-orange-600">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">Total Transaksi</p>
              <p className="text-lg font-bold text-gray-900">{totalOrders}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600">
              <Banknote className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">Cash</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(totalCash)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center text-purple-600">
              <CreditCard className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">QRIS</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(totalQris)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Revenue Chart (simple bar chart) */}
      {days.length > 1 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-bold text-gray-900">Tren Pendapatan</h2>
          </div>
          <div className="flex items-end gap-1 sm:gap-2 h-48">
            {days.map((day: any, i: number) => {
              const height = maxRevenue > 0 ? (day.revenue / maxRevenue) * 100 : 0;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                  {/* Tooltip */}
                  <div className="hidden group-hover:block absolute -top-16 bg-gray-800 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap z-10 shadow-lg">
                    <div className="font-bold">{formatCurrency(day.revenue)}</div>
                    <div>{day.orders} transaksi</div>
                  </div>
                  {/* Bar */}
                  <div className="w-full flex justify-center">
                    <div
                      className="w-full max-w-[40px] bg-blue-500 rounded-t-md hover:bg-blue-600 transition-colors cursor-pointer"
                      style={{ height: `${Math.max(height, 2)}%` }}
                    />
                  </div>
                  {/* Label */}
                  <span className="text-[10px] sm:text-xs text-gray-500 text-center leading-tight">
                    {formatDayDate(day.date).split(', ').pop()?.replace(' ', '\n') || day.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between text-sm text-gray-500">
            <span>Rata-rata/hari: <span className="font-semibold text-gray-700">{formatCurrency(avgPerDay)}</span></span>
            <span>Tertinggi: <span className="font-semibold text-gray-700">{formatCurrency(maxRevenue)}</span></span>
          </div>
        </div>
      )}

      {/* Day-by-Day Table */}
      {days.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-bold text-gray-900">Ringkasan Harian</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-6 py-3 text-sm font-medium text-gray-500">Tanggal</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500 text-right">Pendapatan</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500 text-right">Transaksi</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500 text-right hidden sm:table-cell">Cash</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500 text-right hidden sm:table-cell">QRIS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {[...days].reverse().map((day: any) => (
                  <tr key={day.date} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-3 text-sm font-medium text-gray-900">{formatDayDate(day.date)}</td>
                    <td className="px-6 py-3 text-sm font-semibold text-gray-900 text-right">{formatCurrency(day.revenue)}</td>
                    <td className="px-6 py-3 text-sm text-gray-600 text-right">{day.orders}</td>
                    <td className="px-6 py-3 text-sm text-gray-600 text-right hidden sm:table-cell">{formatCurrencyShort(day.cash)}</td>
                    <td className="px-6 py-3 text-sm text-gray-600 text-right hidden sm:table-cell">{formatCurrencyShort(day.qris)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-50 border-t-2 border-gray-300">
                  <td className="px-6 py-3 text-sm font-bold text-gray-900">Total</td>
                  <td className="px-6 py-3 text-sm font-bold text-gray-900 text-right">{formatCurrency(totalRevenue)}</td>
                  <td className="px-6 py-3 text-sm font-bold text-gray-900 text-right">{totalOrders}</td>
                  <td className="px-6 py-3 text-sm font-bold text-gray-600 text-right hidden sm:table-cell">{formatCurrencyShort(totalCash)}</td>
                  <td className="px-6 py-3 text-sm font-bold text-gray-600 text-right hidden sm:table-cell">{formatCurrencyShort(totalQris)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Transaction History */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">Riwayat Transaksi</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-4 text-sm font-medium text-gray-500">No. Order</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Waktu</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500 hidden sm:table-cell">Tipe</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500 hidden sm:table-cell">Metode</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Status</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {orders.length > 0 ? (
                orders.map((order: any) => (
                  <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{order.order_number}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{formatDate(order.created_at)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 capitalize hidden sm:table-cell">
                      {order.order_type?.replace('_', ' ') || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 uppercase hidden sm:table-cell">
                      {order.payment_method || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${
                          order.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : order.status === 'cancelled'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {order.status === 'completed' ? 'Selesai' : order.status === 'cancelled' ? 'Batal' : order.status === 'pending' ? 'Menunggu' : order.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 text-right">
                      {formatCurrency(parseFloat(order.total_amount))}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    Tidak ada transaksi pada periode ini
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
