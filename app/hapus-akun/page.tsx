import Navbar from '@/components/landing/Navbar';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { BRAND, COMPANY_EMAIL, COMPANY_NAME } from '@/lib/brand';

// URL ini didaftarkan di Play Console (Data safety > penghapusan akun).
// Aturan sebenarnya: backend/services/account_deletion.py. Kalau masa
// tenggang atau daftar data yang disimpan berubah, ubah halaman ini juga.
export const metadata = {
  title: 'Hapus Akun',
  description: `Cara menghapus akun ${BRAND} dan data usaha, beserta data yang dihapus dan yang disimpan.`,
};

const h2 = 'text-xl font-bold text-gray-900 mt-8 mb-4';
const list = 'list-disc pl-6 space-y-2 mb-6';

export default function DeleteAccountPage() {
  return (
    <div className="public-shell font-sans">
      <Navbar />
      <div className="pt-32 pb-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link href="/" className="inline-flex items-center gap-2 text-emerald-600 hover:text-emerald-700 font-medium mb-8">
          <ArrowLeft className="w-4 h-4" /> Kembali ke Beranda
        </Link>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 mb-4">Hapus Akun {BRAND}</h1>
        <p className="text-gray-500 mb-8">Berlaku untuk aplikasi {BRAND} POS, {BRAND} Dapur, dan dashboard web. Dikelola oleh {COMPANY_NAME}.</p>

        <div className="prose prose-emerald max-w-none text-gray-700">
          <h2 className={h2}>Cara menghapus akun</h2>
          <ul className={list}>
            {/* Tombol di app POS dan Dapur sudah ada di source (account_deletion_page.dart)
                tapi APK-nya belum dirilis. Saat rilis, tambahkan: "Di aplikasi: buka
                Pengaturan, pilih Hapus Akun, lalu ketik HAPUS." */}
            <li><strong>Di web:</strong> masuk ke <Link href="/login">dashboard</Link>, buka Akun saya, lalu pilih Hapus akun.</li>
            <li><strong>Tidak bisa masuk:</strong> kirim email ke <a href={`mailto:${COMPANY_EMAIL}`}>{COMPANY_EMAIL}</a> dari email atau dengan nomor HP yang terdaftar. Kami memproses permintaan paling lambat 3 x 24 jam.</li>
          </ul>

          <h2 className={h2}>Akun pemilik usaha</h2>
          <p>
            Menghapus akun pemilik menghapus seluruh usaha. Penghapusan dijalankan 30 hari setelah permintaan. Selama 30 hari itu {BRAND} tetap berjalan normal dan permintaan bisa dibatalkan dari halaman yang sama.
          </p>
          <p>Yang dihapus:</p>
          <ul className={list}>
            <li>Akun pemilik dan semua akun karyawan</li>
            <li>Outlet, menu, resep, stok, pembelian, dan pemasok</li>
            <li>Pesanan, pembayaran, meja, reservasi, shift kas, dan catatan keuangan</li>
            <li>Data pelanggan, poin loyalitas, voucher, dan riwayat promosi</li>
            <li>Data karyawan, jadwal, dan absensi</li>
            <li>Foto yang diunggah, percakapan dengan asisten AI, dan catatan aktivitas</li>
          </ul>
          <p>Yang disimpan:</p>
          <ul className={list}>
            <li>Tagihan dan pembayaran langganan {BRAND}, tanpa nama usaha, sebagai catatan pembukuan {COMPANY_NAME}.</li>
            <li>Catatan referral bila usaha Anda mereferensikan atau direferensikan usaha lain, karena catatan itu juga milik usaha tersebut.</li>
          </ul>
          <p>Salinan cadangan database ikut terhapus paling lambat 14 hari setelah penghapusan.</p>

          <h2 className={h2}>Akun karyawan</h2>
          <p>
            Karyawan dapat menghapus akun login miliknya kapan saja. Akun langsung dihapus dan keluar dari semua perangkat. Nama, nomor HP, username, password, PIN, dan akun Google yang terhubung dihapus. Transaksi yang pernah dicatat karyawan tetap tersimpan di usaha tempatnya bekerja, karena data itu milik usaha. Profil karyawan dan absensi dikelola oleh pemilik usaha.
          </p>

          <p className="mt-8">
            Baca juga <Link href="/privacy">Kebijakan Privasi</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}
