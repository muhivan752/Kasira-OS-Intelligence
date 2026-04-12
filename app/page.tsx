import Link from 'next/link';
import {
  Smartphone, Globe, LineChart, Package,
  Sparkles, CheckCircle2, ArrowRight, MessageCircle,
  Shield, Wifi, WifiOff, Receipt,
  ChefHat, BarChart3, Users, Star,
  Clock, Flame, CreditCard, Store
} from 'lucide-react';
import Navbar from '@/components/landing/Navbar';
import FAQ from '@/components/landing/FAQ';

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Kasira',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Android, Web',
  description: 'Kasir digital modern dengan storefront gratis, QRIS tanpa komisi, dan AI insight untuk bisnis F&B dan UMKM Indonesia.',
  url: 'https://kasira.online',
  offers: [
    { '@type': 'Offer', name: 'Starter', price: '99000', priceCurrency: 'IDR', description: 'POS + Storefront + QRIS + Laporan' },
    { '@type': 'Offer', name: 'Pro', price: '299000', priceCurrency: 'IDR', description: 'Semua Starter + AI Insight + Kitchen Display + Reservasi' },
    { '@type': 'Offer', name: 'Business', price: '499000', priceCurrency: 'IDR', description: 'Semua Pro + Multi Outlet + HQ Dashboard' },
  ],
};

