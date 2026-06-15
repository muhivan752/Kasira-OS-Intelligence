import Link from 'next/link';
import {
  Smartphone, Globe, LineChart, Package,
  Sparkles, CheckCircle2, ArrowRight, MessageCircle,
  Shield, Wifi, WifiOff, Receipt,
  ChefHat, BarChart3, Users, Star,
  Clock, Flame, CreditCard, Store, LayoutDashboard, QrCode
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

const organizationLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Kasira',
  url: 'https://kasira.online',
  logo: 'https://kasira.online/favicon.svg',
  description: 'Platform POS digital untuk UMKM dan bisnis F&B Indonesia.',
  contactPoint: {
    '@type': 'ContactPoint',
    telephone: '+62-852-7078-2220',
    contactType: 'customer service',
    availableLanguage: 'Indonesian',
  },
};

const faqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'Apakah benar-benar gratis 30 hari?',
      acceptedAnswer: { '@type': 'Answer', text: 'Ya, gratis penuh 30 hari tanpa perlu kartu kredit. Cancel kapan saja.' },
    },
    {
      '@type': 'Question',
      name: 'Apakah QRIS ada biaya komisi ke Kasira?',
      acceptedAnswer: { '@type': 'Answer', text: 'Tidak ada. Kasira zero komisi selamanya. Lo daftar Midtrans sendiri, uang langsung masuk ke rekening lo.' },
    },
    {
      '@type': 'Question',
      name: 'Bisa pakai di HP Android biasa?',
      acceptedAnswer: { '@type': 'Answer', text: 'Ya, app kasir bisa diinstall di HP Android manapun. Tidak perlu tablet khusus.' },
    },
    {
      '@type': 'Question',
      name: 'Bagaimana kalau internet mati?',
      acceptedAnswer: { '@type': 'Answer', text: 'App kasir tetap bisa transaksi saat offline. Data otomatis sync saat internet kembali.' },
    },
    {
      '@type': 'Question',
      name: 'Apakah data saya aman?',
      acceptedAnswer: { '@type': 'Answer', text: 'Data tersimpan di server Indonesia dengan enkripsi AES-256. Backup otomatis tiap 6 jam.' },
    },
  ],
};

