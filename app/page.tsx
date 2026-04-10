import Link from 'next/link';
import {
  Smartphone, Globe, LineChart, Package,
  Sparkles, CheckCircle2, ArrowRight, MessageCircle,
  Zap, Shield, Clock
} from 'lucide-react';
import Navbar from '@/components/landing/Navbar';
import FAQ from '@/components/landing/FAQ';

export default function LandingPage() {
  const waLink = 'https://wa.me/6285270782220?text=Halo%20Kasira%2C%20saya%20mau%20coba%20Kasira';

  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* HERO */}
      <section className="relative pt-32 pb-24 lg:pt-48 lg:pb-36 overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-50 via-white to-white" />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-emerald-400/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-emerald-300/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-5xl md:text-7xl font-extrabold text-gray-900 tracking-tight leading-[1.1] mb-6">
              Kasir Digital yang{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-emerald-700">
                Benar-Benar Simpel
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-gray-500 mb-10 leading-relaxed max-w-2xl mx-auto">
              POS modern + storefront gratis + QRIS tanpa ribet. Masuk lewat WhatsApp, langsung jalan.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href={waLink}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-3 px-8 py-4 bg-emerald-500 text-white text-lg font-bold rounded-2xl hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-500/25 hover:-translate-y-0.5"
              >
                <MessageCircle className="w-5 h-5" />
                Daftar via WhatsApp
              </a>
              <Link
                href="/kasira-coffee"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-gray-700 text-lg font-semibold rounded-2xl border-2 border-gray-200 hover:border-gray-300 transition-all"
              >
                Lihat Demo Storefront
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>

          {/* Dashboard Mockup */}
          <div className="mt-20 relative mx-auto max-w-4xl">
            <div className="rounded-2xl overflow-hidden shadow-2xl border border-gray-200 bg-gray-900">
              {/* Browser chrome */}
              <div className="bg-gray-800 px-4 py-3 flex items-center gap-2 border-b border-gray-700">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/70" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
                  <div className="w-3 h-3 rounded-full bg-green-500/70" />
                </div>
                <div className="flex-1 bg-gray-700 rounded-md px-3 py-1 text-xs text-gray-400 text-center">
                  kasira.id/dashboard
                </div>
              </div>
              {/* Dashboard preview */}
              <div className="bg-gray-50 p-6">
                <div className="grid grid-cols-3 gap-4 mb-6">
                  {[
                    { label: 'Revenue Hari Ini', value: 'Rp 2.4jt', bg: 'bg-emerald-100', bar: 'bg-emerald-500' },
                    { label: 'Total Order', value: '47 order', bg: 'bg-blue-100', bar: 'bg-blue-500' },
                    { label: 'Produk Aktif', value: '32 menu', bg: 'bg-purple-100', bar: 'bg-purple-500' },
                  ].map((stat, i) => (
                    <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                      <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
                      <p className="text-xl font-bold text-gray-900">{stat.value}</p>
                      <div className={`mt-2 h-1 rounded-full ${stat.bg}`}>
                        <div className={`h-1 rounded-full ${stat.bar} w-2/3`} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-700">Transaksi Terbaru</span>
                    <span className="text-xs text-emerald-600 font-medium">Live</span>
                  </div>
                  {[
                    { name: 'Kopi Susu', time: '14:32', amount: 'Rp 25.000', status: 'Selesai' },
                    { name: 'Croissant + Latte', time: '14:28', amount: 'Rp 55.000', status: 'Selesai' },
                    { name: 'Matcha Latte', time: '14:21', amount: 'Rp 32.000', status: 'Selesai' },
                  ].map((tx, i) => (
                    <div key={i} className="px-4 py-3 flex items-center justify-between border-b border-gray-50 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{tx.name}</p>
                        <p className="text-xs text-gray-400">{tx.time}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-gray-900">{tx.amount}</p>
                        <span className="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full">{tx.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* VALUE PROPS */}
      <section className="py-12 bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            {[
              { icon: Zap, title: 'Setup 5 Menit', desc: 'Daftar WA, tambah menu, langsung kasir' },
              { icon: Shield, title: 'Zero Komisi', desc: 'Storefront & QRIS tanpa potongan apapun' },
              { icon: Clock, title: 'Offline Mode', desc: 'Tetap transaksi meski internet mati' },
            ].map(({ icon: Icon, title, desc }, i) => (
              <div key={i} className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 bg-emerald-500/10 rounded-2xl flex items-center justify-center">
                  <Icon className="w-6 h-6 text-emerald-400" />
                </div>
                <p className="text-white font-bold">{title}</p>
                <p className="text-gray-400 text-sm">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FITUR */}
      <section id="features" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Semua yang kamu butuhkan
            </h2>
            <p className="text-lg text-gray-500">
              Dirancang khusus untuk cafe dan UMKM Indonesia
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Smartphone,
                title: 'Kasir Digital',
                desc: 'Input order, terima QRIS, cetak struk. Offline mode tetap jalan tanpa internet.',
                pro: false,
              },
              {
                icon: Globe,
                title: 'Storefront Gratis',
                desc: 'kasira.id/nama-kamu aktif otomatis. Customer bisa order online, zero komisi selamanya.',
                pro: false,
              },
              {
                icon: LineChart,
                title: 'Dashboard Owner',
                desc: 'Pantau revenue, stok, dan laporan harian dari HP manapun kapan saja.',
                pro: false,
              },
              {
                icon: Package,
                title: 'Manajemen Stok',
                desc: 'Stok auto-kurang setiap transaksi. Produk auto-hilang dari menu saat stok habis.',
                pro: false,
              },
              {
                icon: Sparkles,
                title: 'AI Insight',
                desc: 'Laporan dan insight bisnis harian dikirim otomatis via WA. Tanya jawab langsung.',
                pro: true,
              },
              {
                icon: MessageCircle,
                title: 'Kitchen Display',
                desc: 'Layar dapur real-time. Pesanan masuk otomatis, dapur langsung tahu.',
                pro: true,
              },
            ].map(({ icon: Icon, title, desc, pro }, i) => (
              <div key={i} className="relative bg-gray-50 rounded-2xl p-7 border border-gray-100 hover:border-emerald-200 hover:shadow-md transition-all group">
                {pro && (
                  <span className="absolute top-5 right-5 bg-amber-100 text-amber-700 text-xs font-bold px-2.5 py-1 rounded-full">
                    PRO
                  </span>
                )}
                <div className="w-11 h-11 bg-white border border-gray-200 rounded-xl flex items-center justify-center mb-5 group-hover:bg-emerald-50 group-hover:border-emerald-200 transition-colors">
                  <Icon className="w-5 h-5 text-gray-600 group-hover:text-emerald-600 transition-colors" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 bg-emerald-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Mulai dalam 5 menit</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8 relative">
            <div className="hidden md:block absolute top-10 left-[20%] right-[20%] h-px bg-emerald-200" />
            {[
              { step: '1', title: 'Chat WhatsApp', desc: 'Hubungi kami via WA, kami bantu setup awal gratis.' },
              { step: '2', title: 'Input Menu', desc: 'Tambah produk beserta harga. Storefront aktif otomatis.' },
              { step: '3', title: 'Kasir Jalan', desc: 'Download app kasir, login WA, langsung transaksi hari ini.' },
            ].map(({ step, title, desc }, i) => (
              <div key={i} className="relative text-center">
                <div className="w-20 h-20 mx-auto bg-white border-2 border-emerald-200 rounded-full flex items-center justify-center mb-5 relative z-10 shadow-sm">
                  <span className="text-2xl font-black text-emerald-500">{step}</span>
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Harga transparan</h2>
            <p className="text-lg text-gray-500">Mulai gratis, tidak perlu kartu kredit</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 items-start">
            {/* STARTER */}
            <div className="bg-white rounded-2xl p-7 border-2 border-emerald-500 shadow-lg relative flex flex-col">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-xs font-bold px-4 py-1 rounded-full whitespace-nowrap">
                Paling Populer
              </div>
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-1">STARTER</h3>
                <p className="text-sm text-gray-400 mb-4">Warung, kantin & toko kecil</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-black text-gray-900">Rp 99rb</span>
                  <span className="text-gray-400 text-sm">/bulan</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                {['Max 3 kasir', 'Max 500 produk', 'Cash + QRIS Xendit', 'Storefront gratis', 'Laporan harian', 'Manajemen stok', 'Email support'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <a href={waLink} target="_blank" rel="noopener noreferrer"
                className="w-full block text-center px-5 py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors text-sm">
                Mulai Gratis
              </a>
            </div>

            {/* PRO */}
            <div className="bg-white rounded-2xl p-7 border border-gray-200 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-1">PRO</h3>
                <p className="text-sm text-gray-400 mb-4">Coffee shop & cafe</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-black text-gray-900">Rp 299rb</span>
                  <span className="text-gray-400 text-sm">/bulan</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                <li className="text-xs font-bold text-gray-400 uppercase tracking-wide pb-2 border-b border-gray-100">Semua Starter +</li>
                {['Max 10 kasir', 'Unlimited produk', 'Kitchen display', 'AI daily insight WA', 'Loyalty points', 'Reservasi meja', 'Export Excel/PDF', 'Priority WA support'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <a href={waLink} target="_blank" rel="noopener noreferrer"
                className="w-full block text-center px-5 py-3 bg-gray-900 text-white font-bold rounded-xl hover:bg-gray-800 transition-colors text-sm">
                Hubungi Kami
              </a>
            </div>

            {/* BUSINESS */}
            <div className="bg-white rounded-2xl p-7 border border-gray-200 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-1">BUSINESS</h3>
                <p className="text-sm text-gray-400 mb-4">Resto & cafe chain</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-black text-gray-900">Rp 499rb</span>
                  <span className="text-gray-400 text-sm">/bulan</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                <li className="text-xs font-bold text-gray-400 uppercase tracking-wide pb-2 border-b border-gray-100">Semua Pro +</li>
                {['Unlimited kasir', 'Multi outlet', 'HQ dashboard', 'Transfer stok antar outlet', 'Prediksi stok & revenue', 'WA support + onboarding'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <a href={waLink} target="_blank" rel="noopener noreferrer"
                className="w-full block text-center px-5 py-3 bg-white text-gray-900 border-2 border-gray-200 font-bold rounded-xl hover:bg-gray-50 transition-colors text-sm">
                Hubungi Kami
              </a>
            </div>

            {/* ENTERPRISE */}
            <div className="bg-gray-900 rounded-2xl p-7 border border-gray-800 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-white mb-1">ENTERPRISE</h3>
                <p className="text-sm text-gray-400 mb-4">Grup multi-brand</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-black text-white">Rp 1.499rb</span>
                  <span className="text-gray-400 text-sm">/bln</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                <li className="text-xs font-bold text-gray-500 uppercase tracking-wide pb-2 border-b border-gray-800">Semua Business +</li>
                {['5 brand + 10 outlet', 'AI autonomous', 'White label APK', 'Custom domain', 'SLA 99.9% uptime', 'Account manager'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-gray-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <a href={waLink} target="_blank" rel="noopener noreferrer"
                className="w-full block text-center px-5 py-3 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-colors text-sm">
                Hubungi Kami
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <FAQ />

      {/* CTA */}
      <section className="py-24 bg-gradient-to-br from-emerald-500 to-emerald-700 relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-black/10 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-4">
            Siap coba Kasira?
          </h2>
          <p className="text-emerald-100 text-xl mb-10">
            Kami bantu setup dari nol.
          </p>
          <a
            href={waLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-3 px-10 py-5 bg-white text-emerald-600 text-lg font-bold rounded-2xl hover:bg-gray-50 transition-all shadow-xl hover:-translate-y-1"
          >
            <MessageCircle className="w-6 h-6" />
            Chat WhatsApp Sekarang
          </a>
          <p className="mt-5 text-emerald-200 text-sm">
            Setup 5 menit · Tidak perlu kartu kredit · Cancel kapan saja
          </p>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-gray-950 py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-8">
            <div>
              <span className="text-white font-black text-2xl tracking-tight">kasira</span>
              <span className="text-emerald-500 font-black text-2xl">.</span>
            </div>
            <div className="flex flex-wrap justify-center gap-8 text-sm">
              <Link href="#features" className="text-gray-400 hover:text-white transition-colors">Fitur</Link>
              <Link href="#pricing" className="text-gray-400 hover:text-white transition-colors">Harga</Link>
              <Link href="/kasira-coffee" className="text-gray-400 hover:text-white transition-colors">Demo</Link>
              <Link href="/login" className="text-gray-400 hover:text-white transition-colors">Login</Link>
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:text-emerald-300 transition-colors">WhatsApp</a>
            </div>
          </div>
          <div className="pt-8 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-500 text-sm">© 2026 Kasira. All rights reserved.</p>
            <p className="text-gray-500 text-sm">POS Digital untuk UMKM Indonesia 🇮🇩</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
