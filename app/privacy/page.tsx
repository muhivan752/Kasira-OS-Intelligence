import Navbar from '@/components/landing/Navbar';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata = {
  title: 'Kebijakan Privasi',
  description: 'Kebijakan Privasi (Privacy Policy) Kasira. Menjelaskan bagaimana kami mengumpulkan, menggunakan, dan melindungi data Anda sesuai UU PDP.',
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />
      <div className="pt-32 pb-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link href="/" className="inline-flex items-center gap-2 text-emerald-600 hover:text-emerald-700 font-medium mb-8">
          <ArrowLeft className="w-4 h-4" /> Kembali ke Beranda
        </Link>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 mb-4">Kebijakan Privasi</h1>
        <p className="text-gray-500 mb-8">Terakhir diperbarui: {new Date().toLocaleDateString('id-ID')}</p>
        
        <div className="prose prose-emerald max-w-none text-gray-700">
          <p>
            Selamat datang di Kasira. Kebijakan Privasi ini menjelaskan bagaimana kami mengumpulkan, menggunakan, mengungkapkan, dan melindungi informasi pribadi Anda saat Anda menggunakan aplikasi Kasira, situs web, dan layanan terkait (secara kolektif disebut "Layanan").
          </p>
          <p>
            Dengan menggunakan Layanan kami, Anda menyetujui pengumpulan dan penggunaan informasi sesuai dengan kebijakan ini. Kebijakan ini tunduk pada hukum Republik Indonesia, termasuk Undang-Undang Pelindungan Data Pribadi (UU PDP).
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">1. Informasi yang Kami Kumpulkan</h2>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li><strong>Informasi Pendaftaran:</strong> Nama, nomor telepon (WhatsApp), email, nama bisnis, jenis bisnis, dan PIN kasir yang Anda berikan saat mendaftar.</li>
            <li><strong>Informasi Transaksi:</strong> Data pesanan, produk, harga, dan metode pembayaran yang diproses melalui Kasira. Kami tidak menyimpan informasi lengkap kartu kredit Anda (diproses oleh Payment Gateway resmi).</li>
            <li><strong>Data Penggunaan & Perangkat:</strong> Alamat IP, jenis browser, versi aplikasi, waktu akses, dan interaksi dalam aplikasi (dikumpulkan secara anonim untuk peningkatan fitur).</li>
            <li><strong>Informasi Pelanggan Anda:</strong> Nama dan kontak pelanggan Anda (jika dimasukkan), yang dikumpulkan atas nama Anda sebagai Pengendali Data.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">2. Bagaimana Kami Menggunakan Informasi Anda</h2>
          <p>Kami menggunakan data yang dikumpulkan untuk:</p>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Menyediakan, mengoperasikan, dan memelihara Layanan Kasira.</li>
            <li>Memproses transaksi dan mengirim pemberitahuan (seperti OTP dan struk digital via WhatsApp).</li>
            <li>Mengirimkan informasi berlangganan, tagihan, dan peringatan teknis.</li>
            <li>Meningkatkan kualitas Layanan dan mengembangkan fitur baru (seperti AI insight).</li>
            <li>Mencegah penipuan dan menjaga keamanan akun Anda.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">3. Penyimpanan dan Keamanan Data</h2>
          <p>
            Data Anda disimpan di server yang berlokasi di Indonesia dengan standar enkripsi AES-256. Kami melakukan backup otomatis dan menerapkan langkah-langkah keamanan (seperti Row-Level Security) untuk mencegah akses tidak sah, kebocoran, atau perubahan data pribadi.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">4. Hak Pengguna (Sesuai UU PDP)</h2>
          <p>Sebagai pemilik data pribadi, Anda berhak untuk:</p>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Meminta akses ke salinan data pribadi yang kami simpan.</li>
            <li>Memperbarui atau mengoreksi data pribadi Anda.</li>
            <li>Meminta penghapusan data pribadi Anda (Hak untuk Dilupakan) dengan menghubungi dukungan kami.</li>
            <li>Menarik kembali persetujuan penggunaan data pribadi.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">5. Pembagian Data ke Pihak Ketiga</h2>
          <p>
            Kami tidak akan menjual atau menyewakan informasi Anda kepada pihak ketiga. Kami hanya membagikan informasi dalam kondisi:
          </p>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li><strong>Penyedia Layanan:</strong> Seperti Payment Gateway (Xendit) untuk memproses pembayaran, atau provider WhatsApp (Fonnte) untuk mengirim OTP dan notifikasi.</li>
            <li><strong>Kewajiban Hukum:</strong> Jika diwajibkan oleh hukum atau permintaan otoritas berwenang di Indonesia.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">6. Hubungi Kami</h2>
          <p>
            Jika Anda memiliki pertanyaan tentang Kebijakan Privasi ini atau ingin menggunakan hak Anda terkait data pribadi, Anda dapat menghubungi kami melalui WhatsApp di nomor layanan pelanggan kami: <strong>+62-852-7078-2220</strong>.
          </p>
        </div>
      </div>
    </div>
  );
}
