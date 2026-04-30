import type { Metadata } from 'next';
import Link from 'next/link';
import {
  Wallet, Smartphone, Receipt, CheckCircle2, ArrowRight,
  MessageCircle, Clock, Shield, Sparkles, RefreshCw,
} from 'lucide-react';
import Navbar from '@/components/landing/Navbar';

export const metadata: Metadata = {
  title: 'Jadi Agen Pulsa KasiraPay — Modal dari Kami',
  description:
    'Daftar jadi agen pulsa KasiraPay. Dapat saldo awal dagang dari admin, jualan pulsa & e-money via aplikasi HP. Cocok untuk warung & toko kelontong.',
  alternates: { canonical: 'https://kasira.online/pulsa-agen' },
  openGraph: {
    title: 'Jadi Agen Pulsa KasiraPay',
    description:
      'Modal dari kami, jualan pulsa harian, top up gampang via TF. Daftar online 5 menit.',
    url: 'https://kasira.online/pulsa-agen',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Jadi Agen Pulsa KasiraPay',
    description: 'Modal dari kami, jualan pulsa harian, top up gampang via TF.',
  },
  keywords: [
    'agen pulsa',
    'daftar agen pulsa online',
    'KasiraPay',
    'jualan pulsa',
    'agen e-wallet',
    'modal jualan pulsa',
    'agen pulsa Sumatera',
    'reseller pulsa Indonesia',
  ],
};

const REGISTER_URL = 'https://pulsa.kasira.online/app/register';
const WA_ADMIN = 'https://wa.me/6285270782220?text=Halo%20admin%2C%20saya%20mau%20daftar%20jadi%20agen%20pulsa%20KasiraPay';

const benefits = [
  {
    icon: Wallet,
    title: 'Saldo Awal Dagang dari Admin',
    desc: 'Mulai jualan tanpa setor modal dari kantong sendiri. Saldo awal dagang langsung masuk setelah KTP disetujui.',
  },
  {
    icon: Smartphone,
    title: 'Aplikasi Praktis di HP',
    desc: 'Pilih produk dari menu kategori (Pulsa, E-Wallet, Token PLN, dll), masukkan nomor pelanggan, transaksi dalam 5 detik.',
  },
  {
    icon: RefreshCw,
    title: 'Top Up Saldo Gampang',
    desc: 'Saldo habis? Transfer cash dari customer balik ke admin via TF, saldo aktif lagi. Cycle revolving.',
  },
  {
    icon: Receipt,
    title: 'Riwayat Transaksi Tercatat',
    desc: 'Semua transaksi otomatis tersimpan. Bisa cek kapan saja siapa beli pulsa apa, sukses atau gagal.',
  },
  {
    icon: Shield,
    title: 'Backed by Kasira',
    desc: 'KasiraPay didukung infrastruktur Kasira (POS digital aktif sejak 2024). Saldo aman, supplier verified Digiflazz.',
  },
  {
    icon: Sparkles,
    title: 'Untung di Tangan Lo',
    desc: 'Harga jual ke pelanggan kamu tentukan sendiri — lo lebih tahu kondisi pasar di area lo. Margin yang lo ambil = untung lo.',
  },
];

const steps = [
  {
    n: 1,
    title: 'Daftar Online',
    desc: 'Isi data toko + foto KTP via aplikasi web. 3 menit selesai.',
  },
  {
    n: 2,
    title: 'Tunggu Approval',
    desc: 'Admin review KTP dalam 1×24 jam. Notifikasi via WA pas disetujui.',
  },
  {
    n: 3,
    title: 'Saldo Masuk, Mulai Jualan',
    desc: 'Saldo awal dagang otomatis masuk. Login pakai OTP WA, langsung jualan ke customer.',
  },
];

const faq = [
  {
    q: 'Saldo awal dagang itu uang gratis?',
    a: 'Bukan. Itu modal kerja yang admin titipkan supaya kamu bisa mulai jualan tanpa setor sendiri. Cash dari customer kamu kumpulkan, lalu TF balik ke admin untuk isi saldo siklus berikutnya.',
  },
  {
    q: 'Berapa untung per transaksi?',
    a: 'Untung kamu = harga jual ke pelanggan dikurangi harga beli dari KasiraPay. Harga beli dari kami tampil di aplikasi sebelum kamu klik bayar. Harga jual ke pelanggan kamu tentukan sendiri — lo yang lebih tahu kondisi pasar di area lo. Biasanya agen ambil margin Rp 1.000–3.000 per transaksi.',
  },
  {
    q: 'Top up saldo gimana?',
    a: 'Transfer cash dari customer ke rekening admin (BCA/SeaBank/dll), kirim bukti TF via WA. Admin akan kredit saldo manual dalam 5–10 menit.',
  },
  {
    q: 'Aplikasinya bisa offline?',
    a: 'Belum, butuh internet aktif untuk transaksi. Tapi aplikasi ringan (PWA) — install di HP tanpa Play Store, jalan di Android & iOS.',
  },
  {
    q: 'Kalau KTP saya ditolak gimana?',
    a: 'Kamu tetap bisa pakai akun, cuma harus deposit saldo sendiri (TF dulu baru jualan). Admin akan kirim alasan penolakan via WA supaya bisa apply ulang.',
  },
];

