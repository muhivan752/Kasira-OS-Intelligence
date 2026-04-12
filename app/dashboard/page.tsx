'use client';

import { useEffect, useState } from 'react';
import { getOutlets, getDailyReport, getWeeklyRevenue, getBestSellers } from '@/app/actions/api';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import {
  TrendingUp,
  ShoppingCart,
  Clock,
  AlertTriangle,
  Award
} from 'lucide-react';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<any>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [bestSellers, setBestSellers] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const outlets = await getOutlets();
        if (outlets && outlets.length > 0) {
          const outletId = outlets[0].id;
          const today = new Date().toISOString().split('T')[0];
          
          const [daily, weekly, bestSellersData] = await Promise.all([
            getDailyReport(outletId, today),
            getWeeklyRevenue(outletId),
            getBestSellers(5)
          ]);

          setReport(daily);
          setChartData(weekly);
          setBestSellers(bestSellersData || []);
        }
      } catch (error) {
        console.error('Failed to load dashboard data', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64">Memuat...</div>;
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ringkasan Hari Ini</h1>
        <p className="text-gray-500">Ringkasan performa outlet Anda hari ini.</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Pendapatan</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {formatCurrency(report?.revenue_today)}
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
              <p className="text-sm font-medium text-gray-500">Total Pesanan</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {report?.order_count || 0}
              </p>
            </div>
            <div className="w-12 h-12 bg-green-50 rounded-lg flex items-center justify-center text-green-600">
              <ShoppingCart className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Shift Aktif</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {report?.active_shifts || 0}
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center text-purple-600">
              <Clock className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Stok Kritis</p>
              <p className="text-2xl font-bold text-red-600 mt-1">
                {report?.critical_stock_items || 0}
              </p>
            </div>
            <div className="w-12 h-12 bg-red-50 rounded-lg flex items-center justify-center text-red-600">
              <AlertTriangle className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Pendapatan 7 Hari Terakhir</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tickFormatter={(value) => `Rp${value / 1000}k`}
                />
                <Tooltip 
                  formatter={(value: any) => [formatCurrency(Number(value)), 'Pendapatan']}
                  cursor={{ fill: '#f3f4f6' }}
                />
                <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Products Today */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Top 5 Hari Ini</h2>
          <div className="space-y-4">
            {report?.top_products?.length > 0 ? (
              report.top_products.slice(0, 5).map((product: any, index: number) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center text-sm font-medium text-gray-600">
                      #{index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{product.name}</p>
                      <p className="text-xs text-gray-500">{product.qty} terjual</p>
                    </div>
                  </div>
                  <p className="text-sm font-medium text-gray-900">
                    {formatCurrency(product.revenue)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">Belum ada data penjualan</p>
            )}
          </div>
        </div>
      </div>

      {/* Best Seller All Time */}
      {bestSellers.length > 0 && (
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Award className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-bold text-gray-900">Best Seller</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {bestSellers.map((product: any, index: number) => (
              <div key={product.id} className="relative text-center p-4 rounded-xl border border-gray-100 bg-gray-50">
                {index === 0 && (
                  <span className="absolute -top-2 -right-2 bg-yellow-400 text-white text-xs font-bold px-2 py-0.5 rounded-full">#1</span>
                )}
                {index === 1 && (
                  <span className="absolute -top-2 -right-2 bg-gray-400 text-white text-xs font-bold px-2 py-0.5 rounded-full">#2</span>
                )}
                {index === 2 && (
                  <span className="absolute -top-2 -right-2 bg-amber-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">#3</span>
                )}
                {index > 2 && (
                  <span className="absolute -top-2 -right-2 bg-gray-300 text-gray-600 text-xs font-bold px-2 py-0.5 rounded-full">#{index + 1}</span>
                )}
                <p className="text-sm font-semibold text-gray-900 mt-1">{product.name}</p>
                <p className="text-xs text-gray-500 mt-1">{product.sold_total} terjual</p>
                <p className="text-sm font-bold text-blue-600 mt-1">{formatCurrency(Number(product.base_price))}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
