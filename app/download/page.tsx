import Link from 'next/link';
import type { Metadata } from 'next';
import Navbar from '@/components/landing/Navbar';
import Footer from '@/components/landing/Footer';
import versions from '@/version.json';

export const metadata: Metadata = {
  title: 'Download aplikasi Android',
  description: 'Unduh Selaris POS untuk kasir dan Selaris Dapur untuk pengelolaan pesanan di dapur.',
};

export default function DownloadPage() {
  return <div className="public-shell">
    <Navbar />
    <main className="public-container download-content">
      <div className="download-heading">
        <p className="public-label">Aplikasi Android</p>
        <h1>Selaris di toko Anda.</h1>
        <p className="public-lead">Pilih aplikasi sesuai perangkat dan tugas tim. Dashboard pemilik tetap dapat diakses melalui browser.</p>
      </div>
      <section aria-label="Pilihan aplikasi" className="download-list">
        <article>
          <div><h2>Selaris POS</h2><p>Untuk kasir: pesanan, pembayaran, shift, dan cetak struk Bluetooth. Transaksi tunai tetap tersedia saat offline.</p>
            <span className="public-caption">Android · Versi {versions.pos.version}</span></div>
          <a href="/api/download/pos" className="ks-btn">Unduh APK POS</a>
        </article>
        <article>
          <div><h2>Selaris Dapur</h2><p>Untuk tim dapur: lihat pesanan masuk dan perbarui status pengerjaan. Tersedia untuk paket Pro.</p>
            <span className="public-caption">Android · Versi {versions.dapur.version}</span></div>
          <a href="/api/download/dapur" className="ks-btn ks-btn-outline">Unduh APK Dapur</a>
        </article>
      </section>
      <section className="download-install">
        <div><p className="public-label">Instalasi</p><h2>Pasang di perangkat kasir.</h2></div>
        <ol>
          <li><strong>Unduh file APK.</strong><p>Pilih aplikasi di atas, lalu buka file yang sudah diunduh.</p></li>
          <li><strong>Izinkan pemasangan.</strong><p>Jika Android meminta izin, aktifkan izin instalasi untuk browser yang digunakan.</p></li>
          <li><strong>Buka aplikasi dan masuk.</strong><p>Gunakan akun usaha atau PIN kasir yang sudah didaftarkan. Untuk pembaruan, pasang langsung tanpa menghapus aplikasi lama.</p></li>
        </ol>
      </section>
      <div className="download-account"><p>Belum memiliki akun usaha?</p><Link className="public-text-link" href="/register">Daftarkan usaha</Link>
        <Link className="public-text-link" href="/dashboard">Buka dashboard</Link></div>
    </main>
    <Footer />
  </div>;
}