// JSON-LD structured data for Google rich results.
// Service = KasiraPay sebagai layanan agen pulsa.
// FAQPage = 5 pertanyaan di section FAQ.
// BreadcrumbList = kasira.online > pulsa-agen.
const serviceLd = {
  '@context': 'https://schema.org',
  '@type': 'Service',
  serviceType: 'Agen Pulsa & E-Wallet Digital',
  provider: {
    '@type': 'Organization',
    name: 'KasiraPay',
    url: 'https://kasira.online/pulsa-agen',
    parentOrganization: {
      '@type': 'Organization',
      name: 'Kasira',
      url: 'https://kasira.online',
    },
  },
  areaServed: { '@type': 'Country', name: 'Indonesia' },
  description:
    'Layanan agen pulsa digital dengan saldo awal dagang dari admin. Agen jualan pulsa, e-money, token PLN, dan top-up game via aplikasi HP.',
  offers: {
    '@type': 'Offer',
    description: 'Saldo Awal Dagang gratis untuk mulai jualan setelah KTP disetujui',
    availability: 'https://schema.org/InStock',
    eligibleRegion: { '@type': 'Country', name: 'Indonesia' },
  },
};

const faqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: faq.map((item) => ({
    '@type': 'Question',
    name: item.q,
    acceptedAnswer: { '@type': 'Answer', text: item.a },
  })),
};

const breadcrumbLd = {
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Kasira', item: 'https://kasira.online' },
    { '@type': 'ListItem', position: 2, name: 'Agen Pulsa', item: 'https://kasira.online/pulsa-agen' },
  ],
};