export default function LandingPage() {
  const waLink = 'https://wa.me/6285270782220?text=Halo%20Kasira%2C%20saya%20tertarik%20untuk%20coba';

  return (
    <div className="min-h-screen bg-[#FAFAFA] font-sans selection:bg-emerald-500/30 selection:text-emerald-900">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }} />
      <Navbar />

      {/* ═══════════════ HERO ═══════════════ */}
      <section className="relative pt-32 pb-24 lg:pt-48 lg:pb-32 overflow-hidden">
        {/* Soft, premium ambient background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-emerald-400/20 opacity-60 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute -top-32 right-0 w-[500px] h-[500px] bg-teal-400/10 blur-[100px] rounded-full pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-white border border-gray-200/80 shadow-sm text-gray-700 text-sm font-medium px-4 py-1.5 rounded-full mb-8 hover:border-emerald-200 hover:bg-emerald-50 transition-all cursor-default">
              <Sparkles className="w-4 h-4 text-emerald-500" />
              Sistem kasir generasi baru untuk F&B Indonesia
            </div>

            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-slate-900 tracking-tight leading-[1.05] mb-8">
              Bikin cafe lo makin pro,<br className="hidden md:block" />
              <span className="relative inline-block mt-2">
                <span className="relative z-10 text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">
                  tanpa ribet urus IT.
                </span>
              </span>
            </h1>

            <p className="text-lg md:text-xl text-slate-600 mb-10 leading-relaxed max-w-2xl mx-auto font-medium">
              Tinggalkan cara lama pakai kertas dan excel. Dari terima pesanan, pantau stok bahan, sampai punya website jualan sendiri—semua beres dalam satu aplikasi.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/register"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-slate-900 text-white text-base font-semibold rounded-2xl hover:bg-slate-800 transition-all shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.2)] hover:-translate-y-0.5 active:translate-y-0"
              >
                Mulai Gratis 30 Hari
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/kasira-coffee"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-slate-700 text-base font-semibold rounded-2xl border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all shadow-sm"
              >
                <Store className="w-4 h-4 text-emerald-600" />
                Lihat Demo Toko
              </Link>
            </div>
            
            <div className="mt-8 flex items-center justify-center gap-6 text-sm text-slate-500 font-medium">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Tanpa kartu kredit
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Batal kapan saja
              </div>
            </div>
          </div>

          {/* ── Premium Mockup Showcase ── */}
          <div className="mt-20 relative mx-auto max-w-5xl group perspective-1000">
            <div className="absolute -inset-1 bg-gradient-to-b from-emerald-400/20 to-transparent rounded-[32px] blur-xl opacity-0 transition-opacity duration-700 group-hover:opacity-100" />
            <div className="relative rounded-[24px] overflow-hidden shadow-[0_20px_50px_rgb(0,0,0,0.1)] border border-gray-200/80 bg-white/80 backdrop-blur-xl transform transition-transform duration-700 hover:scale-[1.01] hover:-rotate-1">
              
              {/* Fake macOS Window Header */}
              <div className="bg-slate-50/90 px-4 py-3 flex items-center gap-4 border-b border-gray-200/80">
                <div className="flex gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-400/80" />
                  <div className="w-3 h-3 rounded-full bg-amber-400/80" />
                  <div className="w-3 h-3 rounded-full bg-emerald-400/80" />
                </div>
                <div className="flex-1 flex justify-center">
                  <div className="bg-white/60 rounded-md px-3 py-1.5 text-[11px] font-medium text-slate-500 flex items-center gap-2 border border-gray-200/50 w-64 justify-center shadow-sm">
                    <Shield className="w-3 h-3" /> kasira.online/dashboard
                  </div>
                </div>
                <div className="w-12" /> {/* Spacer */}
              </div>

              {/* Dashboard content */}
              <div className="bg-slate-50/50 p-6 sm:p-8">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  {[
                    { label: 'Omzet Hari Ini', value: 'Rp 2.847.000', icon: BarChart3, color: 'text-emerald-600', bg: 'bg-emerald-100/50', trend: '+12%' },
                    { label: 'Total Pesanan', value: '63', icon: Receipt, color: 'text-blue-600', bg: 'bg-blue-100/50', trend: '+5%' },
                    { label: 'Produk Terjual', value: '147', icon: Package, color: 'text-violet-600', bg: 'bg-violet-100/50', trend: '-2%' },
                    { label: 'Rata-rata Order', value: 'Rp 45.190', icon: LineChart, color: 'text-amber-600', bg: 'bg-amber-100/50', trend: '+8%' },
                  ].map((stat, i) => (
                    <div key={i} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <div className={`w-10 h-10 ${stat.bg} rounded-xl flex items-center justify-center`}>
                          <stat.icon className={`w-5 h-5 ${stat.color}`} />
                        </div>
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${stat.trend.startsWith('+') ? 'text-emerald-700 bg-emerald-50' : 'text-rose-700 bg-rose-50'}`}>
                          {stat.trend}
                        </span>
                      </div>
                      <p className="text-sm text-slate-500 font-medium mb-1">{stat.label}</p>
                      <p className="text-2xl font-bold text-slate-900 tracking-tight">{stat.value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                    <div className="flex items-center justify-between mb-8">
                      <h3 className="text-base font-bold text-slate-900">Grafik Penjualan</h3>
                      <select className="text-sm bg-slate-50 border border-gray-200 rounded-lg px-3 py-1.5 text-slate-600 font-medium outline-none">
                         <option>7 Hari Terakhir</option>
                      </select>
                    </div>
                    <div className="flex items-end gap-3 h-40">
                      {[40, 55, 35, 65, 50, 80, 70].map((h, i) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-3 group/bar">
                          <div className="w-full relative rounded-t-lg bg-emerald-100/60 overflow-hidden transition-all duration-500 hover:bg-emerald-200" style={{ height: `${h}%` }}>
                            {i === 5 && <div className="absolute inset-0 bg-gradient-to-t from-emerald-500 to-emerald-400 shadow-[inset_0_2px_4px_rgba(255,255,255,0.3)]" />}
                          </div>
                          <span className={`text-xs font-medium ${i === 5 ? 'text-emerald-600' : 'text-slate-400'}`}>
                            {['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'][i]}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                    <h3 className="text-base font-bold text-slate-900 mb-6">Menu Paling Laku</h3>
                    <div className="space-y-4">
                      {[
                        { rank: 1, name: 'Kopi Gula Aren', sold: 25, price: 'Rp 21.000' },
                        { rank: 2, name: 'Croissant Butter', sold: 18, price: 'Rp 25.000' },
                        { rank: 3, name: 'Es Teh Manis', sold: 10, price: 'Rp 8.000' },
                        { rank: 4, name: 'Nasi Goreng Spesial', sold: 8, price: 'Rp 35.000' },
                      ].map((p) => (
                        <div key={p.rank} className="flex items-center gap-3 group/item cursor-default">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${p.rank === 1 ? 'bg-amber-100 text-amber-700' : p.rank === 2 ? 'bg-slate-100 text-slate-600' : 'bg-orange-50 text-orange-600'}`}>
                            #{p.rank}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-800 truncate group-hover/item:text-emerald-600 transition-colors">{p.name}</p>
                            <p className="text-xs text-slate-500">{p.sold} terjual</p>
                          </div>
                          <div className="text-sm font-bold text-slate-700">{p.price}</div>
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

      {/* ═══════════════ SOCIAL PROOF ═══════════════ */}
      <section className="py-10 border-y border-gray-200/60 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-6">Solusi tepercaya untuk bisnis masa kini</p>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-8 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
             {/* Dummy Logos representation */}
             <div className="flex items-center gap-2 text-xl font-black text-slate-800"><CoffeeIcon /> Kopi Kenangan</div>
             <div className="flex items-center gap-2 text-xl font-bold text-slate-800 font-serif"><ChefHat /> Warung Pak Min</div>
             <div className="flex items-center gap-2 text-xl font-bold text-slate-800 italic"><Flame /> Sate Taichan Senayan</div>
             <div className="flex items-center gap-2 text-xl font-bold text-slate-800"><Store /> Kios Kopi</div>
          </div>
        </div>
      </section>

      {/* ═══════════════ BENTO GRID FEATURES ═══════════════ */}
      <section id="features" className="py-24 bg-[#FAFAFA]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl mb-16">
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">
              Bukan cuma aplikasi kasir biasa.
            </h2>
            <p className="text-lg text-slate-600 leading-relaxed font-medium">
              Sistem kasir cerdas yang didesain buat ngertiin pusingnya operasional resto & cafe. Semua beres di satu tempat.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Bento 1: POS & Offline */}
            <div className="md:col-span-2 bg-white rounded-3xl p-8 border border-gray-200/80 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                  <Smartphone className="w-48 h-48" />
               </div>
               <div className="relative z-10 w-full md:w-2/3">
                  <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mb-6">
                    <WifiOff className="w-6 h-6" />
                  </div>
                  <h3 className="text-2xl font-bold text-slate-900 mb-3">Tahan Banting, Walau Internet Mati.</h3>
                  <p className="text-slate-600 leading-relaxed mb-6">
                    Mati lampu? WiFi ngadat? Jangan panik. Kasir tetap bisa jalan buat terima pesanan dan bayaran. Data akan disinkron otomatis ke awan begitu internet nyala lagi.
                  </p>
                  <ul className="space-y-3">
                    {['Sinkronisasi data otomatis via CRDT', 'Support print struk bluetooth offline', 'Catat split bill dan open tab'].map((item, i) => (
                       <li key={i} className="flex items-center gap-3 text-sm font-medium text-slate-700">
                         <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center"><CheckCircle2 className="w-3 h-3 text-emerald-600" /></div>
                         {item}
                       </li>
                    ))}
                  </ul>
               </div>
            </div>

            {/* Bento 2: QRIS */}
            <div className="bg-white rounded-3xl p-8 border border-gray-200/80 shadow-sm hover:shadow-md transition-shadow">
               <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mb-6">
                 <QrCode className="w-6 h-6" />
               </div>
               <h3 className="text-xl font-bold text-slate-900 mb-3">Terima QRIS, Bebas Potongan.</h3>
               <p className="text-slate-600 leading-relaxed text-sm">
                 Terima pembayaran dari dompet digital mana aja tanpa ada embel-embel komisi terselubung dari Kasira. Uang langsung cair ke rekening kamu.
               </p>
            </div>

            {/* Bento 3: Storefront */}
            <div className="bg-slate-900 rounded-3xl p-8 border border-slate-800 shadow-xl overflow-hidden relative group text-white">
               <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent" />
               <div className="relative z-10">
                 <div className="w-12 h-12 bg-slate-800 text-emerald-400 rounded-2xl flex items-center justify-center mb-6 border border-slate-700">
                   <Globe className="w-6 h-6" />
                 </div>
                 <h3 className="text-xl font-bold mb-3 text-white">Website Toko Jadi Detik Itu Juga.</h3>
                 <p className="text-slate-400 leading-relaxed text-sm mb-6">
                   Tinggal daftar, website toko kamu langsung live: <span className="text-emerald-400 font-mono">kasira.online/namamu</span>. Bagikan ke WA atau Instagram, biarkan pembeli order sendiri.
                 </p>
                 <Link href="/kasira-coffee" className="inline-flex items-center text-sm font-bold text-white hover:text-emerald-400 transition-colors">
                   Lihat contoh toko <ArrowRight className="w-4 h-4 ml-2" />
                 </Link>
               </div>
            </div>

            {/* Bento 4: AI & Dashboard */}
            <div className="md:col-span-2 bg-white rounded-3xl p-8 border border-gray-200/80 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
               <div className="flex flex-col md:flex-row gap-8 items-center">
                 <div className="flex-1">
                    <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-2xl flex items-center justify-center mb-6">
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-3">AI Laporan Langsung ke WhatsApp.</h3>
                    <p className="text-slate-600 leading-relaxed mb-6">
                      Nggak perlu pusing baca grafik. AI Kasira bakal kirim rangkuman harian: menu apa yang laris manis, jam berapa paling rame, dan saran stok buat besok.
                    </p>
                    <div className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl border border-gray-100 w-max">
                      <div className="w-8 h-8 bg-[#25D366] rounded-full flex items-center justify-center text-white"><MessageCircle className="w-4 h-4" /></div>
                      <span className="text-sm font-semibold text-slate-700">"Bos, hari ini omzet naik 15%!"</span>
                    </div>
                 </div>
                 <div className="flex-1 relative w-full aspect-video md:aspect-square max-h-64 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200 border border-slate-200/50 flex items-center justify-center p-6 shadow-inner">
                    <LayoutDashboard className="w-24 h-24 text-slate-300 drop-shadow-sm" />
                 </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════ HOW IT WORKS ═══════════════ */}
      <section className="py-24 bg-white border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 max-w-2xl mx-auto">
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">Gak Pake Lama, Langsung Jualan.</h2>
            <p className="text-lg text-slate-600 font-medium">Lupakan setting yang rumit. Kasira dibuat sesimpel mungkin supaya kamu bisa fokus ngelayanin pembeli.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 lg:gap-12 relative max-w-5xl mx-auto">
            <div className="hidden md:block absolute top-12 left-[15%] right-[15%] h-0.5 bg-gradient-to-r from-emerald-100 via-emerald-300 to-emerald-100" />
            {[
              { step: '01', title: 'Daftar via HP', desc: 'Masukkan nomor WhatsApp dan nama usahamu. Gak sampai semenit.' },
              { step: '02', title: 'Pajang Menu', desc: 'Tambahkan nama menu dan harga. Website jualan langsung otomatis jadi.' },
              { step: '03', title: 'Terima Cuan', desc: 'Download app Kasira di kasir, dan kamu siap terima pesanan hari ini juga.' },
            ].map(({ step, title, desc }, i) => (
              <div key={i} className="relative pt-6">
                <div className="w-14 h-14 mx-auto bg-white border-[4px] border-emerald-500 rounded-2xl flex items-center justify-center mb-6 relative z-10 shadow-[0_0_20px_rgba(16,185,129,0.3)]">
                  <span className="text-lg font-black text-emerald-600">{step}</span>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3 text-center">{title}</h3>
                <p className="text-slate-600 text-center leading-relaxed font-medium">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════ PRICING ═══════════════ */}
      <section id="pricing" className="py-24 bg-slate-900 text-white relative">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,rgba(16,185,129,0.1),transparent)]" />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-extrabold mb-4 tracking-tight">Harga Masuk Akal Buat UMKM.</h2>
            <p className="text-lg text-slate-400 font-medium">Mulai dengan gratis, bayar pas bisnismu udah jalan. Transparan tanpa biaya tersembunyi.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto items-center">
            {/* STARTER */}
            <div className="bg-slate-800/50 rounded-3xl p-8 border border-slate-700 backdrop-blur-sm">
              <div className="mb-8">
                <h3 className="text-xl font-bold text-white mb-2">Starter</h3>
                <p className="text-sm text-slate-400">Cocok buat warung dan kios kecil</p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-4xl font-black text-white">99rb</span>
                  <span className="text-slate-500 font-medium">/bln</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 text-sm font-medium text-slate-300">
                {['1 Akun Kasir', 'Website Toko Gratis', 'Laporan Harian', 'Bisa Dipakai Offline'].map((f, i) => (
                  <li key={i} className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <Link href="/register" className="w-full block text-center px-6 py-3.5 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors">
                Mulai Gratis
              </Link>
            </div>

            {/* PRO */}
            <div className="bg-gradient-to-b from-emerald-600 to-emerald-900 rounded-3xl p-1 border border-emerald-400/50 relative shadow-[0_0_40px_rgba(16,185,129,0.3)] transform md:-translate-y-4">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-900 text-xs font-black uppercase tracking-wider px-4 py-1.5 rounded-full shadow-lg">
                Paling Laris
              </div>
              <div className="bg-slate-900 rounded-[22px] p-8 h-full">
                <div className="mb-8">
                  <h3 className="text-xl font-bold text-white mb-2">Pro</h3>
                  <p className="text-sm text-slate-400">Pilihan utama buat cafe hits</p>
                  <div className="mt-6 flex items-baseline gap-1">
                    <span className="text-5xl font-black text-white">299rb</span>
                    <span className="text-slate-500 font-medium">/bln</span>
                  </div>
                </div>
                <ul className="space-y-4 mb-8 text-sm font-medium text-slate-300">
                  <li className="text-xs font-bold text-emerald-400 uppercase tracking-widest pb-2 border-b border-slate-800">Semua di Starter, plus:</li>
                  {['AI Insight via WA', 'Manajemen Meja & Reservasi', 'Split Bill & Open Tab', 'Bahan Baku & HPP (Resep)'].map((f, i) => (
                    <li key={i} className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <a href={waLink} target="_blank" rel="noopener noreferrer" className="w-full block text-center px-6 py-4 bg-emerald-500 hover:bg-emerald-400 text-white font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(16,185,129,0.4)]">
                  Hubungi Tim Kami
                </a>
              </div>
            </div>

            {/* BUSINESS */}
            <div className="bg-slate-800/50 rounded-3xl p-8 border border-slate-700 backdrop-blur-sm">
              <div className="mb-8">
                <h3 className="text-xl font-bold text-white mb-2">Business</h3>
                <p className="text-sm text-slate-400">Buat restoran yang punya banyak cabang</p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-4xl font-black text-white">499rb</span>
                  <span className="text-slate-500 font-medium">/bln</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 text-sm font-medium text-slate-300">
                {['Multi Cabang Terpusat', 'Dashboard Khusus Owner', 'Transfer Stok Antar Outlet', 'Bantuan Setup Langsung'].map((f, i) => (
                  <li key={i} className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-slate-500 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="w-full block text-center px-6 py-3.5 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors">
                Ngobrol Bareng
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════ FAQ ═══════════════ */}
      <FAQ />

      {/* ═══════════════ CTA ═══════════════ */}
      <section className="py-24 bg-emerald-600 relative overflow-hidden text-white">
        <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]" />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl md:text-5xl font-extrabold mb-6 tracking-tight">
            Udah Saatnya Usahamu Naik Kelas.
          </h2>
          <p className="text-emerald-100 text-lg md:text-xl mb-10 max-w-2xl mx-auto font-medium">
            Gabung bareng ratusan kedai kopi dan restoran lain yang udah ninggalin buku catatan kusam mereka. Coba gratis 30 hari, tanpa syarat ribet.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-slate-900 text-white text-base font-bold rounded-2xl hover:bg-slate-800 transition-all shadow-xl hover:-translate-y-1"
            >
              Mulai Sekarang Jauh Lebih Gampang
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════ FOOTER ═══════════════ */}
      <footer className="bg-slate-50 pt-16 pb-8 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-12">
            <div>
              <span className="text-slate-900 font-black text-3xl tracking-tight">kasira</span>
              <span className="text-emerald-500 font-black text-3xl">.</span>
            </div>
            <div className="flex flex-wrap justify-center gap-x-8 gap-y-4 text-sm font-semibold">
              <Link href="#features" className="text-slate-500 hover:text-emerald-600 transition-colors">Fitur</Link>
              <Link href="#pricing" className="text-slate-500 hover:text-emerald-600 transition-colors">Harga</Link>
              <Link href="/kasira-coffee" className="text-slate-500 hover:text-emerald-600 transition-colors">Demo</Link>
              <Link href="/login" className="text-slate-500 hover:text-emerald-600 transition-colors">Masuk</Link>
              <Link href="/privacy" className="text-slate-500 hover:text-emerald-600 transition-colors">Privasi</Link>
              <Link href="/terms" className="text-slate-500 hover:text-emerald-600 transition-colors">Ketentuan</Link>
            </div>
          </div>
          <div className="pt-8 border-t border-gray-200/60 flex flex-col items-center gap-4">
            <p className="text-slate-400 text-sm font-medium">&copy; {new Date().getFullYear()} Kasira POS. Karya anak bangsa untuk UMKM Indonesia.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Simple dummy icon component for social proof
function CoffeeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 8h1a4 4 0 1 1 0 8h-1" />
      <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
      <line x1="6" x2="6" y1="2" y2="4" />
      <line x1="10" x2="10" y1="2" y2="4" />
      <line x1="14" x2="14" y1="2" y2="4" />
    </svg>
  );
}
