import Link from 'next/link';
import {
  ArrowRight, Check, ChevronDown, MessageCircle, Camera, Receipt, Smartphone,
  Package, Users, LineChart, Bot, Store, Truck, Sparkles,
} from 'lucide-react';
import LandingChat from '@/components/landing/LandingChat';
import { Logo } from '@/components/ui/logo';
import { BRAND, SITE_URL, WA_LINK, DEMO_SLUG } from '@/lib/brand';

const NAV = [
  { label: 'Cara kerja', href: '#cara-kerja' },
  { label: 'Tampilan', href: '#tampilan' },
  { label: 'Modul', href: '#modul' },
  { label: 'Harga', href: '#harga' },
];

// Tesis produk: pemilik cuma nyentuh tiga hal, sisanya turunan.
const INPUTS = [
  {
    icon: Smartphone,
    title: 'Transaksi di kasir',
    body: 'Setiap pesanan yang dibayar, baik tunai, QRIS, maupun split bill, langsung menjadi stok berkurang, omzet, laba per menu, dan riwayat pelanggan.',
    outputs: ['Stok', 'Omzet & laba per menu', 'Riwayat pelanggan'],
  },
  {
    icon: Camera,
    title: 'Foto nota belanja',
    body: 'Belanja bahan di pasar, cukup foto notanya. Stok bertambah, harga modal dihitung ulang dengan metode rata-rata, dan utang ke supplier tercatat.',
    outputs: ['Stok bahan', 'HPP otomatis', 'Utang supplier'],
    badge: 'Baru',
  },
  {
    icon: MessageCircle,
    title: 'Nomor WA di struk',
    body: 'Kasir memasukkan nomor pelanggan saat mengirim struk. Profilnya terbentuk sendiri: kunjungan, menu favorit, poin, sampai siapa yang mulai jarang datang.',
    outputs: ['Profil pelanggan', 'Poin loyalitas', 'Pelanggan yang perlu dihubungi'],
  },
];

const MODULES = [
  { icon: Store, title: 'Kasir offline', body: 'Listrik padam atau internet terputus, transaksi tetap jalan. Cetak struk lewat Bluetooth, data tersinkron otomatis.', status: 'ada' },
  { icon: Receipt, title: 'Split bill ala warkop', body: 'Satu meja lima orang, masing-masing membayar pesanannya sendiri. Ada yang datang menyusul atau pulang lebih dulu, tagihan meja tetap rapi.', status: 'ada' },
  { icon: Package, title: 'Stok, resep & HPP', body: 'Resep per menu, stok bahan berkurang setiap pesanan, dan harga modal selalu mengikuti nota belanja terakhir.', status: 'ada', pro: true },
  { icon: Truck, title: 'Pembelian & utang supplier', body: 'Catat nota atau cukup fotonya. Belanja bulan ini, tagihan yang belum dibayar, dan jatuh temponya terlihat dalam satu halaman.', status: 'baru' },
  { icon: Users, title: 'Pelanggan & loyalty', body: 'Poin terkumpul otomatis dari transaksi, profil pelanggan terbentuk dari nomor di struk, dan struk digital terkirim lewat WhatsApp.', status: 'ada' },
  { icon: LineChart, title: 'Laba rugi & arus kas', body: 'Pendapatan dikurangi harga modal dan pengeluaran, dihitung per bulan tanpa jurnal. Utang supplier dan kas laci ikut terbaca.', status: 'segera' },
  { icon: Sparkles, title: 'Segmen pelanggan & promo WA', body: 'Segmen "setia", "mulai jarang", dan "hilang" terbentuk sendiri dari data kunjungan. Kirim promo per segmen, lalu ukur siapa yang kembali.', status: 'segera', pro: true },
  { icon: Bot, title: 'AI asisten di WhatsApp', body: 'Setiap pagi: omzet kemarin, menu yang menurun, bahan yang menipis, dan saran harga. Semuanya dari data toko Anda sendiri.', status: 'ada', pro: true },
];

