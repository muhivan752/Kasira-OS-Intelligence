import Link from 'next/link';
import { Bricolage_Grotesque } from 'next/font/google';
import { ArrowRight, Check, ChevronDown, MessageCircle } from 'lucide-react';
import LandingChat from '@/components/landing/LandingChat';

// Font display khusus landing. Sengaja di-load di sini, bukan di layout.tsx,
// biar halaman lain (dashboard/login) nggak kena ongkos font yang nggak dipakai
// dan biar nggak nabrak redesign Aurora yang lagi jalan di layout.
const bricolage = Bricolage_Grotesque({
  subsets: ['latin'],
  weight: ['600', '700', '800'],
  variable: '--font-bricolage',
  display: 'swap',
});

// Ditulis literal (bukan disusun runtime) supaya kebaca scanner Tailwind.
const DISPLAY = 'font-[family-name:var(--font-bricolage)]';

const WA_NUMBER = '6285270782220';
const WA_LINK = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent('Halo Kasira, saya tertarik coba')}`;
const DEMO_SLUG = 'kasira-coffee';

const NAV = [
  { label: 'Fitur', href: '#fitur' },
  { label: 'Kenapa beda', href: '#beda' },
  { label: 'Harga', href: '#harga' },
  { label: 'Cerita', href: '#cerita' },
];

const PAINS = [
  { bad: 'Tutup shift, hitung cash selisih terus', good: 'Rekap cash + QRIS otomatis' },
  { bad: 'Pelanggan nanya menu, kirim foto satu-satu', good: 'Website toko online sendiri' },
  { bad: 'Nggak tau menu mana untung, mana buntung', good: 'Margin real-time per produk' },
  { bad: 'Bayar komisi 0,7% tiap transaksi QRIS', good: 'QRIS BYOK, nol komisi' },
];

const DIFFS = [
  {
    no: '01',
    title: 'Bayar per orang, ala warkop beneran.',
    body: 'Lima orang nongkrong di satu meja, masing-masing bayar item sendiri, ada yang nyusul, ada yang cabut duluan. Kasir tinggal centang item yang mau dibayar — sisanya nempel di tab. Kompetitor cuma bisa bagi rata.',
    tag: 'Warkop Pay-Items',
  },
  {
    no: '02',
    title: 'QRIS langsung ke rekening kamu. Komisi ke Kasira: nol.',
    body: 'Daftar Xendit sendiri (BYOK), tempel API key, uang tiap transaksi masuk langsung ke rekening kamu — bypass Kasira. Bukan "gratis 6 bulan lalu kena potong". Nol, selamanya.',
    tag: 'BYOK Xendit · 0% komisi',
  },
  {
    no: '03',
    title: 'Tahu untung-rugi tiap menu, bukan cuma omzet.',
    body: 'Masukin HPP pas restock, dashboard hitung margin per produk otomatis. Muncul alert kalau margin Kopi Susu turun dari 60% ke 45% bulan ini — biar kamu bisa gerak sebelum rugi.',
    tag: 'Margin tracking',
  },
  {
    no: '04',
    title: 'Rangkuman & saran mampir ke WhatsApp tiap pagi.',
    body: 'Buka WA pagi hari, AI Kasira udah kirim: omzet kemarin, menu yang turun, sampai saran stok buat hari ini. Nyambung ke transaksi toko kamu — bukan chatbot generik.',
    tag: 'AI Kopi Asisten · Pro',
  },
];

const PILLARS = [
  {
    title: 'Kasir yang tahan banting',
    body: 'Mati lampu atau WiFi ngadat, kasir tetap jalan. Data sync otomatis pas online lagi.',
    items: ['Mode offline', 'Print struk bluetooth', 'Split bill & open tab'],
  },
  {
    title: 'Toko online jadi seketika',
    body: 'Daftar, website toko langsung live di kasira.online/namamu. Sebar ke WA & IG.',
    items: ['Storefront gratis', 'Terima order sendiri', 'Reservasi meja (Pro)'],
  },
  {
    title: 'Dapur & stok terkendali',
    body: 'Pantau stok bahan, resep & HPP, sampai layar dapur pas jam rame.',
    items: ['Alert stok rendah', 'Resep & HPP', 'Kitchen Display (Pro)'],
  },
];

const PLANS = [
  {
    name: 'Starter',
    tagline: 'Buat warung & kios kecil',
    price: '99rb',
    badge: 'Siap pakai',
    dark: false,
    features: ['1 kasir + 1 outlet', 'Website toko gratis', 'QRIS BYOK (nol komisi)', 'Mode offline', 'Margin & laporan harian'],
    cta: 'Mulai gratis',
    href: '/register',
  },
  {
    name: 'Pro',
    tagline: 'Pilihan utama cafe hits',
    price: '299rb',
    badge: 'Early access',
    dark: true,
    features: ['Semua Starter, plus:', 'Warkop Pay-Items ⭐', 'AI Kopi Asisten via WA', 'Reservasi & Kitchen Display', 'Resep + HPP, loyalty points'],
    cta: 'Mulai Pro 30 hari',
    href: '/register?tier=pro',
  },
];

const FAQS = [
  { q: 'Beneran gratis 30 hari?', a: 'Ya, 30 hari penuh tanpa kartu kredit. Batal kapan aja, nggak ada penalti.' },
  { q: 'QRIS-nya kena potongan ke Kasira?', a: 'Nggak. Kamu daftar Xendit sendiri (BYOK), tempel API key di setelan, dan uang tiap transaksi QRIS langsung masuk ke rekening kamu. Kasira nol komisi, selamanya.' },
  { q: 'Kenapa harus daftar Xendit sendiri (BYOK)?', a: 'Karena kamu settle langsung tanpa lewat Kasira, kami nggak perlu KYC platform — jadi harganya bisa lebih murah dan kontrol pembayaran penuh di tangan kamu.' },
  { q: 'Bisa dipakai di HP Android biasa?', a: 'Bisa. App kasir jalan di HP Android manapun, nggak butuh tablet atau mesin khusus.' },
  { q: 'Kalau internet mati gimana?', a: 'Kasir tetap bisa transaksi offline. Data otomatis kesinkron begitu internet nyala lagi.' },
  { q: 'Data saya aman?', a: 'Data disimpan di server Indonesia dengan enkripsi, dan di-backup otomatis berkala.' },
];

const SPLIT_ROWS = [
  { name: 'Andi', items: 'Kopi Susu · Croissant', status: '✓ QRIS', paid: true },
  { name: 'Rani', items: 'Matcha Latte', status: '✓ Tunai', paid: true },
  { name: 'Budi', items: 'Nasi Goreng · Es Teh', status: 'Rp 43rb', paid: false },
];

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Kasira',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Android, Web',
  description:
    'Kasir digital modern dengan storefront gratis, QRIS tanpa komisi, dan AI insight untuk bisnis F&B dan UMKM Indonesia.',
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

// Diturunkan dari FAQS yang sama dengan yang dirender — biar structured data
// nggak pernah beda dari yang dibaca pengunjung. (Versi lama masih nyebut
// Midtrans padahal pembayaran udah pindah ke BYOK Xendit.)
const faqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map((f) => ({
    '@type': 'Question',
    name: f.q,
    acceptedAnswer: { '@type': 'Answer', text: f.a },
  })),
};

export default function LandingPage() {
  return (
    <div className={`${bricolage.variable} min-h-screen w-full overflow-x-hidden bg-[#FAFAF7] text-[#0B1512] antialiased`}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }} />

      {/* ── NAV ── */}
      <header className="sticky top-0 z-50 border-b border-[#EAE8E1] bg-[#FAFAF7]/85 backdrop-blur-[14px]">
        <div className="mx-auto flex h-[68px] max-w-[1180px] items-center justify-between px-5 sm:px-6">
          <Link href="/" className={`${DISPLAY} text-[24px] font-extrabold tracking-[-0.03em] text-[#0B1512]`}>
            kasira<span className="text-[#059669]">.</span>
          </Link>

          <nav className="hidden items-center gap-7 text-[14.5px] font-semibold text-[#3F4A45] md:flex">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} className="transition hover:text-[#0B1512]">
                {n.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2.5">
            <Link href="/login" className="hidden px-3 py-2 text-[14.5px] font-semibold text-[#3F4A45] transition hover:text-[#0B1512] sm:block">
              Masuk
            </Link>
            <Link href="/register" className="rounded-full bg-[#0B1512] px-4 py-2.5 text-[14px] font-semibold text-white transition hover:bg-[#1a2622]">
              Coba gratis
            </Link>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="mx-auto max-w-[1180px] px-5 pb-16 pt-14 sm:px-6 lg:pb-24 lg:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-[#D8E7DF] bg-[#ECFDF5] px-3 py-1.5 text-[12.5px] font-bold text-[#047857]">
              <span className="rounded-full bg-[#059669] px-1.5 py-0.5 text-[10.5px] text-white">Baru</span>
              POS + toko online + AI, jadi satu
            </span>

            <h1 className={`${DISPLAY} mt-5 text-[42px] font-extrabold leading-[1.03] tracking-[-0.035em] sm:text-[54px] lg:text-[62px]`}>
              Fokus ke rasa,
              <br />
              <span className="text-[#4B5750]">sisanya</span> Kasira urus.
            </h1>

            <p className="mt-5 max-w-[540px] text-[16.5px] leading-[1.6] text-[#4B5750]">
              Tinggalin catatan kertas sama Excel. Dari terima pesanan, pantau stok bahan, sampai punya website
              jualan sendiri — semua beres di satu aplikasi. Setup 5 menit, langsung jualan.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 rounded-full bg-[#059669] px-6 py-3.5 text-[15px] font-bold text-white shadow-[0_16px_34px_-14px_rgba(5,150,105,0.9)] transition hover:bg-[#047857]"
              >
                Coba gratis 30 hari
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href={`/${DEMO_SLUG}`}
                className="inline-flex items-center gap-2 rounded-full border border-[#DCDAD2] bg-white px-6 py-3.5 text-[15px] font-bold text-[#0B1512] transition hover:border-[#0B1512]"
              >
                Lihat demo toko
              </Link>
            </div>

            <ul className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] font-medium text-[#8A938D]">
              {['Tanpa kartu kredit', 'Batal kapan aja', 'Server di Indonesia'].map((t) => (
                <li key={t} className="flex items-center gap-1.5">
                  <Check className="h-3.5 w-3.5 text-[#059669]" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          {/* Kartu demo split bill */}
          <div className="relative">
            <div className="rounded-[22px] border border-[#E7E5DE] bg-white p-5 shadow-[0_30px_60px_-30px_rgba(11,21,18,0.35)]">
              <div className="flex items-start justify-between">
                <div>
                  <p className={`${DISPLAY} text-[19px] font-extrabold`}>Meja 4</p>
                  <p className="text-[12.5px] text-[#8A938D]">4 orang · buka 19:24</p>
                </div>
                <span className="rounded-full bg-[#ECFDF5] px-2.5 py-1 text-[11.5px] font-bold text-[#047857]">Split aktif</span>
              </div>

              <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.12em] text-[#A8B0AA]">Bayar per orang</p>

              <div className="mt-2.5 space-y-2">
                {SPLIT_ROWS.map((r) => (
                  <div
                    key={r.name}
                    className={`flex items-center justify-between rounded-xl border px-3.5 py-3 ${
                      r.paid ? 'border-[#E3EFE9] bg-[#F6FBF8]' : 'border-[#E7E5DE] bg-white'
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="text-[14px] font-bold">{r.name}</p>
                      <p className="truncate text-[12px] text-[#8A938D]">{r.items}</p>
                    </div>
                    <span className={`shrink-0 text-[12.5px] font-bold ${r.paid ? 'text-[#047857]' : 'text-[#0B1512]'}`}>
                      {r.status}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-3.5 flex items-center justify-between border-t border-[#EAE8E1] pt-3.5">
                <p className="text-[12.5px] text-[#8A938D]">Sisa 1 orang belum bayar</p>
                <p className="text-[12.5px] font-bold text-[#047857]">2/3 lunas</p>
              </div>

              <div aria-hidden="true" className="mt-3 w-full rounded-xl bg-[#0B1512] py-3 text-center text-[14px] font-bold text-white">
                Tagih Budi · Rp 43.000
              </div>
            </div>

            <div className="mt-3 flex items-center gap-2 rounded-xl border border-[#E3EFE9] bg-[#ECFDF5] px-3.5 py-2.5 text-[12.5px] text-[#047857]">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#10B981]" />
              <span>
                <strong className="font-bold">QRIS Andi masuk</strong> — langsung ke rekening kamu
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ── PAY-ITEMS ── */}
      <section className="border-y border-[#EAE8E1] bg-white">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#059669]">Warkop Pay-Items</p>
          <h2 className={`${DISPLAY} mt-3 max-w-[640px] text-[30px] font-extrabold leading-[1.12] tracking-[-0.03em] sm:text-[38px]`}>
            Satu meja, tiap orang bayar punyanya sendiri.
          </h2>
          <p className="mt-4 max-w-[620px] text-[16px] leading-[1.6] text-[#4B5750]">
            Ada yang bayar duluan pakai QRIS, ada yang cash, ada yang nyusul. Kasir tinggal centang item per orang
            — bukan maksa bagi rata kayak kasir lain.
          </p>
          <div className="mt-6 flex flex-wrap gap-2.5">
            {['Metode bayar beda-beda per orang', 'Tab meja tetap jalan sampai semua lunas'].map((t) => (
              <span key={t} className="rounded-full border border-[#E7E5DE] bg-[#FAFAF7] px-3.5 py-2 text-[13px] font-semibold text-[#3F4A45]">
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── PAINS ── */}
      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#8A938D]">Yang bikin pusing → beres</p>
        <h2 className={`${DISPLAY} mt-3 max-w-[620px] text-[30px] font-extrabold leading-[1.12] tracking-[-0.03em] sm:text-[38px]`}>
          Kamu udah kenal masalahnya. Kami bikin solusinya.
        </h2>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {PAINS.map((p) => (
            <div key={p.bad} className="rounded-2xl border border-[#E7E5DE] bg-white p-5">
              <p className="text-[14px] leading-snug text-[#8A938D] line-through decoration-[#D6D3CA]">{p.bad}</p>
              <p className="mt-2.5 flex items-start gap-2 text-[15px] font-bold leading-snug text-[#0B1512]">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#059669]" />
                {p.good}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── DIFFS ── */}
      <section id="beda" className="border-y border-[#EAE8E1] bg-white">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#059669]">Bukan kasir biasa</p>
          <h2 className={`${DISPLAY} mt-3 text-[30px] font-extrabold leading-[1.12] tracking-[-0.03em] sm:text-[38px]`}>
            Empat hal yang nggak dipunya kompetitor.
          </h2>
          <p className="mt-4 max-w-[640px] text-[16px] leading-[1.6] text-[#4B5750]">
            Moka, Pawoon, Olsera — bagus, tapi kerasa &ldquo;barat&rdquo;. Ini bagian yang kami bikin khusus buat
            cara jualan orang Indonesia.
          </p>

          <div className="mt-9 grid gap-5 md:grid-cols-2">
            {DIFFS.map((d) => (
              <article key={d.no} className="rounded-2xl border border-[#E7E5DE] bg-[#FAFAF7] p-6">
                <span className={`${DISPLAY} text-[13px] font-extrabold tracking-[0.08em] text-[#059669]`}>{d.no}</span>
                <h3 className={`${DISPLAY} mt-2.5 text-[20px] font-extrabold leading-[1.2] tracking-[-0.02em] sm:text-[22px]`}>
                  {d.title}
                </h3>
                <p className="mt-3 text-[15px] leading-[1.62] text-[#4B5750]">{d.body}</p>
                <span className="mt-4 inline-block rounded-full border border-[#DCE8E2] bg-white px-3 py-1.5 text-[12px] font-bold text-[#047857]">
                  {d.tag}
                </span>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── PILLARS ── */}
      <section id="fitur" className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
        <div className="grid gap-5 md:grid-cols-3">
          {PILLARS.map((f) => (
            <article key={f.title} className="rounded-2xl border border-[#E7E5DE] bg-white p-6">
              <h3 className={`${DISPLAY} text-[19px] font-extrabold leading-tight tracking-[-0.02em]`}>{f.title}</h3>
              <p className="mt-2.5 text-[14.5px] leading-[1.6] text-[#4B5750]">{f.body}</p>
              <ul className="mt-4 space-y-2">
                {f.items.map((it) => (
                  <li key={it} className="flex items-center gap-2 text-[14px] font-medium text-[#2C3833]">
                    <Check className="h-3.5 w-3.5 shrink-0 text-[#059669]" />
                    {it}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      {/* ── HARGA ── */}
      <section id="harga" className="border-y border-[#EAE8E1] bg-white">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
          <div className="text-center">
            <h2 className={`${DISPLAY} text-[30px] font-extrabold leading-[1.12] tracking-[-0.03em] sm:text-[38px]`}>
              Masuk akal buat UMKM.
            </h2>
            <p className="mx-auto mt-4 max-w-[520px] text-[16px] leading-[1.6] text-[#4B5750]">
              Mulai gratis, bayar pas bisnis udah jalan. Transparan, tanpa biaya nyempil.
            </p>
          </div>

          <div className="mx-auto mt-10 grid max-w-[840px] gap-5 md:grid-cols-2">
            {PLANS.map((pl) => (
              <article
                key={pl.name}
                className={
                  pl.dark
                    ? 'rounded-[22px] border border-[#12201B] bg-[#0A0F0D] p-7 shadow-[0_30px_60px_-24px_rgba(5,150,105,0.45)]'
                    : 'rounded-[22px] border border-[#E7E5DE] bg-white p-7'
                }
              >
                <span
                  className={`inline-block rounded-full px-2.5 py-1 text-[11.5px] font-bold ${
                    pl.dark ? 'bg-[#FEF3C7] text-[#B45309]' : 'bg-[#ECFDF5] text-[#047857]'
                  }`}
                >
                  {pl.badge}
                </span>
                <h3 className={`${DISPLAY} mt-3.5 text-[24px] font-extrabold ${pl.dark ? 'text-white' : 'text-[#0B1512]'}`}>
                  {pl.name}
                </h3>
                <p className={`text-[13.5px] ${pl.dark ? 'text-[#8CA095]' : 'text-[#6B756F]'}`}>{pl.tagline}</p>

                <p className="mt-5 flex items-baseline gap-1.5">
                  <span className={`${DISPLAY} text-[38px] font-extrabold tracking-[-0.03em] ${pl.dark ? 'text-white' : 'text-[#0B1512]'}`}>
                    {pl.price}
                  </span>
                  <span className={`text-[14px] ${pl.dark ? 'text-[#8CA095]' : 'text-[#6B756F]'}`}>/bln</span>
                </p>

                <ul className="mt-6 space-y-2.5">
                  {pl.features.map((ft) => (
                    <li key={ft} className={`flex items-start gap-2.5 text-[14.5px] ${pl.dark ? 'text-[#D3DED8]' : 'text-[#2C3833]'}`}>
                      <Check className={`mt-0.5 h-4 w-4 shrink-0 ${pl.dark ? 'text-[#34D399]' : 'text-[#059669]'}`} />
                      {ft}
                    </li>
                  ))}
                </ul>

                <Link
                  href={pl.href}
                  className={`mt-7 flex w-full items-center justify-center rounded-xl py-3.5 text-[15px] font-bold transition ${
                    pl.dark
                      ? 'bg-[#10B981] text-[#04231A] hover:bg-[#34D399]'
                      : 'border border-[#E4E2DB] bg-[#F2F1EC] text-[#0B1512] hover:border-[#0B1512]'
                  }`}
                >
                  {pl.cta}
                </Link>
              </article>
            ))}
          </div>

          <p className="mx-auto mt-6 max-w-[560px] text-center text-[13px] leading-relaxed text-[#8A938D]">
            Demo toko pakai data contoh. Pro lagi tahap early access — feedback kamu kami dengerin.
          </p>
        </div>
      </section>

      {/* ── CERITA ── */}
      <section id="cerita" className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
        <div className="mx-auto max-w-[760px] rounded-[22px] border border-[#E7E5DE] bg-white p-7 sm:p-10">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#8A938D]">Kenapa Kasira ada</p>
          <blockquote className={`${DISPLAY} mt-4 text-[20px] font-semibold leading-[1.4] tracking-[-0.015em] text-[#0B1512] sm:text-[23px]`}>
            &ldquo;Gue bikin Kasira karena POS yang ada kerasa terlalu &lsquo;barat&rsquo; buat warkop Indonesia.
            Split bill bagi rata? Warkop beneran nggak gitu — orang bayar punya dia sendiri, ada yang nyusul, ada
            yang pulang duluan. Itu yang Kasira beresin.&rdquo;
          </blockquote>
          <div className="mt-6 flex items-center gap-3">
            <span className={`${DISPLAY} flex h-11 w-11 items-center justify-center rounded-full bg-[#0B1512] text-[17px] font-extrabold text-white`}>
              I
            </span>
            <div>
              <p className="text-[14.5px] font-bold">Ivan</p>
              <p className="text-[13px] text-[#8A938D]">Founder Kasira</p>
            </div>
          </div>
          <p className="mt-6 rounded-xl bg-[#FAFAF7] px-4 py-3.5 text-[13.5px] leading-relaxed text-[#4B5750]">
            Kami lagi di fase pra-pilot. 10 cafe pertama yang gabung bantu bentuk produknya — dan dapet 2 bulan Pro
            gratis.
          </p>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="border-y border-[#EAE8E1] bg-white">
        <div className="mx-auto max-w-[780px] px-5 py-16 sm:px-6 lg:py-20">
          <h2 className={`${DISPLAY} text-[30px] font-extrabold leading-[1.12] tracking-[-0.03em] sm:text-[36px]`}>
            Pertanyaan yang sering muncul
          </h2>
          <div className="mt-8 border-y border-[#EAE8E1]">
            {FAQS.map((f) => (
              // <details> native: accordion tanpa JavaScript sama sekali, dan
              // isinya tetap kebaca crawler buat SEO.
              <details key={f.q} className="group border-b border-[#EAE8E1] py-4 last:border-b-0">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[15.5px] font-bold text-[#0B1512]">
                  {f.q}
                  <ChevronDown className="h-4 w-4 shrink-0 text-[#8A938D] transition group-open:rotate-180" />
                </summary>
                <p className="mt-3 text-[14.5px] leading-[1.65] text-[#4B5750]">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-24">
        <div className="rounded-[26px] bg-[#0A0F0D] px-7 py-12 text-center sm:px-10 sm:py-16">
          <h2 className={`${DISPLAY} mx-auto max-w-[560px] text-[30px] font-extrabold leading-[1.1] tracking-[-0.03em] text-white sm:text-[40px]`}>
            Cafe kamu layak sistem yang proper.
          </h2>
          <p className="mx-auto mt-4 max-w-[520px] text-[16px] leading-[1.6] text-[#8CA095]">
            Coba gratis 30 hari. Tanpa kartu kredit, tanpa syarat ribet. Kalau nggak cocok, tinggal berhenti.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-full bg-[#10B981] px-6 py-3.5 text-[15px] font-bold text-[#04231A] transition hover:bg-[#34D399]"
            >
              Daftar gratis sekarang
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href={WA_LINK}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-[#25342D] px-6 py-3.5 text-[15px] font-bold text-white transition hover:border-[#8CA095]"
            >
              <MessageCircle className="h-4 w-4" />
              Tanya via WhatsApp
            </a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[#EAE8E1]">
        <div className="mx-auto flex max-w-[1180px] flex-col items-center justify-between gap-4 px-5 py-8 text-[13px] text-[#8A938D] sm:flex-row sm:px-6">
          <p>© {new Date().getFullYear()} Kasira · buat UMKM Indonesia 🇮🇩</p>
          <nav className="flex flex-wrap items-center justify-center gap-5">
            <Link href={`/${DEMO_SLUG}`} className="transition hover:text-[#0B1512]">Demo</Link>
            <Link href="/download" className="transition hover:text-[#0B1512]">Download</Link>
            <Link href="/privacy" className="transition hover:text-[#0B1512]">Privasi</Link>
            <Link href="/terms" className="transition hover:text-[#0B1512]">Ketentuan</Link>
          </nav>
        </div>
      </footer>

      <LandingChat waLink={WA_LINK} />
    </div>
  );
}
