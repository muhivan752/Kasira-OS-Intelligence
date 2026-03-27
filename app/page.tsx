import Link from 'next/link';
import Image from 'next/image';
import { 
  Store, 
  Smartphone, 
  Globe, 
  LineChart, 
  Package, 
  Sparkles, 
  Link as LinkIcon,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import Navbar from '@/components/landing/Navbar';
import FAQ from '@/components/landing/FAQ';
import { Logo } from '@/components/ui/logo';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-50 font-sans selection:bg-emerald-100 selection:text-emerald-900">
      <Navbar />

      {/* SECTION 2 — HERO */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden bg-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-emerald-50 via-white to-white" />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-5xl md:text-7xl font-extrabold text-gray-900 tracking-tight leading-[1.1] mb-8">
              Kasir Digital untuk <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-emerald-700">
                UMKM Indonesia
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 mb-10 leading-relaxed max-w-2xl mx-auto">
              POS modern dengan storefront gratis, QRIS tanpa komisi, dan AI insight yang bantu bisnis lo berkembang.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
              <Link 
                href="/onboarding"
                className="w-full sm:w-auto px-8 py-4 bg-emerald-500 text-white text-lg font-semibold rounded-full hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 hover:-translate-y-0.5"
              >
                Coba Gratis 30 Hari
              </Link>
              <Link 
                href="/warung-demo"
                className="w-full sm:w-auto px-8 py-4 bg-white text-gray-900 text-lg font-semibold rounded-full border-2 border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all"
              >
                Lihat Demo
              </Link>
            </div>
            
            <p className="text-sm text-gray-500 font-medium">
              Tidak perlu kartu kredit · Gratis 30 hari · Cancel kapan saja
            </p>
          </div>

          {/* Hero Image/Mockup */}
          <div className="mt-20 relative mx-auto max-w-5xl">
            <div className="aspect-[16/9] rounded-2xl overflow-hidden shadow-2xl border border-gray-200/50 bg-gray-900 relative">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-emerald-900/40 mix-blend-overlay z-10" />
              <Image 
                src="https://picsum.photos/seed/kasir/1920/1080" 
                alt="Kasira Dashboard" 
                fill 
                className="object-cover opacity-90"
                referrerPolicy="no-referrer"
              />
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3 — SOCIAL PROOF BAR */}
      <section className="py-12 bg-gray-900 text-white border-y border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center divide-x divide-gray-800">
            <div>
              <div className="text-3xl md:text-4xl font-bold text-emerald-400 mb-2">500+</div>
              <div className="text-sm text-gray-400 font-medium tracking-wide uppercase">Outlet Aktif</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-emerald-400 mb-2">Rp 2M+</div>
              <div className="text-sm text-gray-400 font-medium tracking-wide uppercase">Transaksi Diproses</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-emerald-400 mb-2">4.9/5</div>
              <div className="text-sm text-gray-400 font-medium tracking-wide uppercase">Rating</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-emerald-400 mb-2">Zero</div>
              <div className="text-sm text-gray-400 font-medium tracking-wide uppercase">Komisi Storefront</div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4 — FITUR UNGGULAN */}
      <section id="features" className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight mb-4">
              Semua yang lo butuhkan, dalam satu aplikasi
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Card 1 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6">
                <Smartphone className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Kasir Digital</h3>
              <p className="text-gray-600 leading-relaxed">
                Input order, QRIS, struk WA otomatis. Offline mode — tetap jalan tanpa internet.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6">
                <Globe className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Storefront Gratis</h3>
              <p className="text-gray-600 leading-relaxed">
                kasira.id/&#123;nama-outlet&#125; aktif otomatis. Zero komisi selamanya. Customer bisa order online.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6">
                <LineChart className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Dashboard Owner</h3>
              <p className="text-gray-600 leading-relaxed">
                Lihat revenue real-time, stok kritis, dan laporan harian dari HP manapun.
              </p>
            </div>

            {/* Card 4 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6">
                <Package className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Manajemen Stok</h3>
              <p className="text-gray-600 leading-relaxed">
                Stok auto-deduct setiap transaksi. Alert WA kalau stok hampir habis.
              </p>
            </div>

            {/* Card 5 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow relative overflow-hidden">
              <div className="absolute top-6 right-6 bg-gradient-to-r from-amber-200 to-amber-400 text-amber-900 text-xs font-bold px-3 py-1 rounded-full">PRO</div>
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6">
                <Sparkles className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">AI Insight</h3>
              <p className="text-gray-600 leading-relaxed">
                AI kasih insight harian via WA: menu terlaris, jam ramai, saran promo.
              </p>
            </div>

            {/* Card 6 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow relative overflow-hidden">
              <div className="absolute top-6 right-6 bg-gradient-to-r from-amber-200 to-amber-400 text-amber-900 text-xs font-bold px-3 py-1 rounded-full">PRO</div>
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6">
                <LinkIcon className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Multi-Channel</h3>
              <p className="text-gray-600 leading-relaxed">
                Self-order QR di meja, kitchen display, dan integrasi GrabFood/GoFood.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5 — HOW IT WORKS */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">
              Mulai dalam 5 menit
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-12 relative">
            {/* Connection Line (Desktop) */}
            <div className="hidden md:block absolute top-12 left-[15%] right-[15%] h-0.5 bg-gray-100" />

            {/* Step 1 */}
            <div className="relative text-center">
              <div className="w-24 h-24 mx-auto bg-white border-4 border-emerald-50 rounded-full flex items-center justify-center mb-6 relative z-10 shadow-sm">
                <span className="text-3xl font-black text-emerald-500">1</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Daftar dengan nomor WA</h3>
              <p className="text-gray-600">
                Tidak perlu email atau password. OTP WA, langsung masuk.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative text-center">
              <div className="w-24 h-24 mx-auto bg-white border-4 border-emerald-50 rounded-full flex items-center justify-center mb-6 relative z-10 shadow-sm">
                <span className="text-3xl font-black text-emerald-500">2</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Input menu pertama</h3>
              <p className="text-gray-600">
                Tambah menu beserta harga. Storefront otomatis aktif.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative text-center">
              <div className="w-24 h-24 mx-auto bg-white border-4 border-emerald-50 rounded-full flex items-center justify-center mb-6 relative z-10 shadow-sm">
                <span className="text-3xl font-black text-emerald-500">3</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Download app kasir</h3>
              <p className="text-gray-600">
                Install APK di HP atau tablet. Kasir siap transaksi hari ini.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6 — PRICING */}
      <section id="pricing" className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight mb-4">
              Harga yang terjangkau untuk semua skala bisnis
            </h2>
            <p className="text-xl text-gray-600">
              Mulai gratis 30 hari, cancel kapan saja
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* STARTER */}
            <div className="bg-white rounded-3xl p-8 border-2 border-emerald-500 shadow-xl relative flex flex-col">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-emerald-500 text-white text-sm font-bold px-4 py-1 rounded-full">
                Paling Populer
              </div>
              <div className="mb-8">
                <h3 className="text-xl font-bold text-gray-900 mb-2">STARTER</h3>
                <p className="text-sm text-gray-500 mb-4 h-10">Target: Warung & toko kecil</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-gray-900">Rp 99rb</span>
                  <span className="text-gray-500">/bulan</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 flex-1">
                {[
                  'Max 3 kasir',
                  'Max 500 produk',
                  'Cash + QRIS Midtrans',
                  'Struk WA otomatis',
                  'Simple stock management',
                  'Laporan harian',
                  'Storefront gratis (pickup & delivery)',
                  'Email support'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-600">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Link 
                href="/onboarding"
                className="w-full block text-center px-6 py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors"
              >
                Mulai Gratis
              </Link>
            </div>

            {/* PRO */}
            <div className="bg-white rounded-3xl p-8 border border-gray-200 shadow-sm flex flex-col">
              <div className="mb-8">
                <h3 className="text-xl font-bold text-gray-900 mb-2">PRO</h3>
                <p className="text-sm text-gray-500 mb-4 h-10">Target: Coffee shop & cafe</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-gray-900">Rp 299rb</span>
                  <span className="text-gray-500">/bulan</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 flex-1">
                <li className="text-sm font-bold text-gray-900 pb-2 border-b border-gray-100">Semua fitur Starter, plus:</li>
                {[
                  'Max 10 kasir',
                  'Unlimited produk',
                  'Self-order QR di meja',
                  'Kitchen display realtime',
                  'AI daily summary WA',
                  'AI chatbot owner',
                  'Recipe-based stock + HPP',
                  'Export Excel/PDF',
                  'Priority WA support'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-600">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Link 
                href="/onboarding"
                className="w-full block text-center px-6 py-3 bg-gray-900 text-white font-bold rounded-xl hover:bg-gray-800 transition-colors"
              >
                Mulai Gratis
              </Link>
            </div>

            {/* BUSINESS */}
            <div className="bg-white rounded-3xl p-8 border border-gray-200 shadow-sm flex flex-col">
              <div className="mb-8">
                <h3 className="text-xl font-bold text-gray-900 mb-2">BUSINESS</h3>
                <p className="text-sm text-gray-500 mb-4 h-10">Target: Resto & cafe chain</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-gray-900">Rp 499rb</span>
                  <span className="text-gray-500">/bulan</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 flex-1">
                <li className="text-sm font-bold text-gray-900 pb-2 border-b border-gray-100">Semua fitur Pro, plus:</li>
                {[
                  'Unlimited kasir',
                  'Multi outlet (add-on Rp 99rb/outlet)',
                  'HQ dashboard cross-outlet',
                  'Pilot Otomatis rule engine',
                  'Prediksi stok + revenue',
                  'Transfer stok antar outlet',
                  'WA support + onboarding session'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-600">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <a 
                href="mailto:sales@kasira.id"
                className="w-full block text-center px-6 py-3 bg-white text-gray-900 border-2 border-gray-200 font-bold rounded-xl hover:bg-gray-50 transition-colors"
              >
                Hubungi Kami
              </a>
            </div>

            {/* ENTERPRISE */}
            <div className="bg-gray-900 rounded-3xl p-8 border border-gray-800 shadow-sm flex flex-col text-white">
              <div className="mb-8">
                <h3 className="text-xl font-bold text-white mb-2">ENTERPRISE</h3>
                <p className="text-sm text-gray-400 mb-4 h-10">Target: Grup usaha multi-brand</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-white">Rp 1.499rb</span>
                  <span className="text-gray-400">/bln</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 flex-1">
                <li className="text-sm font-bold text-white pb-2 border-b border-gray-800">Semua fitur Business, plus:</li>
                {[
                  '5 brand + 10 outlet included',
                  'AI autonomous',
                  'White label APK',
                  'Custom domain storefront',
                  'SLA 99.9% uptime',
                  'Dedicated account manager'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <a 
                href="mailto:sales@kasira.id"
                className="w-full block text-center px-6 py-3 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-colors"
              >
                Hubungi Kami
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 7 — STOREFRONT PREVIEW */}
      <section className="py-24 bg-white overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-5xl font-bold text-gray-900 tracking-tight mb-6 leading-tight">
                Storefront gratis untuk setiap outlet
              </h2>
              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                <span className="font-mono bg-gray-100 px-2 py-1 rounded text-emerald-600">kasira.id/&#123;nama-outlet&#125;</span> aktif otomatis saat lo daftar. Zero komisi selamanya.
              </p>
              
              <ul className="space-y-6 mb-10">
                {[
                  'Link unik per outlet',
                  'Pickup & delivery',
                  'Bayar QRIS langsung'
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    </div>
                    <span className="text-lg font-medium text-gray-900">{item}</span>
                  </li>
                ))}
              </ul>
              
              <Link 
                href="/warung-demo"
                className="inline-flex items-center gap-2 px-8 py-4 bg-gray-900 text-white text-lg font-bold rounded-full hover:bg-gray-800 transition-colors"
              >
                Lihat Contoh Storefront
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
            
            <div className="relative">
              <div className="absolute inset-0 bg-emerald-500/10 rounded-full blur-3xl" />
              <div className="relative mx-auto w-full max-w-[320px] aspect-[9/19] bg-gray-900 rounded-[2.5rem] border-[8px] border-gray-900 shadow-2xl overflow-hidden">
                <Image 
                  src="https://picsum.photos/seed/storefront/600/1200" 
                  alt="Storefront Preview" 
                  fill 
                  className="object-cover"
                  referrerPolicy="no-referrer"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 8 — FAQ */}
      <FAQ />

      {/* SECTION 9 — CTA FINAL */}
      <section className="relative py-24 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500 to-emerald-700" />
        <div className="absolute inset-0 bg-[url('https://picsum.photos/seed/pattern/1920/1080')] opacity-10 mix-blend-overlay" />
        
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl md:text-6xl font-extrabold text-white tracking-tight mb-6">
            Siap modernisasi bisnis lo?
          </h2>
          <p className="text-xl text-emerald-100 mb-10 max-w-2xl mx-auto">
            Bergabung dengan ratusan outlet yang sudah pakai Kasira.
          </p>
          
          <Link 
            href="/onboarding"
            className="inline-block px-10 py-5 bg-white text-emerald-600 text-xl font-bold rounded-full hover:bg-gray-50 transition-all shadow-xl hover:-translate-y-1 hover:shadow-2xl"
          >
            Coba Gratis 30 Hari Sekarang
          </Link>
          
          <p className="mt-6 text-emerald-200 font-medium">
            Setup 5 menit · Tidak perlu kartu kredit
          </p>
        </div>
      </section>

      {/* SECTION 10 — FOOTER */}
      <footer className="bg-gray-900 py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <Logo size="md" variant="dark" />
            </div>
            
            <div className="flex flex-wrap justify-center gap-8">
              <Link href="#features" className="text-gray-400 hover:text-white transition-colors">Fitur</Link>
              <Link href="#pricing" className="text-gray-400 hover:text-white transition-colors">Harga</Link>
              <Link href="/warung-demo" className="text-gray-400 hover:text-white transition-colors">Demo</Link>
              <Link href="/login" className="text-gray-400 hover:text-white transition-colors">Login</Link>
            </div>
          </div>
          
          <div className="mt-12 pt-8 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-500 text-sm">
              © 2026 Kasira. All rights reserved.
            </p>
            <p className="text-gray-500 text-sm flex items-center gap-1">
              POS Digital untuk UMKM Indonesia · Made with <span className="text-red-500">❤️</span> in Indonesia
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
