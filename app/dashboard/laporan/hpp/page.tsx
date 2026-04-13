'use client';

import React, { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import { getHPPReport, getOutlets } from '@/app/actions/api';
import { useProGuard } from '@/app/hooks/use-pro-guard';

interface HPPIngredient {
  name: string;
  quantity: number;
  unit: string;
  buy_price: number;
  buy_qty: number;
  cost_per_unit: number;
  line_cost: number;
}

interface HPPProduct {
  product_id: string;
  product_name: string;
  selling_price: number;
  recipe_cost: number;
  margin_amount: number;
  margin_percent: number;
  has_recipe: boolean;
  ingredients: HPPIngredient[];
}

export default function HPPReportPage() {
  const allowed = useProGuard('Laporan HPP');
  const [products, setProducts] = useState<HPPProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function load() {
      try {
        const outlets = await getOutlets();
        if (outlets?.length > 0) {
          const data = await getHPPReport(outlets[0].brand_id);
          setProducts(data || []);
        }
      } catch { /* */ }
      setLoading(false);
    }
    load();
  }, []);

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n);

  const marginColor = (pct: number) => {
    if (pct < 20) return 'text-red-600 bg-red-50';
    if (pct < 40) return 'text-amber-600 bg-amber-50';
    return 'text-green-600 bg-green-50';
  };

  if (!allowed || loading) return <div className="flex items-center justify-center h-64">Memuat...</div>;

  const withRecipe = products.filter(p => p.has_recipe);
  const withoutRecipe = products.filter(p => !p.has_recipe);
  const avgMargin = withRecipe.length > 0
    ? withRecipe.reduce((s, p) => s + p.margin_percent, 0) / withRecipe.length : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Laporan HPP</h1>
        <p className="text-gray-500">Harga Pokok Penjualan — analisis cost vs harga jual per produk</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <p className="text-sm text-gray-500">Produk dengan Resep</p>
          <p className="text-2xl font-bold mt-1">{withRecipe.length} / {products.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <p className="text-sm text-gray-500">Rata-rata Margin</p>
          <p className={`text-2xl font-bold mt-1 ${avgMargin < 20 ? 'text-red-600' : avgMargin < 40 ? 'text-amber-600' : 'text-green-600'}`}>
            {avgMargin.toFixed(1)}%
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <p className="text-sm text-gray-500">Tanpa Resep</p>
          <p className="text-2xl font-bold mt-1 text-gray-400">{withoutRecipe.length}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Produk</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Harga Jual</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">HPP</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Margin</th>
              <th className="text-center px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Margin %</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {products.map((p) => {
              const isExpanded = expanded.has(p.product_id);
              const toggleExpand = () => {
                const next = new Set(expanded);
                if (isExpanded) next.delete(p.product_id); else next.add(p.product_id);
                setExpanded(next);
              };
              return (
                <React.Fragment key={p.product_id}>
                  <tr className="hover:bg-gray-50 cursor-pointer" onClick={p.has_recipe && p.ingredients?.length > 0 ? toggleExpand : undefined}>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {p.has_recipe && p.ingredients?.length > 0 && (
                          isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />
                        )}
                        <span className="font-medium text-gray-900">{p.product_name}</span>
                        {!p.has_recipe && (
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">Tanpa resep</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right text-gray-900">{formatCurrency(p.selling_price)}</td>
                    <td className="px-6 py-4 text-right text-gray-600">
                      {p.has_recipe ? formatCurrency(p.recipe_cost) : '-'}
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-gray-900">
                      {p.has_recipe ? formatCurrency(p.margin_amount) : '-'}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {p.has_recipe ? (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${marginColor(p.margin_percent)}`}>
                          {p.margin_percent}%
                        </span>
                      ) : '-'}
                    </td>
                  </tr>
                  {isExpanded && p.ingredients?.map((ing, idx) => (
                    <tr key={`${p.product_id}-${idx}`} className="bg-gray-50/50">
                      <td className="pl-14 pr-6 py-2">
                        <span className="text-sm text-gray-600">{ing.name}</span>
                        <span className="text-xs text-gray-400 ml-2">
                          {ing.quantity} {ing.unit}
                        </span>
                      </td>
                      <td className="px-6 py-2 text-right text-xs text-gray-400">
                        {ing.buy_price > 0 ? `${formatCurrency(ing.buy_price)}/${ing.buy_qty}${ing.unit}` : '-'}
                      </td>
                      <td className="px-6 py-2 text-right text-sm text-gray-500">
                        {formatCurrency(ing.line_cost)}
                      </td>
                      <td className="px-6 py-2 text-right text-xs text-gray-400">
                        @{formatCurrency(ing.cost_per_unit)}/{ing.unit}
                      </td>
                      <td></td>
                    </tr>
                  ))}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