// Tangkapan layar asli dari APK kasir (bukan mockup). Rasio 640×1292 dikunci
// lewat width/height biar layout nggak lompat pas gambarnya belum turun.
const SHOTS = [
  { src: '/app/beranda.webp', title: 'Beranda kasir', body: 'Omzet hari ini, shift yang sedang berjalan, dan satu saran dari AI yang membaca data toko Anda sendiri.' },
  { src: '/app/kasir.webp', title: 'Layar jualan', body: 'Menu bergambar, pencarian cepat, satu ketukan masuk keranjang. Tetap berjalan saat internet mati.' },
  { src: '/app/keranjang.webp', title: 'Keranjang & bayar', body: 'Diskon, data pelanggan, dan saran menu yang sering dibeli bersamaan. Bayar sekarang atau simpan ke meja.' },
];

// Tangkapan layar dashboard pemilik (browser 1440x900, diambil dari data demo).
const DASH_SHOTS = [
  { src: '/app/dash-overview.webp', title: 'Ringkasan harian', body: 'Omzet, jumlah pesanan, shift yang sedang berjalan, dan menu terlaris. Terbentuk dari transaksi kasir, tanpa rekap manual.', wide: true },
  { src: '/app/dash-keuangan.webp', title: 'Laba rugi dan arus kas', body: 'Pendapatan, harga modal terjual, pengeluaran, dan posisi kas per akun. Tanpa satu pun jurnal diketik.', wide: false },
  { src: '/app/dash-pembelian.webp', title: 'Pembelian dan utang supplier', body: 'Nota belanja bulan ini, tagihan yang belum lunas, dan jatuh tempo terdekat.', wide: false },
];

const STATUS_LABEL: Record<string, { text: string; cls: string }> = {
  ada: { text: 'Sudah jalan', cls: 'bg-[color-mix(in_srgb,var(--success)_14%,transparent)] text-[var(--success)]' },
  baru: { text: 'Baru dirilis', cls: 'bg-[var(--brand-tint)] text-[var(--brand-primary)]' },
  segera: { text: 'Segera', cls: 'bg-[var(--surface-sunken)] text-[var(--text-muted)]' },
};

const PLANS = [
  {
    name: 'Starter',
    tagline: 'Warung, kios, dan toko kecil',
    price: '99rb',
    badge: 'Siap pakai',
    dark: false,
    features: ['1 kasir + 1 outlet, mode offline', 'Website toko gratis', 'QRIS atas nama sendiri, tanpa komisi', 'Nota belanja dan utang supplier', 'Pelanggan dan laporan harian'],
    cta: 'Coba gratis 30 hari',
    href: '/register',
  },
  {
    name: 'Pro',
    tagline: 'Kafe dan restoran',
    price: '299rb',
    badge: 'Paling lengkap',
    dark: true,
    features: ['Semua Starter, plus:', 'Resep, stok bahan, dan harga modal otomatis', 'Split bill dan reservasi meja', 'Program loyalitas dan layar dapur', 'Asisten AI lewat WhatsApp'],
    cta: 'Coba Pro 30 hari',
    href: '/register?tier=pro',
  },
];