export default function PulsaAgenPage() {
  return (
    <div className="min-h-screen bg-white font-sans">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(serviceLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }} />
      <Navbar />

      {/* HERO */}
      <section className="relative pt-28 pb-16 lg:pt-40 lg:pb-24 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(16,185,129,0.12),transparent)]" />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
              <Wallet className="w-4 h-4" />
              KasiraPay — Agen Pulsa Digital
            </div>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight leading-[1.1] mb-6">
              Jualan pulsa,{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-teal-600">
                modal dari kami
              </span>
            </h1>

            <p className="text-lg md:text-xl text-gray-500 mb-10 leading-relaxed max-w-2xl mx-auto">
              Daftar jadi agen pulsa KasiraPay, dapat saldo awal dagang dari admin, jualan ke
              customer warung kamu lewat aplikasi HP. Cocok buat toko kelontong, warung, dan
              UMKM Indonesia.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <a
                href={REGISTER_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-gray-900 text-white text-base font-bold rounded-xl hover:bg-gray-800 transition-all shadow-lg hover:-translate-y-0.5"
              >
                Daftar Agen Sekarang
                <ArrowRight className="w-4 h-4" />
              </a>
              <a
                href={WA_ADMIN}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-gray-700 text-base font-semibold rounded-xl border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all"
              >
                <MessageCircle className="w-4 h-4" />
                Tanya Admin Dulu
              </a>
            </div>

            <p className="mt-4 text-sm text-gray-400">Daftar online 5 menit, approval 1×24 jam.</p>
          </div>
        </div>
      </section>

      {/* BENEFITS */}
      <section className="py-16 lg:py-24 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-extrabold text-gray-900 mb-4">
              Kenapa pilih KasiraPay
            </h2>
            <p className="text-gray-500 max-w-2xl mx-auto">
              Lebih dari sekadar agen pulsa biasa. Kami sediakan modal awal, infrastruktur, dan
              aplikasi yang dipakai untuk jualan harian.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {benefits.map((b, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl p-6 border border-gray-100 hover:border-emerald-200 hover:shadow-md transition-all"
              >
                <div className="w-11 h-11 rounded-xl bg-emerald-50 flex items-center justify-center mb-4">
                  <b.icon className="w-5 h-5 text-emerald-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{b.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{b.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-16 lg:py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-extrabold text-gray-900 mb-4">
              Cara Daftar — 3 Langkah
            </h2>
            <p className="text-gray-500">Dari klik daftar sampai mulai jualan, max 1 hari.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {steps.map((s) => (
              <div
                key={s.n}
                className="relative bg-white rounded-2xl p-6 border border-gray-100"
              >
                <div className="absolute -top-4 left-6 w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white text-lg font-bold flex items-center justify-center shadow-md">
                  {s.n}
                </div>
                <div className="pt-4">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">{s.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-12 text-center">
            <a
              href={REGISTER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-emerald-600 text-white text-base font-bold rounded-xl hover:bg-emerald-700 transition-all shadow-lg hover:-translate-y-0.5"
            >
              Mulai Daftar
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* CASH FLOW EXAMPLE */}
      <section className="py-16 bg-emerald-50/40">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-2xl p-6 lg:p-10 border border-emerald-100 shadow-sm">
            <div className="flex items-center gap-3 mb-5">
              <Clock className="w-5 h-5 text-emerald-600" />
              <h3 className="text-xl font-bold text-gray-900">Contoh siklus jualan</h3>
            </div>
            <ol className="space-y-3 text-sm text-gray-600 leading-relaxed">
              <li className="flex gap-3">
                <span className="flex-none w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-xs">
                  1
                </span>
                <span>
                  KTP disetujui → admin titip <strong className="text-gray-900">Saldo Awal Dagang Rp 200.000</strong> ke akun KasiraPay kamu.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="flex-none w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-xs">
                  2
                </span>
                <span>
                  Pelanggan kamu mau pulsa Telkomsel 25K. Lo cek di app KasiraPay — harga belinya misal <strong className="text-gray-900">Rp 25.500</strong>. Lo bayar pakai saldo. Saldo tinggal Rp 174.500.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="flex-none w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-xs">
                  3
                </span>
                <span>
                  Lo jual ke pelanggan misal <strong className="text-gray-900">Rp 28.000</strong> (lo bebas tentukan harga jual sesuai kondisi pasar di area lo). Pelanggan bayar cash Rp 28.000 ke kamu.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="flex-none w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-xs">
                  4
                </span>
                <span>
                  Untung kamu = <strong className="text-gray-900">Rp 28.000 − Rp 25.500 = Rp 2.500</strong> per transaksi. Cash hasil jualan kamu kumpulkan, sebagian besar untuk TF balik ke admin (isi saldo siklus berikutnya), sisanya untung kamu.
                </span>
              </li>
            </ol>
            <div className="mt-6 rounded-xl bg-emerald-50 border border-emerald-100 p-4 text-sm text-emerald-900">
              <strong>Inti:</strong> Lo yang tentukan harga jual ke pelanggan — lo paling tahu pasar di area lo. KasiraPay sediakan modal kerja + harga beli yang competitive, untung di tangan lo.
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 lg:py-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl md:text-4xl font-extrabold text-gray-900 mb-10 text-center">
            Pertanyaan Sering Ditanya
          </h2>
          <div className="space-y-4">
            {faq.map((item, i) => (
              <details
                key={i}
                className="group bg-white border border-gray-200 rounded-xl px-5 py-4 hover:border-emerald-200 transition-colors"
              >
                <summary className="cursor-pointer list-none flex items-center justify-between gap-4">
                  <h3 className="text-base font-semibold text-gray-900">{item.q}</h3>
                  <span className="flex-none w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center group-open:rotate-45 transition-transform">
                    +
                  </span>
                </summary>
                <p className="mt-3 text-sm text-gray-500 leading-relaxed">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA FINAL */}
      <section className="py-16 lg:py-24 bg-gradient-to-br from-emerald-600 to-teal-700 text-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-extrabold mb-4">Siap mulai jualan pulsa?</h2>
          <p className="text-emerald-50 mb-8 text-lg leading-relaxed">
            Daftar 3 menit, KTP review 1×24 jam, langsung jualan. Modal dari kami.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href={REGISTER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-emerald-700 text-base font-bold rounded-xl hover:bg-emerald-50 transition-all shadow-lg"
            >
              Daftar Agen Sekarang
              <ArrowRight className="w-4 h-4" />
            </a>
            <a
              href={WA_ADMIN}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white/10 backdrop-blur text-white text-base font-semibold rounded-xl border border-white/30 hover:bg-white/20 transition-all"
            >
              <MessageCircle className="w-4 h-4" />
              Chat Admin di WA
            </a>
          </div>
          <p className="mt-6 text-emerald-100 text-sm">
            Atau mau pakai{' '}
            <Link href="/" className="underline hover:text-white">
              POS Kasira
            </Link>{' '}
            untuk warung kamu juga? Bisa keduanya.
          </p>
        </div>
      </section>
    </div>
  );
}