export default function LandingPage() {
  const waLink = 'https://wa.me/6285270782220?text=Halo%20Kasira%2C%20saya%20tertarik%20untuk%20coba';

  return (
    <div className="min-h-screen bg-white font-sans">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Navbar />

      {/* ═══════════════ HERO ═══════════════ */}
      <section className="relative pt-28 pb-20 lg:pt-44 lg:pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(16,185,129,0.12),transparent)]" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
              <Flame className="w-4 h-4" />
              Dibuat khusus untuk F&B Indonesia
            </div>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight leading-[1.1] mb-6">
              Buka kasir,{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-teal-600">
                bukan spreadsheet
              </span>
            </h1>

            <p className="text-lg md:text-xl text-gray-500 mb-10 leading-relaxed max-w-2xl mx-auto">
              Capek itung manual di notes HP? Kasira bikin cafe lo punya sistem kasir + toko online + laporan otomatis. Setup 5 menit, langsung jalan.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/register"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-gray-900 text-white text-base font-bold rounded-xl hover:bg-gray-800 transition-all shadow-lg hover:-translate-y-0.5"
              >
                Coba Gratis 30 Hari
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/kasira-coffee"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-gray-700 text-base font-semibold rounded-xl border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all"
              >
                <Store className="w-4 h-4" />
                Lihat Demo Storefront
              </Link>
            </div>

            <p className="mt-4 text-sm text-gray-400">Tanpa kartu kredit. Cancel kapan saja.</p>
          </div>

          {/* ── Live Dashboard Preview ── */}
          <div className="mt-16 lg:mt-20 relative mx-auto max-w-5xl">
            <div className="absolute -inset-4 bg-gradient-to-b from-emerald-100/50 to-transparent rounded-3xl blur-2xl" />
            <div className="relative rounded-2xl overflow-hidden shadow-2xl border border-gray-200/80 bg-white">
              {/* Browser chrome */}
              <div className="bg-gray-100 px-4 py-2.5 flex items-center gap-3 border-b border-gray-200">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-gray-300" />
                  <div className="w-2.5 h-2.5 rounded-full bg-gray-300" />
                  <div className="w-2.5 h-2.5 rounded-full bg-gray-300" />
                </div>
                <div className="flex-1 bg-white rounded-md px-3 py-1 text-xs text-gray-400 text-center border border-gray-200">
                  kasira.online/dashboard
                </div>
              </div>

              {/* Dashboard content */}
              <div className="bg-gray-50 p-5 sm:p-8">
                {/* Stats row */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                  {[
                    { label: 'Revenue Hari Ini', value: 'Rp 2.847.000', icon: BarChart3, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                    { label: 'Total Pesanan', value: '63 order', icon: Receipt, color: 'text-blue-600', bg: 'bg-blue-50' },
                    { label: 'Produk Terjual', value: '147 item', icon: Package, color: 'text-violet-600', bg: 'bg-violet-50' },
                    { label: 'Rata-rata Order', value: 'Rp 45.190', icon: LineChart, color: 'text-amber-600', bg: 'bg-amber-50' },
                  ].map((stat, i) => (
                    <div key={i} className="bg-white rounded-xl p-4 border border-gray-100">
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`w-7 h-7 ${stat.bg} rounded-lg flex items-center justify-center`}>
                          <stat.icon className={`w-3.5 h-3.5 ${stat.color}`} />
                        </div>
                        <p className="text-xs text-gray-400 font-medium">{stat.label}</p>
                      </div>
                      <p className="text-lg font-bold text-gray-900">{stat.value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                  {/* Chart area */}
                  <div className="lg:col-span-3 bg-white rounded-xl border border-gray-100 p-4">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-sm font-semibold text-gray-700">Pendapatan 7 Hari</span>
                      <span className="text-xs text-emerald-600 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">+23%</span>
                    </div>
                    <div className="flex items-end gap-2 h-28">
                      {[40, 55, 35, 65, 50, 80, 70].map((h, i) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-1">
                          <div
                            className={`w-full rounded-md ${i === 5 ? 'bg-emerald-500' : 'bg-emerald-100'}`}
                            style={{ height: `${h}%` }}
                          />
                          <span className="text-[10px] text-gray-400">
                            {['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'][i]}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Best seller */}
                  <div className="lg:col-span-2 bg-white rounded-xl border border-gray-100 p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Star className="w-4 h-4 text-amber-500" />
                      <span className="text-sm font-semibold text-gray-700">Best Seller</span>
                    </div>
                    <div className="space-y-3">
                      {[
                        { rank: 1, name: 'Kopi Gula Aren', sold: 25, badge: 'bg-amber-400' },
                        { rank: 2, name: 'Bakwan Goreng', sold: 18, badge: 'bg-gray-400' },
                        { rank: 3, name: 'Kopi Hitam', sold: 10, badge: 'bg-amber-600' },
                      ].map((p) => (
                        <div key={p.rank} className="flex items-center gap-3">
                          <span className={`w-6 h-6 ${p.badge} text-white text-xs font-bold rounded-full flex items-center justify-center`}>
                            {p.rank}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                          </div>
                          <span className="text-xs text-gray-400 font-medium">{p.sold}x</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════ PAIN POINTS ═══════════════ */}
      <section className="py-16 bg-gray-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500 mb-8 uppercase tracking-widest font-medium">Masalah yang Kasira selesaikan</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                before: 'Tutup kasir harus itung cash manual, selisih terus',
                after: 'Shift auto-close — ringkasan cash, QRIS, selisih langsung keliatan',
                icon: CreditCard,
              },
              {
                before: 'Gak tau menu mana yang laku, stok tiba-tiba habis',
                after: 'Best seller auto-ranking + alert stok rendah otomatis',
                icon: Flame,
              },
              {
                before: 'Customer nanya "ada menu apa?" — kirim foto satu-satu',
                after: 'Storefront online gratis — customer tinggal buka link',
                icon: Globe,
              },
            ].map(({ before, after, icon: Icon }, i) => (
              <div key={i} className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                <div className="w-10 h-10 bg-gray-800 rounded-xl flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-emerald-400" />
                </div>
                <p className="text-gray-500 text-sm mb-3 line-through decoration-gray-700">{before}</p>
                <p className="text-white text-sm font-medium">{after}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════ FEATURES ═══════════════ */}
      <section id="features" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-20">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Satu app, semua kebutuhan cafe
            </h2>
            <p className="text-gray-500">
              Dari kasir sampai laporan. Dari offline sampai online.
            </p>
          </div>

          {/* Feature 1: POS */}
          <div className="grid lg:grid-cols-2 gap-12 items-center mb-24">
            <div>
              <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-xs font-bold px-3 py-1 rounded-full mb-4 uppercase tracking-wide">
                <Smartphone className="w-3.5 h-3.5" />
                Kasir
              </div>
              <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
                Ketuk. Bayar. Selesai.
              </h3>
              <p className="text-gray-500 mb-6 leading-relaxed">
                Buka app, pilih menu, terima pembayaran. Cash atau QRIS. Struk otomatis. Bahkan bisa jalan <strong>tanpa internet</strong> — data sync otomatis saat online.
              </p>
              <ul className="space-y-3">
                {[
                  'Input order dalam hitungan detik',
                  'Offline mode — tetap transaksi saat WiFi mati',
                  'Multi-kasir dengan shift & tutup kasir otomatis',
                  'Split bill & tab untuk customer reguler',
                ].map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            {/* POS Mockup */}
            <div className="bg-gray-100 rounded-2xl p-6 border border-gray-200">
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-bold text-gray-800">Kasira POS</span>
                  <span className="text-xs text-gray-400">Sab, 12 Apr 14:30</span>
                </div>
                <div className="grid grid-cols-3 gap-2 mb-4">
                  {[
                    { name: 'Kopi Gula Aren', price: 'Rp 21rb', hot: true },
                    { name: 'Bakwan Goreng', price: 'Rp 15rb', hot: true },
                    { name: 'Nasi Ayam', price: 'Rp 18rb', hot: false },
                    { name: 'Kopi Hitam', price: 'Rp 20rb', hot: false },
                    { name: 'Es Teh', price: 'Rp 8rb', hot: false },
                    { name: 'Fried Banana', price: 'Rp 15rb', hot: false },
                  ].map((item, i) => (
                    <div key={i} className="relative bg-gray-50 rounded-lg p-3 text-center border border-gray-100 hover:border-emerald-200 transition-colors">
                      {item.hot && (
                        <span className="absolute -top-1.5 -right-1.5 bg-amber-400 text-white text-[8px] font-bold px-1.5 py-0.5 rounded-full">Populer</span>
                      )}
                      <div className="w-full h-8 bg-gray-200 rounded mb-2" />
                      <p className="text-xs font-medium text-gray-800 truncate">{item.name}</p>
                      <p className="text-xs text-emerald-600 font-bold">{item.price}</p>
                    </div>
                  ))}
                </div>
                <div className="bg-emerald-500 text-white text-center py-2.5 rounded-lg text-sm font-bold">
                  Bayar Rp 54.000
                </div>
              </div>
            </div>
          </div>

          {/* Feature 2: Storefront */}
          <div className="grid lg:grid-cols-2 gap-12 items-center mb-24">
            <div className="order-2 lg:order-1">
              <div className="bg-gray-100 rounded-2xl p-6 border border-gray-200">
                <div className="bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100">
                  <div className="bg-emerald-600 p-4 text-white">
                    <p className="text-xs opacity-75">kasira.online/kasira-coffee</p>
                    <p className="text-lg font-bold mt-1">Kasira Coffee</p>
                    <p className="text-xs opacity-75">Jl. Contoh No. 123 &middot; Buka</p>
                  </div>
                  <div className="p-4 space-y-3">
                    {[
                      { name: 'Kopi Gula Aren', price: 'Rp 21.000', tag: 'Best Seller' },
                      { name: 'Bakwan Goreng', price: 'Rp 15.000', tag: null },
                      { name: 'Nasi Ayam', price: 'Rp 18.000', tag: null },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gray-100 rounded-lg" />
                          <div>
                            <p className="text-sm font-medium text-gray-800">{item.name}</p>
                            {item.tag && <span className="text-[10px] bg-amber-100 text-amber-700 font-bold px-1.5 py-0.5 rounded">{item.tag}</span>}
                          </div>
                        </div>
                        <p className="text-sm font-bold text-gray-900">{item.price}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="order-1 lg:order-2">
              <div className="inline-flex items-center gap-2 bg-violet-50 text-violet-700 text-xs font-bold px-3 py-1 rounded-full mb-4 uppercase tracking-wide">
                <Globe className="w-3.5 h-3.5" />
                Storefront
              </div>
              <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
                Toko online gratis, langsung jadi
              </h3>
              <p className="text-gray-500 mb-6 leading-relaxed">
                Begitu lo daftar dan masukin menu, storefront lo langsung live di <strong>kasira.online/nama-cafe</strong>. Customer tinggal klik, lihat menu + harga. Zero komisi, selamanya.
              </p>
              <ul className="space-y-3">
                {[
                  'URL cantik: kasira.online/nama-cafe-kamu',
                  'Menu, harga, foto update otomatis dari dashboard',
                  'Customer lihat stok real-time',
                  'Gak perlu coding, gak perlu hosting',
                ].map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/kasira-coffee"
                className="inline-flex items-center gap-2 mt-6 text-sm font-semibold text-emerald-600 hover:text-emerald-700 transition-colors"
              >
                Coba lihat storefront demo
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          {/* Feature 3: Dashboard + Laporan */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-amber-50 text-amber-700 text-xs font-bold px-3 py-1 rounded-full mb-4 uppercase tracking-wide">
                <BarChart3 className="w-3.5 h-3.5" />
                Dashboard
              </div>
              <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
                Tau persis bisnis lo hari ini
              </h3>
              <p className="text-gray-500 mb-6 leading-relaxed">
                Revenue, best seller, stok kritis, laporan shift — semua di satu layar. Buka dari HP, laptop, kapan aja. Gak perlu nunggu admin kirim rekap Excel.
              </p>
              <ul className="space-y-3">
                {[
                  'Revenue harian, mingguan, per-produk',
                  'Best seller ranking otomatis',
                  'Alert stok rendah real-time',
                  'Tax & service charge (PB1 + SC)',
                  'Pro: AI insight dikirim via WhatsApp',
                ].map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-gray-100 rounded-2xl p-6 border border-gray-200">
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <p className="text-sm font-bold text-gray-800 mb-3">Ringkasan Shift #4</p>
                <div className="space-y-2 text-sm">
                  {[
                    { label: 'Total Order', value: '23 order' },
                    { label: 'Cash', value: 'Rp 1.245.000' },
                    { label: 'QRIS', value: 'Rp 847.000' },
                    { label: 'PB1 (10%)', value: 'Rp 209.200' },
                    { label: 'Service (5%)', value: 'Rp 104.600' },
                  ].map((row, i) => (
                    <div key={i} className="flex justify-between py-1.5 border-b border-gray-50">
                      <span className="text-gray-500">{row.label}</span>
                      <span className="font-semibold text-gray-800">{row.value}</span>
                    </div>
                  ))}
                  <div className="flex justify-between pt-2">
                    <span className="font-bold text-gray-900">Total Revenue</span>
                    <span className="font-bold text-emerald-600 text-base">Rp 2.405.800</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════ MORE FEATURES GRID ═══════════════ */}
      <section className="py-16 bg-gray-50 border-y border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: WifiOff, title: 'Offline Mode', desc: 'Tetap transaksi saat WiFi mati' },
              { icon: Users, title: 'Multi Kasir', desc: 'Shift per kasir, tutup kasir otomatis' },
              { icon: ChefHat, title: 'Kitchen Display', desc: 'Order masuk langsung ke layar dapur', pro: true },
              { icon: Sparkles, title: 'AI Insight', desc: 'Laporan harian otomatis via WA', pro: true },
              { icon: Shield, title: 'Data Aman', desc: 'Enkripsi AES-256, server Indonesia' },
              { icon: Receipt, title: 'Struk Otomatis', desc: 'Print thermal atau struk digital' },
              { icon: CreditCard, title: 'QRIS', desc: 'Terima pembayaran digital, zero komisi' },
              { icon: Clock, title: 'Reservasi Meja', desc: 'Booking meja online dari storefront', pro: true },
            ].map(({ icon: Icon, title, desc, pro }, i) => (
              <div key={i} className="bg-white rounded-xl p-5 border border-gray-100 hover:border-emerald-200 hover:shadow-sm transition-all">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-bold text-gray-900">{title}</span>
                  {pro && <span className="text-[10px] bg-amber-100 text-amber-700 font-bold px-1.5 py-0.5 rounded">PRO</span>}
                </div>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════ HOW IT WORKS ═══════════════ */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Mulai dalam 5 menit</h2>
            <p className="text-gray-500 mt-3">Gak perlu training. Gak perlu teknisi.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 relative">
            <div className="hidden md:block absolute top-10 left-[20%] right-[20%] h-px bg-gray-200 border-dashed" />
            {[
              { step: '1', title: 'Daftar via WA', desc: 'Masukkan nomor WhatsApp, verifikasi OTP. 30 detik selesai.' },
              { step: '2', title: 'Input menu lo', desc: 'Tambah produk, set harga, upload foto. Storefront langsung live.' },
              { step: '3', title: 'Download app kasir', desc: 'Install di Android, login, mulai terima order hari ini juga.' },
            ].map(({ step, title, desc }, i) => (
              <div key={i} className="relative text-center">
                <div className="w-16 h-16 mx-auto bg-gray-900 rounded-2xl flex items-center justify-center mb-4 relative z-10 shadow-lg">
                  <span className="text-xl font-black text-white">{step}</span>
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm max-w-xs mx-auto">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════ PRICING ═══════════════ */}
      <section id="pricing" className="py-24 bg-gray-50 border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Harga jelas, gak ada biaya tersembunyi</h2>
            <p className="text-gray-500">Semua plan termasuk storefront gratis + offline mode</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {/* STARTER */}
            <div className="bg-white rounded-2xl p-7 border-2 border-gray-900 shadow-lg relative flex flex-col">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs font-bold px-4 py-1 rounded-full whitespace-nowrap">
                Paling Populer
              </div>
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-1">Starter</h3>
                <p className="text-sm text-gray-400 mb-4">Warung, kantin, toko kecil</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-gray-900">99rb</span>
                  <span className="text-gray-400 text-sm">/bulan</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                {['1 kasir + 1 outlet', 'Max 500 produk', 'Cash + QRIS', 'Storefront gratis', 'Laporan harian', 'Manajemen stok + alert', 'Offline mode', 'Email support'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link href="/register"
                className="w-full block text-center px-5 py-3 bg-gray-900 text-white font-bold rounded-xl hover:bg-gray-800 transition-colors text-sm">
                Mulai Gratis 30 Hari
              </Link>
            </div>

            {/* PRO */}
            <div className="bg-white rounded-2xl p-7 border border-gray-200 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-1">Pro</h3>
                <p className="text-sm text-gray-400 mb-4">Coffee shop & cafe</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-gray-900">299rb</span>
                  <span className="text-gray-400 text-sm">/bulan</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                <li className="text-xs font-bold text-emerald-600 uppercase tracking-wide pb-2 border-b border-gray-100">Semua Starter +</li>
                {['Max 5 kasir', 'Unlimited produk', 'Kitchen display', 'AI daily insight via WA', 'Loyalty points', 'Reservasi meja', 'Split bill & tab', 'Resep + HPP tracking', 'Priority WA support'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-gray-600">
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

            {/* BUSINESS */}
            <div className="bg-white rounded-2xl p-7 border border-gray-200 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-1">Business</h3>
                <p className="text-sm text-gray-400 mb-4">Resto chain & multi outlet</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-gray-900">499rb</span>
                  <span className="text-gray-400 text-sm">/bulan</span>
                </div>
              </div>
              <ul className="space-y-3 mb-7 flex-1 text-sm">
                <li className="text-xs font-bold text-emerald-600 uppercase tracking-wide pb-2 border-b border-gray-100">Semua Pro +</li>
                {['Unlimited kasir & outlet', 'HQ dashboard', 'Transfer stok antar outlet', 'Prediksi stok & revenue', 'Custom domain storefront', 'Dedicated account manager'].map((f, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-gray-600">
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
          </div>
        </div>
      </section>

      {/* ═══════════════ FAQ ═══════════════ */}
      <FAQ />

      {/* ═══════════════ CTA ═══════════════ */}
      <section className="py-24 bg-gray-900 relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-5xl font-extrabold text-white mb-4">
            Cafe lo layak punya sistem yang proper
          </h2>
          <p className="text-gray-400 text-lg mb-10 max-w-xl mx-auto">
            Mulai dari Rp 99rb/bulan. Gratis 30 hari pertama. Kami bantu setup dari nol.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-8 py-4 bg-emerald-500 text-white text-base font-bold rounded-xl hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/25 hover:-translate-y-0.5"
            >
              Daftar Gratis Sekarang
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href={waLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white/10 text-white text-base font-semibold rounded-xl hover:bg-white/20 transition-all border border-white/10"
            >
              <MessageCircle className="w-4 h-4" />
              Tanya via WhatsApp
            </a>
          </div>
        </div>
      </section>

      {/* ═══════════════ FOOTER ═══════════════ */}
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
              <Link href="/download" className="text-gray-400 hover:text-white transition-colors">Download</Link>
              <Link href="/kasira-coffee" className="text-gray-400 hover:text-white transition-colors">Demo</Link>
              <Link href="/login" className="text-gray-400 hover:text-white transition-colors">Login</Link>
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:text-emerald-300 transition-colors">WhatsApp</a>
            </div>
          </div>
          <div className="pt-8 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-500 text-sm">&copy; 2026 Kasira. All rights reserved.</p>
            <p className="text-gray-600 text-sm">POS digital untuk UMKM Indonesia</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