const FAQS = [
  { q: 'Ini POS atau ERP?', a: `Keduanya, dan Anda tidak perlu memikirkan bedanya. ${BRAND} mulai dari kasir, lalu mengisi sendiri bagian yang di software lain harus diketik manual: stok, harga modal, utang supplier, dan profil pelanggan. Tanpa jurnal, tanpa formulir akuntansi.` },
  { q: 'Beneran gratis 30 hari?', a: 'Ya, 30 hari penuh tanpa kartu kredit. Berhenti kapan saja, tanpa penalti.' },
  { q: 'QRIS-nya kena potongan?', a: `Tidak. Anda mendaftar Xendit atas nama sendiri, memasang API key di pengaturan, lalu uang setiap transaksi QRIS langsung masuk ke rekening Anda. ${BRAND} tidak mengambil komisi, selamanya.` },
  { q: 'Usaha saya bukan kafe, apakah toko vape atau sparepart bisa?', a: 'Bisa. Paket Starter dipakai banyak toko di luar bidang makanan: stok produk jadi, nota belanja ke supplier, utang, dan data pelanggan. Fitur khusus makanan dan minuman seperti resep, bahan baku, dan meja ada di paket Pro.' },
  { q: 'Kalau internet mati?', a: 'Kasir tetap bisa melayani transaksi secara offline. Data tersinkron otomatis begitu internet kembali tersambung.' },
  { q: 'Data saya aman?', a: 'Data disimpan di server Indonesia, dipisahkan per bisnis pada level basis data, dan dicadangkan otomatis setiap 6 jam.' },
];

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: BRAND,
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Android, Web',
  description: 'Kasir digital yang mengisi pembukuan sendiri: stok, harga modal, utang supplier, dan data pelanggan terbentuk otomatis dari transaksi, nota belanja, dan nomor WhatsApp. Untuk kafe dan UMKM Indonesia.',
  url: SITE_URL,
  offers: [
    { '@type': 'Offer', name: 'Starter', price: '99000', priceCurrency: 'IDR', description: 'Kasir offline, website toko, QRIS atas nama sendiri, pembelian, dan laporan' },
    { '@type': 'Offer', name: 'Pro', price: '299000', priceCurrency: 'IDR', description: 'Semua fitur Starter ditambah resep dan harga modal, split bill, loyalitas, dan asisten AI' },
  ],
};

const organizationLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: BRAND,
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.svg`,
  description: 'Platform kasir, ERP ringan, dan CRM untuk UMKM serta bisnis makanan dan minuman di Indonesia.',
  contactPoint: { '@type': 'ContactPoint', telephone: '+62-852-7078-2220', contactType: 'customer service', availableLanguage: 'Indonesian' },
};

const faqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map((f) => ({ '@type': 'Question', name: f.q, acceptedAnswer: { '@type': 'Answer', text: f.a } })),
};

/// Bingkai jendela browser buat tangkapan layar dashboard. Tiga titik di kiri
/// dan pil alamat bikin gambarnya kebaca sebagai layar komputer, bukan gambar
/// lepas yang ngambang di tengah halaman.
function _Browser({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="overflow-hidden rounded-[16px] border border-[var(--border-default)] bg-[var(--surface-card)] shadow-[0_24px_60px_-32px_rgba(20,10,40,0.45)]">
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--surface-sunken)] px-3.5 py-2.5">
        <span className="flex gap-1.5" aria-hidden="true">
          {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
            <span key={c} className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
          ))}
        </span>
        <span className="ml-1 truncate rounded-full bg-[var(--surface-card)] px-3 py-1 text-[11px] text-[var(--text-muted)]">selaris.id/dashboard</span>
      </div>
      <img src={src} alt={alt} width={1440} height={900} loading="lazy" className="block w-full" />
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[var(--bg-base)] text-[var(--text-body)] antialiased">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }} />

      {/* ── NAV ── */}
      <header className="sticky top-0 z-50 border-b border-[var(--border-subtle)] bg-[color-mix(in_srgb,var(--bg-base)_85%,transparent)] backdrop-blur-[14px]">
        <div className="mx-auto flex h-[68px] max-w-[1180px] items-center justify-between px-5 sm:px-6">
          <Link href="/" aria-label={BRAND}><Logo size="sm" variant="light" /></Link>
          <nav className="hidden items-center gap-7 text-[14.5px] font-semibold text-[var(--text-body)] md:flex">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} className="transition hover:text-[var(--text-strong)]">{n.label}</a>
            ))}
          </nav>
          <div className="flex items-center gap-2.5">
            <Link href="/login" className="hidden px-3 py-2 text-[14.5px] font-semibold text-[var(--text-body)] transition hover:text-[var(--text-strong)] sm:block">Masuk</Link>
            <Link href="/register" className="ks-btn ks-btn-sm !w-auto">Coba gratis</Link>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="relative">
        <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[image:var(--gradient-glow)]" />
        <div className="relative mx-auto max-w-[1180px] px-5 pb-16 pt-14 sm:px-6 lg:pb-24 lg:pt-20">
          <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
            <div>
              <span className="ks-eyebrow inline-flex items-center gap-2 text-[var(--brand-primary)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--brand-primary)]" />
                Kasir · Stok · Pembelian · Pelanggan dalam satu aplikasi
              </span>
              <h1 className="ks-display mt-5 text-[42px] leading-[1.03] text-[var(--text-strong)] sm:text-[54px] lg:text-[62px]" style={{ textWrap: 'balance' }}>
                Kasir yang mengisi pembukuan Anda <span className="ks-gradient-text">sendiri.</span>
              </h1>
              <p className="mt-5 max-w-[540px] text-[16.5px] leading-[1.6] text-[var(--text-body)]">
                Setiap transaksi, nota belanja, dan nomor WhatsApp pelanggan otomatis menjadi data stok, harga modal,
                utang supplier, dan daftar pelanggan yang perlu dihubungi. Anda fokus berjualan, {BRAND} yang mencatat.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link href="/register" className="ks-btn ks-btn-lg !w-auto">
                  Coba gratis 30 hari <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href={`/${DEMO_SLUG}`} className="ks-btn ks-btn-lg ks-btn-outline !w-auto">Lihat toko demo</Link>
              </div>
              <ul className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] font-medium text-[var(--text-muted)]">
                {['Tanpa kartu kredit', 'Berhenti kapan saja', 'Server di Indonesia'].map((t) => (
                  <li key={t} className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[var(--success)]" />{t}</li>
                ))}
              </ul>
            </div>

            {/* Kartu demo: satu nota → efek berantai */}
            <div className="relative">
              <div className="ks-card p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="ks-display text-[18px] text-[var(--text-strong)]">Nota belanja</p>
                    <p className="text-[12.5px] text-[var(--text-muted)]">Toko Berkah · Selasa 07:40 · dari foto nota</p>
                  </div>
                  <span className="rounded-full bg-[var(--brand-tint)] px-2.5 py-1 text-[11.5px] font-bold text-[var(--brand-primary)]">Tercatat</span>
                </div>

                <div className="mt-4 space-y-2">
                  {[
                    { name: 'Susu UHT', qty: '4 liter', total: 'Rp 72.000' },
                    { name: 'Kopi arabica', qty: '1 kg', total: 'Rp 145.000' },
                    { name: 'Gula aren', qty: '2 kg', total: 'Rp 48.000' },
                  ].map((r) => (
                    <div key={r.name} className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-card)] px-3.5 py-2.5">
                      <div className="min-w-0">
                        <p className="text-[14px] font-bold text-[var(--text-strong)]">{r.name}</p>
                        <p className="text-[12px] text-[var(--text-muted)]">{r.qty}</p>
                      </div>
                      <span className="ks-mono shrink-0 text-[12.5px] font-bold text-[var(--text-strong)]">{r.total}</span>
                    </div>
                  ))}
                </div>

                <p className="ks-eyebrow mt-4">Yang keisi sendiri</p>
                <div className="mt-2 space-y-1.5 text-[13px]">
                  {[
                    ['Stok susu', '2,1 L → 6,1 L'],
                    ['HPP Kopi Susu', 'Rp 6.850 → Rp 7.120'],
                    ['Margin Kopi Susu', '64% → 62% · masih sehat'],
                    ['Utang Toko Berkah', 'Rp 265.000 · tempo 7 hari'],
                  ].map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between gap-3 border-b border-dashed border-[var(--border-subtle)] py-1.5 last:border-b-0">
                      <span className="text-[var(--text-muted)]">{k}</span>
                      <span className="ks-mono font-bold text-[var(--text-strong)]">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-3 flex items-center gap-2 rounded-xl border border-[color-mix(in_srgb,var(--success)_35%,transparent)] bg-[color-mix(in_srgb,var(--success)_10%,transparent)] px-3.5 py-2.5 text-[12.5px] text-[var(--text-strong)]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--success)]" />
                <span><strong className="font-bold">Anda hanya memfoto notanya.</strong> Empat baris di atas tidak ada yang diketik manual.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CARA KERJA: tiga input ── */}
      <section id="cara-kerja" className="border-y border-[var(--border-subtle)] bg-[var(--surface-card)]">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
          <p className="ks-eyebrow text-[var(--brand-primary)]">Cara kerja</p>
          <h2 className="ks-display mt-3 max-w-[680px] text-[30px] leading-[1.12] text-[var(--text-strong)] sm:text-[38px]" style={{ textWrap: 'balance' }}>
            Tiga hal yang Anda isi. Sisanya dihitung sendiri.
          </h2>
          <p className="mt-4 max-w-[640px] text-[16px] leading-[1.6] text-[var(--text-body)]">
            Software ERP umumnya memberi Anda sepuluh modul dan sepuluh formulir. {BRAND} kebalikannya: yang diisi manusia
            hanya hal yang memang cuma diketahui manusia. Sisanya, angka pembukuan, dihitung dari situ.
          </p>

          <div className="mt-9 grid gap-4 md:grid-cols-3">
            {INPUTS.map((it, i) => (
              <article key={it.title} className="relative rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-6">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[image:var(--gradient-frekuensi)] text-[var(--text-on-brand)] shadow-[var(--glow-pink)]">
                    <it.icon className="h-5 w-5" />
                  </div>
                  {it.badge && <span className="rounded-full bg-[var(--brand-tint)] px-2.5 py-1 text-[11px] font-bold text-[var(--brand-primary)]">{it.badge}</span>}
                </div>
                <p className="ks-eyebrow mt-5">Input {i + 1}</p>
                <h3 className="ks-display mt-1 text-[20px] leading-tight text-[var(--text-strong)]">{it.title}</h3>
                <p className="mt-2.5 text-[14.5px] leading-[1.6] text-[var(--text-body)]">{it.body}</p>
                <div className="mt-4 border-t border-dashed border-[var(--border-subtle)] pt-3">
                  <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">Jadi otomatis</p>
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {it.outputs.map((o) => (
                      <li key={o} className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-card)] px-2.5 py-1 text-[12.5px] font-semibold text-[var(--text-strong)]">{o}</li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── TAMPILAN APLIKASI ── */}
      <section id="tampilan" className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
        <p className="ks-eyebrow text-[var(--brand-primary)]">Tampilan aplikasi</p>
        <h2 className="ks-display mt-3 max-w-[620px] text-[30px] leading-[1.12] text-[var(--text-strong)] sm:text-[38px]" style={{ textWrap: 'balance' }}>
          Seperti ini tampilannya di ponsel kasir Anda.
        </h2>
        <p className="mt-4 max-w-[620px] text-[16px] leading-[1.6] text-[var(--text-body)]">
          Tangkapan layar asli dari aplikasi yang dipakai hari ini, bukan gambar rancangan.
        </p>

        <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
          {SHOTS.map((sh) => (
            <figure key={sh.src} className="flex flex-col items-center">
              <div className="w-full max-w-[280px] rounded-[30px] border border-[var(--border-default)] bg-[var(--surface-inverse)] p-2 shadow-[0_24px_60px_-28px_rgba(20,10,40,0.55)]">
                <img
                  src={sh.src}
                  alt={`${BRAND} ${sh.title}`}
                  width={640}
                  height={1292}
                  loading="lazy"
                  className="w-full rounded-[24px] bg-[var(--surface-card)]"
                />
              </div>
              <figcaption className="mt-5 max-w-[300px] text-center">
                <p className="ks-display text-[17px] text-[var(--text-strong)]">{sh.title}</p>
                <p className="mt-1.5 text-[13.5px] leading-[1.55] text-[var(--text-muted)]">{sh.body}</p>
              </figcaption>
            </figure>
          ))}
        </div>

        <div className="mt-16 border-t border-[var(--border-subtle)] pt-12">
          <p className="ks-eyebrow text-[var(--brand-secondary)]">Dashboard pemilik</p>
          <h3 className="ks-display mt-3 max-w-[620px] text-[24px] leading-[1.15] text-[var(--text-strong)] sm:text-[30px]" style={{ textWrap: 'balance' }}>
            Yang kasir kerjakan, langsung terbaca di layar Anda.
          </h3>

          <div className="mt-8 space-y-6">
            {DASH_SHOTS.filter((d) => d.wide).map((d) => (
              <figure key={d.src}>
                <_Browser src={d.src} alt={`${BRAND} ${d.title}`} />
                <figcaption className="mt-4 max-w-[640px]">
                  <p className="ks-display text-[17px] text-[var(--text-strong)]">{d.title}</p>
                  <p className="mt-1.5 text-[14px] leading-[1.6] text-[var(--text-muted)]">{d.body}</p>
                </figcaption>
              </figure>
            ))}
            <div className="grid gap-6 md:grid-cols-2">
              {DASH_SHOTS.filter((d) => !d.wide).map((d) => (
                <figure key={d.src}>
                  <_Browser src={d.src} alt={`${BRAND} ${d.title}`} />
                  <figcaption className="mt-4">
                    <p className="ks-display text-[16px] text-[var(--text-strong)]">{d.title}</p>
                    <p className="mt-1.5 text-[13.5px] leading-[1.55] text-[var(--text-muted)]">{d.body}</p>
                  </figcaption>
                </figure>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center gap-3">
          <Link href="/download" className="ks-btn ks-btn-outline !w-auto">Unduh aplikasinya</Link>
          <Link href={`/${DEMO_SLUG}`} className="text-[14px] font-semibold text-[var(--brand-primary)] transition hover:opacity-80">Lihat toko demo</Link>
        </div>
      </section>

      {/* ── MODUL ── */}
      <section id="modul" className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
        <p className="ks-eyebrow text-[var(--text-muted)]">Apa yang kamu dapat</p>
        <h2 className="ks-display mt-3 max-w-[640px] text-[30px] leading-[1.12] text-[var(--text-strong)] sm:text-[38px]" style={{ textWrap: 'balance' }}>
          Dari kasir sampai laba rugi, tanpa berganti aplikasi.
        </h2>
        <p className="mt-4 max-w-[600px] text-[15px] leading-[1.6] text-[var(--text-muted)]">
          Kami tulis apa adanya: mana yang sudah berjalan dan mana yang masih dibangun.
        </p>
        <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => {
            const st = STATUS_LABEL[m.status];
            return (
              <article key={m.title} className="flex flex-col rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-card)] p-5">
                <div className="flex items-start justify-between gap-2">
                  <m.icon className="h-5 w-5 text-[var(--brand-secondary)]" />
                  <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-bold ${st.cls}`}>{st.text}</span>
                </div>
                <h3 className="ks-display mt-3 text-[17px] leading-tight text-[var(--text-strong)]">{m.title}</h3>
                <p className="mt-2 flex-1 text-[13.5px] leading-[1.55] text-[var(--text-body)]">{m.body}</p>
                {m.pro && <p className="mt-3 text-[11.5px] font-bold text-[var(--brand-secondary)]">Paket Pro</p>}
              </article>
            );
          })}
        </div>
      </section>

      {/* ── DUA HAL YANG BEDA ── */}
      <section className="border-y border-[var(--border-subtle)] bg-[var(--surface-card)]">
        <div className="mx-auto grid max-w-[1180px] gap-8 px-5 py-16 sm:px-6 md:grid-cols-2 lg:py-20">
          <article>
            <p className="ks-eyebrow text-[var(--brand-primary)]">Split bill warkop</p>
            <h3 className="ks-display mt-3 text-[26px] leading-[1.15] text-[var(--text-strong)]" style={{ textWrap: 'balance' }}>Satu meja, setiap orang membayar pesanannya sendiri.</h3>
            <p className="mt-3 text-[15px] leading-[1.62] text-[var(--text-body)]">
              Ada yang membayar lebih dulu dengan QRIS, ada yang tunai, ada yang baru datang pukul sepuluh. Kasir cukup
              mencentang pesanan per orang, bukan memaksa dibagi rata. Struk terbit per orang dan sisa tagihan meja selalu terlihat.
            </p>
          </article>
          <article>
            <p className="ks-eyebrow text-[var(--brand-primary)]">QRIS atas nama sendiri · tanpa komisi</p>
            <h3 className="ks-display mt-3 text-[26px] leading-[1.15] text-[var(--text-strong)]" style={{ textWrap: 'balance' }}>Uang QRIS masuk ke rekening Anda, bukan lewat kami.</h3>
            <p className="mt-3 text-[15px] leading-[1.62] text-[var(--text-body)]">
              Daftarkan Xendit atas nama Anda sendiri, pasang API key, selesai. Bukan pola &ldquo;gratis enam bulan lalu
              dipotong&rdquo;. {BRAND} tidak pernah memegang uang transaksi Anda.
            </p>
          </article>
        </div>
      </section>

      {/* ── HARGA ── */}
      <section id="harga" className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-20">
        <div className="text-center">
          <h2 className="ks-display text-[30px] leading-[1.12] text-[var(--text-strong)] sm:text-[38px]">Harga yang masuk akal untuk UMKM.</h2>
          <p className="mx-auto mt-4 max-w-[520px] text-[16px] leading-[1.6] text-[var(--text-body)]">
            Mulai gratis, bayar setelah bisnis berjalan. Transparan, tanpa biaya tersembunyi.
          </p>
        </div>
        <div className="mx-auto mt-10 grid max-w-[840px] gap-5 md:grid-cols-2">
          {PLANS.map((pl) => (
            <article
              key={pl.name}
              className={pl.dark
                ? 'rounded-[22px] bg-[var(--surface-inverse)] p-7 text-[var(--text-inverse)] shadow-[var(--glow-violet)]'
                : 'ks-card p-7'}
            >
              <span className={`inline-block rounded-full px-2.5 py-1 text-[11.5px] font-bold ${pl.dark ? 'bg-[image:var(--gradient-frekuensi)] text-[var(--text-on-brand)]' : 'bg-[var(--brand-tint)] text-[var(--brand-primary)]'}`}>{pl.badge}</span>
              <h3 className={`ks-display mt-3.5 text-[24px] ${pl.dark ? 'text-[var(--text-inverse)]' : 'text-[var(--text-strong)]'}`}>{pl.name}</h3>
              <p className={`text-[13.5px] ${pl.dark ? 'opacity-70' : 'text-[var(--text-muted)]'}`}>{pl.tagline}</p>
              <p className="mt-5 flex items-baseline gap-1.5">
                <span className={`ks-display text-[38px] ${pl.dark ? 'text-[var(--text-inverse)]' : 'text-[var(--text-strong)]'}`}>{pl.price}</span>
                <span className={`text-[14px] ${pl.dark ? 'opacity-70' : 'text-[var(--text-muted)]'}`}>/bln</span>
              </p>
              <ul className="mt-6 space-y-2.5">
                {pl.features.map((ft) => (
                  <li key={ft} className="flex items-start gap-2.5 text-[14.5px]">
                    <Check className={`mt-0.5 h-4 w-4 shrink-0 ${pl.dark ? 'text-[var(--mint-400)]' : 'text-[var(--success)]'}`} />
                    {ft}
                  </li>
                ))}
              </ul>
              <Link href={pl.href} className={`mt-7 flex w-full items-center justify-center ${pl.dark ? 'ks-btn' : 'ks-btn ks-btn-soft'}`}>{pl.cta}</Link>
            </article>
          ))}
        </div>
        <p className="mx-auto mt-6 max-w-[560px] text-center text-[13px] leading-relaxed text-[var(--text-muted)]">
          Toko demo menggunakan data contoh. Butuh lebih dari satu outlet? Tanyakan paket Business lewat WhatsApp.
        </p>
      </section>

      {/* ── FAQ ── */}
      <section className="border-y border-[var(--border-subtle)] bg-[var(--surface-card)]">
        <div className="mx-auto max-w-[780px] px-5 py-16 sm:px-6 lg:py-20">
          <h2 className="ks-display text-[30px] leading-[1.12] text-[var(--text-strong)] sm:text-[36px]">Pertanyaan yang sering muncul</h2>
          <div className="mt-8 border-y border-[var(--border-subtle)]">
            {FAQS.map((f) => (
              <details key={f.q} className="group border-b border-[var(--border-subtle)] py-4 last:border-b-0">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[15.5px] font-bold text-[var(--text-strong)]">
                  {f.q}
                  <ChevronDown className="h-4 w-4 shrink-0 text-[var(--text-muted)] transition group-open:rotate-180" />
                </summary>
                <p className="mt-3 text-[14.5px] leading-[1.65] text-[var(--text-body)]">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-6 lg:py-24">
        <div className="rounded-[26px] bg-[image:var(--gradient-aurora)] px-7 py-12 text-center text-[var(--text-on-brand)] sm:px-10 sm:py-16">
          <h2 className="ks-display mx-auto max-w-[600px] text-[30px] leading-[1.1] sm:text-[40px]" style={{ textWrap: 'balance' }}>
            Berhenti mencatat ulang apa yang kasir Anda sudah tahu.
          </h2>
          <p className="mx-auto mt-4 max-w-[520px] text-[16px] leading-[1.6] opacity-90">
            Coba gratis 30 hari. Tanpa kartu kredit dan tanpa syarat berbelit. Jika tidak cocok, tinggal berhenti.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className="inline-flex items-center gap-2 rounded-full bg-[var(--surface-card)] px-6 py-3.5 text-[15px] font-bold text-[var(--text-strong)] transition hover:opacity-90">
              Daftar gratis sekarang <ArrowRight className="h-4 w-4" />
            </Link>
            <a href={WA_LINK} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-full border border-white/40 px-6 py-3.5 text-[15px] font-bold text-[var(--text-on-brand)] transition hover:border-white">
              <MessageCircle className="h-4 w-4" /> Tanya via WhatsApp
            </a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[var(--border-subtle)]">
        <div className="mx-auto flex max-w-[1180px] flex-col items-center justify-between gap-4 px-5 py-8 text-[13px] text-[var(--text-muted)] sm:flex-row sm:px-6">
          <p>© {new Date().getFullYear()} {BRAND} · untuk UMKM Indonesia 🇮🇩</p>
          <nav className="flex flex-wrap items-center justify-center gap-5">
            <Link href={`/${DEMO_SLUG}`} className="transition hover:text-[var(--text-strong)]">Demo</Link>
            <Link href="/download" className="transition hover:text-[var(--text-strong)]">Download</Link>
            <Link href="/privacy" className="transition hover:text-[var(--text-strong)]">Privasi</Link>
            <Link href="/terms" className="transition hover:text-[var(--text-strong)]">Ketentuan</Link>
          </nav>
        </div>
      </footer>

      <LandingChat waLink={WA_LINK} />
    </div>
  );
}
