'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getOutlets, getDailyReport, getWeeklyRevenue, getBestSellers } from '@/app/actions/api';
import { SefrekuensiCard } from '@/components/dashboard/sefrekuensi-card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const currency = (amount: number | string) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
}).format(Number(amount) || 0);

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<any>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [bestSellers, setBestSellers] = useState<any[]>([]);
  const [outletId, setOutletId] = useState<string>();
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    async function loadData(silent = false) {
      try {
        const outlets = await getOutlets();
        if (!active) return;
        if (!outlets?.length) { setOutletId(undefined); setError(''); return; }
        const id = outlets[0].id;
        setOutletId(id);
        const today = new Date().toISOString().split('T')[0];
        const [daily, weekly, best] = await Promise.all([
          getDailyReport(id, today), getWeeklyRevenue(id), getBestSellers(5),
        ]);
        if (!active) return;
        if (!daily) throw new Error('Daily report unavailable');
        setReport(daily); setChartData(weekly || []); setBestSellers(best || []); setError('');
      } catch {
        if (active) setError('Ringkasan belum dapat dimuat. Coba muat kembali.');
      } finally { if (active && !silent) setLoading(false); }
    }
    loadData();
    const timer = setInterval(() => loadData(true), 30000);
    const onVisible = () => { if (document.visibilityState === 'visible') loadData(true); };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);
    return () => {
      active = false; clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [retry]);

  if (loading) return <p role="status" className="py-16 text-[var(--text-muted)]">Memuat ringkasan toko…</p>;

  return <div className="overview-page">
    <header className="overview-heading">
      <div><p className="text-sm text-[var(--text-muted)]">Dashboard pemilik</p>
        <h1>Ringkasan Hari Ini</h1></div>
      <Link href="/dashboard/laporan" className="overview-link">Lihat laporan</Link>
    </header>
    {error && <div role="alert" className="overview-error"><p>{error}</p>
      <button onClick={() => { setLoading(true); setRetry(value => value + 1); }}>Muat kembali</button></div>}
    {!outletId && !error && <div className="overview-panel"><h2>Siapkan usaha Anda</h2>
      <p>Tambahkan informasi toko dan produk untuk mulai mencatat penjualan.</p>
      <Link href="/onboarding" className="overview-link">Lanjutkan pengaturan usaha</Link></div>}
    {outletId && (!error || report) && <>
      <section className="overview-today" aria-label="Angka penjualan hari ini">
        <div className="overview-revenue"><p>Total Pendapatan</p><strong>{currency(report?.revenue_today)}</strong></div>
        <dl className="overview-metrics">
          <div><dt>Total Pesanan</dt><dd>{report?.order_count || 0}</dd></div>
          <div><dt>Shift Aktif</dt><dd>{report?.active_shifts || 0}</dd></div>
          <div><dt>Stok Kritis</dt><dd><Link href="/dashboard/menu" className={report?.critical_stock_items ? 'text-[var(--danger)]' : ''}>{report?.critical_stock_items || 0}</Link></dd></div>
        </dl>
      </section>
      <div className="overview-columns">
        <section className="overview-panel">
          <h2>Pendapatan 7 Hari Terakhir</h2>
          {chartData.some(day => Number(day.revenue) > 0) ? <div className="h-72 mt-6" role="img" aria-label="Grafik pendapatan tujuh hari terakhir; rincian tersedia pada tabel di bawah">
            <ResponsiveContainer width="100%" height="100%"><BarChart data={chartData}>
              <CartesianGrid vertical={false} stroke="var(--border-default)" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
              <YAxis width={58} axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} tickFormatter={value => `Rp${value / 1000}k`} />
              <Tooltip formatter={(value: any) => [currency(value), 'Pendapatan']} cursor={{ fill: 'var(--bg-subtle)' }} contentStyle={{ background: 'var(--surface-card)', color: 'var(--text-body)', borderColor: 'var(--border-default)', borderRadius: 8 }} />
              <Bar dataKey="revenue" fill="var(--brand-primary)" radius={[3, 3, 0, 0]} />
            </BarChart></ResponsiveContainer>
          </div> : <p className="overview-empty">Belum ada pendapatan dalam tujuh hari terakhir. Transaksi yang tercatat akan muncul di sini.</p>}
          {chartData.length > 0 && <details className="overview-chart-table"><summary>Lihat rincian harian</summary>
            <table><caption className="sr-only">Pendapatan tujuh hari terakhir</caption><thead><tr><th>Hari</th><th>Pendapatan</th></tr></thead>
              <tbody>{chartData.map((day, index) => <tr key={index}><td>{day.name}</td><td>{currency(day.revenue)}</td></tr>)}</tbody></table></details>}
        </section>
        <section className="overview-panel">
          <h2>Produk terlaris hari ini</h2>
          {report?.top_products?.length ? <ol className="overview-products">
            {report.top_products.slice(0, 5).map((product: any, index: number) => <li key={index}>
              <span className="overview-rank">{index + 1}</span><div><strong>{product.name}</strong><p>{product.qty} terjual</p></div><span>{currency(product.revenue)}</span>
            </li>)}
          </ol> : <p className="overview-empty">Belum ada penjualan hari ini.</p>}
        </section>
      </div>
      {bestSellers.length > 0 && <section className="overview-panel">
        <h2>Produk terlaris keseluruhan</h2>
        <ol className="overview-products overview-history">{bestSellers.map((product: any, index: number) => <li key={product.id}>
          <span className="overview-rank">{index + 1}</span><div><strong>{product.name}</strong><p>{product.sold_total} terjual</p></div>
          <span>{currency(product.base_price)}</span>
        </li>)}</ol>
      </section>}
    </>}
    <SefrekuensiCard outletId={outletId} />
  </div>;
}
