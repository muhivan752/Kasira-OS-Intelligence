import Link from 'next/link';
import {
  Download,
  Smartphone,
  Shield,
  Wifi,
  WifiOff,
  CheckCircle2,
  ArrowRight,
  MessageCircle,
  Monitor,
} from 'lucide-react';
import Navbar from '@/components/landing/Navbar';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Download Kasira — Aplikasi Kasir Android',
  description: 'Download aplikasi Kasira POS untuk Android. Kasir digital offline-ready dengan QRIS, sync real-time, dan printer Bluetooth.',
  openGraph: {
    title: 'Download Kasira — Aplikasi Kasir Android',
    description: 'Kasir digital offline-ready untuk cafe dan UMKM Indonesia. Download APK gratis.',
  },
};

const APK_URL = 'https://github.com/muhivan752/Kasira-OS-Intelligence/releases/latest';

export default function DownloadPage() {
  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* Hero */}
      <section className="pt-32 pb-16 lg:pt-44 lg:pb-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-full text-sm font-semibold mb-6">
              <Smartphone className="w-4 h-4" />
              Android App
            </div>

            <h1 className="text-4xl md:text-6xl font-extrabold text-gray-900 tracking-tight leading-[1.1] mb-6">
              Unduh Aplikasi{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-emerald-700">
                Kasira POS
              </span>
            </h1>

            <p className="text-xl text-gray-500 mb-10 max-w-xl mx-auto leading-relaxed">
              Aplikasi kasir Android yang bisa jalan offline. Terima pembayaran, cetak struk, dan sync otomatis saat online.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href={APK_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-3 px-8 py-4 bg-emerald-500 text-white text-lg font-bold rounded-2xl hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-500/25 hover:-translate-y-0.5"
              >
                <Download className="w-5 h-5" />
                Download APK
              </a>
              <Link
                href="/register"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-gray-700 text-lg font-semibold rounded-2xl border-2 border-gray-200 hover:border-gray-300 transition-all"
              >
                Belum punya akun? Daftar
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* App Features */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">Apa yang bisa dilakukan app kasir?</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Smartphone, title: 'POS Lengkap', desc: 'Input order, cari produk, modifier, diskon. Semua dari genggaman.' },
              { icon: WifiOff, title: 'Offline Mode', desc: 'Tetap terima order dan bayar cash meski internet mati. Sync otomatis.' },
              { icon: Shield, title: 'QRIS Payment', desc: 'Terima pembayaran QRIS langsung dari app. Real-time notification.' },
            ].map(({ icon: Icon, title, desc }, i) => (
              <div key={i} className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
                <div className="w-11 h-11 bg-emerald-50 rounded-xl flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-emerald-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Install Steps */}
      <section className="py-16 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">Cara Install</h2>

          <div className="space-y-6">
            {[
              { num: '1', title: 'Download APK', desc: 'Klik tombol download di atas. File APK akan terunduh ke HP kamu.' },
              { num: '2', title: 'Izinkan instalasi', desc: 'Jika muncul peringatan, buka Settings → aktifkan "Install from unknown sources" atau "Allow from this source".' },
              { num: '3', title: 'Install & buka', desc: 'Tap file APK untuk install. Setelah selesai, buka app Kasira.' },
              { num: '4', title: 'Login', desc: 'Masuk dengan nomor WhatsApp yang kamu daftarkan. Masukkan PIN, langsung kasir.' },
            ].map(({ num, title, desc }) => (
              <div key={num} className="flex gap-4">
                <div className="shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold text-sm">
                  {num}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{title}</h3>
                  <p className="text-sm text-gray-500 mt-1">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-10 bg-blue-50 border border-blue-100 rounded-xl p-5">
            <h3 className="font-bold text-blue-900 mb-2">Belum punya akun?</h3>
            <p className="text-sm text-blue-700 mb-3">
              Kamu perlu daftar dulu sebelum bisa login di app kasir.
            </p>
            <Link href="/register" className="inline-flex items-center gap-2 text-sm font-bold text-blue-600 hover:text-blue-800">
              Daftar Gratis <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Two Platforms */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">2 Platform, 1 Sistem</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl p-7 border-2 border-emerald-500 shadow-md">
              <div className="flex items-center gap-3 mb-4">
                <Smartphone className="w-6 h-6 text-emerald-600" />
                <h3 className="text-lg font-bold text-gray-900">App Kasir (Android)</h3>
              </div>
              <p className="text-sm text-gray-500 mb-4">Untuk kasir di toko — input order, terima bayaran, cetak struk.</p>
              <ul className="space-y-2 text-sm">
                {['Offline mode', 'Printer Bluetooth', 'QRIS Payment', 'PIN login kasir', 'Shift management'].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <a
                href={APK_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-6 w-full block text-center px-5 py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors text-sm"
              >
                Download APK
              </a>
            </div>

            <div className="bg-white rounded-2xl p-7 border border-gray-200">
              <div className="flex items-center gap-3 mb-4">
                <Monitor className="w-6 h-6 text-blue-600" />
                <h3 className="text-lg font-bold text-gray-900">Dashboard Web</h3>
              </div>
              <p className="text-sm text-gray-500 mb-4">Untuk owner — kelola menu, pantau laporan, atur bisnis dari mana saja.</p>
              <ul className="space-y-2 text-sm">
                {['Akses dari browser', 'Laporan real-time', 'Kelola menu & stok', 'AI Insight (Pro)', 'Reservasi (Pro)'].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/dashboard"
                className="mt-6 w-full block text-center px-5 py-3 bg-white text-gray-900 border-2 border-gray-200 font-bold rounded-xl hover:bg-gray-50 transition-colors text-sm"
              >
                Buka Dashboard
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="py-16 bg-white">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Ada pertanyaan?</h2>
          <p className="text-gray-500 mb-6">Tim kami siap bantu via WhatsApp.</p>
          <a
            href="https://wa.me/6285270782220?text=Halo%20Kasira%2C%20saya%20butuh%20bantuan"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white font-bold rounded-xl hover:bg-gray-800 transition-colors text-sm"
          >
            <MessageCircle className="w-4 h-4" />
            Chat WhatsApp
          </a>
        </div>
      </section>
    </div>
  );
}
