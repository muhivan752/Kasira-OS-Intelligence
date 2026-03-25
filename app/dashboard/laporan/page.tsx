'use client';

import { useState, useEffect } from 'react';
import { getOutlets, getDailyReport, getOrders } from '@/app/actions/api';
import { Calendar, Download, Banknote, CreditCard, TrendingUp } from 'lucide-react';

export default function LaporanPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState<string>('');
  const [filter, setFilter] = useState('today'); // today, week, month
  const [report, setReport] = useState<any>(null);
  const [orders, setOrders] = useState<any[]>([]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        let startDateStr = today.toISOString().split('T')[0];
        let endDateStr = today.toISOString().split('T')[0];
        
        if (filter === 'week') {
          const lastWeek = new Date(today);
          lastWeek.setDate(today.getDate() - 7);
          startDateStr = lastWeek.toISOString().split('T')[0];
        } else if (filter === 'month') {
          const lastMonth = new Date(today);
          lastMonth.setMonth(today.getMonth() - 1);
          startDateStr = lastMonth.toISOString().split('T')[0];
        }
        
        // For simplicity, we just fetch daily report for today, 
        // but in a real app we would have a date range report endpoint
        const [daily, ords] = await Promise.all([
          getDailyReport(id, endDateStr),
          getOrders(id, startDateStr, endDateStr)
        ]);
        
        setReport(daily);
        setOrders(ords || []);
      }
    } catch (error) {
      console.error('Failed to load report data', error);
    } finally {
      setLoading(false);
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('id-ID', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Calculate breakdown from orders
  const totalCash = orders.filter(o => o.payment_method === 'cash').reduce((sum, o) => sum + parseFloat(o.total_amount), 0);
  const totalQris = orders.filter(o => o.payment_method === 'qris').reduce((sum, o) => sum + parseFloat(o.total_amount), 0);
  const totalRevenue = totalCash + totalQris;

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="space-y-6">
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
          <button className="flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            <Download className="w-5 h-5" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Pendapatan</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {formatCurrency(totalRevenue)}
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
              <TrendingUp className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Pembayaran Tunai (Cash)</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {formatCurrency(totalCash)}
              </p>
            </div>
            <div className="w-12 h-12 bg-green-50 rounded-lg flex items-center justify-center text-green-600">
              <Banknote className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Pembayaran QRIS</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {formatCurrency(totalQris)}
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center text-purple-600">
              <CreditCard className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Order History */}
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
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Tipe</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Metode</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500">Status</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-500 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {orders.length > 0 ? (
                orders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {order.order_number}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {formatDate(order.created_at)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 capitalize">
                      {order.order_type.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 uppercase">
                      {order.payment_method || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${
                        order.status === 'completed' ? 'bg-green-100 text-green-800' :
                        order.status === 'cancelled' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {order.status}
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
