import Navbar from '@/components/landing/Navbar';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata = {
  title: 'Syarat & Ketentuan',
  description: 'Syarat dan Ketentuan (Terms of Service) penggunaan aplikasi dan layanan Kasira.',
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />
      <div className="pt-32 pb-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link href="/" className="inline-flex items-center gap-2 text-emerald-600 hover:text-emerald-700 font-medium mb-8">
          <ArrowLeft className="w-4 h-4" /> Kembali ke Beranda
        </Link>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 mb-4">Syarat & Ketentuan</h1>
        <p className="text-gray-500 mb-8">Terakhir diperbarui: {new Date().toLocaleDateString('id-ID')}</p>
        
        <div className="prose prose-emerald max-w-none text-gray-700">
          <p>
            Dengan mendaftar dan menggunakan Kasira ("Layanan"), Anda menyetujui syarat dan ketentuan berikut ("Ketentuan Layanan"). Harap baca dengan saksama sebelum menggunakan Layanan kami.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">1. Akun dan Registrasi</h2>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Anda harus memberikan informasi yang akurat, termasuk nomor WhatsApp aktif dan informasi bisnis, saat mendaftar.</li>
            <li>Anda bertanggung jawab menjaga kerahasiaan PIN dan akses ke akun Kasira Anda.</li>
            <li>Kasira berhak menolak pendaftaran atau membatalkan akun jika ditemukan pelanggaran, penipuan, atau aktivitas ilegal.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">2. Layanan dan Ketersediaan (SLA)</h2>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Kasira disediakan dengan upaya terbaik (<i>best-effort</i>). Kami tidak menjamin 100% <i>uptime</i> (SLA tertulis).</li>
            <li>Aplikasi kasir dirancang dengan <strong>Offline Mode</strong>, memungkinkan Anda tetap melakukan transaksi saat koneksi internet terputus. Namun, sinkronisasi data ke cloud memerlukan koneksi internet aktif.</li>
            <li>Jika terjadi gangguan server di luar pemeliharaan terjadwal selama lebih dari 24 jam berturut-turut, kompensasi <i>prorate</i> (perpanjangan masa berlangganan) akan diberikan untuk hari yang terdampak.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">3. Biaya dan Pembayaran</h2>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Kami menawarkan masa uji coba gratis selama 30 hari. Setelah masa uji coba berakhir, Anda harus berlangganan paket berbayar (Starter, Pro, atau Business) untuk terus menggunakan layanan secara penuh.</li>
            <li>Biaya langganan ditagihkan setiap bulan. Semua pembayaran bersifat final dan tidak dapat di-<i>refund</i> secara sebagian.</li>
            <li>Pembatalan langganan dapat dilakukan kapan saja. Akun Anda akan tetap aktif hingga akhir periode penagihan yang telah dibayar.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">4. Penggunaan QRIS dan Payment Gateway</h2>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Kasira tidak memungut komisi tambahan untuk transaksi QRIS jika Anda menghubungkan akun Payment Gateway (Xendit) Anda sendiri (<i>Bring Your Own Key</i>).</li>
            <li>Anda bertanggung jawab atas kepatuhan terhadap kebijakan Payment Gateway (seperti dilarang menjual barang ilegal).</li>
            <li>Kasira tidak bertanggung jawab atas penahanan dana (<i>fund hold</i>) yang dilakukan oleh pihak Payment Gateway atas indikasi <i>fraud</i> atau perselisihan (<i>dispute</i>).</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">5. Pembatasan Tanggung Jawab</h2>
          <p>
            Kasira tidak bertanggung jawab atas kerugian finansial langsung, tidak langsung, insidental, atau konsekuensial yang diakibatkan oleh penggunaan atau ketidakmampuan menggunakan Layanan kami, termasuk namun tidak terbatas pada hilangnya data, hilangnya keuntungan bisnis, atau gangguan layanan yang disebabkan oleh Force Majeure.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">6. Perubahan Syarat & Ketentuan</h2>
          <p>
            Kasira berhak untuk memperbarui atau mengubah Syarat & Ketentuan ini kapan saja. Kami akan memberikan pemberitahuan yang wajar (seperti via aplikasi atau WhatsApp) tentang perubahan material apa pun. Jika Anda terus menggunakan Layanan setelah perubahan efektif, Anda dianggap telah menyetujui ketentuan yang direvisi.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">7. Hukum yang Berlaku</h2>
          <p>
            Syarat & Ketentuan ini tunduk pada dan ditafsirkan sesuai dengan hukum yang berlaku di Republik Indonesia. Segala perselisihan yang timbul sehubungan dengan Syarat & Ketentuan ini akan diselesaikan secara musyawarah atau melalui pengadilan negeri yang berwenang di Indonesia.
          </p>
        </div>
      </div>
    </div>
  );
}
