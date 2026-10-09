import Navbar from '@/components/landing/Navbar';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { COMPANY_CITY, COMPANY_EMAIL, COMPANY_NAME } from '@/lib/brand';

export const metadata = {
  title: 'Kebijakan Privasi',
  description: 'Kebijakan Privasi (Privacy Policy) Selaris. Menjelaskan bagaimana kami mengumpulkan, menggunakan, dan melindungi data Anda sesuai UU PDP.',
};

export default function PrivacyPolicyPage() {
  return (
    <div className="public-shell font-sans">
      <Navbar />
      <div className="pt-32 pb-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link href="/" className="inline-flex items-center gap-2 text-emerald-600 hover:text-emerald-700 font-medium mb-8">
          <ArrowLeft className="w-4 h-4" /> Kembali ke Beranda
        </Link>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 mb-4">Kebijakan Privasi</h1>
        <p className="text-gray-500 mb-8">Terakhir diperbarui: 9 Oktober 2026</p>
        
        <div className="prose prose-emerald max-w-none text-gray-700">
          <p>
            Selamat datang di Selaris. Selaris dikelola oleh {COMPANY_NAME} ("kami"), berkedudukan di {COMPANY_CITY}, Indonesia. Kebijakan Privasi ini menjelaskan bagaimana kami mengumpulkan, menggunakan, mengungkapkan, dan melindungi informasi pribadi Anda saat Anda menggunakan aplikasi Selaris, situs web, dan layanan terkait (secara kolektif disebut "Layanan").
          </p>
          <p>
            Dengan menggunakan Layanan kami, Anda menyetujui pengumpulan dan penggunaan informasi sesuai dengan kebijakan ini. Kebijakan ini tunduk pada hukum Republik Indonesia, termasuk Undang-Undang Pelindungan Data Pribadi (UU PDP).
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">1. Informasi yang Kami Kumpulkan</h2>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li><strong>Akun pemilik dan karyawan:</strong> Nama, nomor HP, email, akun Google bila Anda masuk dengan Google, username, password dan PIN kasir (disimpan dalam bentuk hash), serta peran dan izin akses.</li>
            <li><strong>Data usaha:</strong> Nama usaha, outlet, alamat, menu, harga, resep, stok, pembelian, nota pemasok, dan catatan keuangan yang Anda masukkan.</li>
            <li><strong>Transaksi:</strong> Pesanan, pembayaran, meja, reservasi, dan shift kas. Data kartu tidak kami simpan; pembayaran nontunai diproses oleh Xendit.</li>
            <li><strong>Data karyawan:</strong> Profil karyawan, jadwal kerja, dan absensi yang dicatat lewat fitur Tim & absensi.</li>
            <li><strong>Data pelanggan Anda:</strong> Nama, nomor WhatsApp, riwayat kunjungan, dan poin loyalitas pelanggan yang Anda atau kasir Anda catat.</li>
            <li><strong>Lokasi outlet:</strong> Koordinat perangkat kasir dikirim satu kali sesudah login, hanya bila Anda memberi izin lokasi, untuk melengkapi alamat outlet. Lokasi tidak dilacak terus-menerus.</li>
            <li><strong>Foto dan percakapan AI:</strong> Foto nota yang Anda unggah untuk dibaca otomatis, serta pertanyaan Anda kepada asisten AI Selaris di aplikasi, dashboard, situs web, atau WhatsApp.</li>
            <li><strong>Data teknis:</strong> Alamat IP, jenis perangkat dan browser, versi aplikasi, token notifikasi, catatan error, dan statistik kunjungan situs web.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">2. Bagaimana Kami Menggunakan Informasi Anda</h2>
          <p>Kami menggunakan data tersebut untuk:</p>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Menjalankan kasir, dapur, stok, keuangan, absensi, dan fitur Selaris lainnya.</li>
            <li>Mengirim kode masuk, struk digital, dan notifikasi lewat WhatsApp, aplikasi Sefrekuensi, atau notifikasi aplikasi.</li>
            <li>Memproses pembayaran QRIS dan pembayaran nontunai lain.</li>
            <li>Menjawab pertanyaan Anda lewat asisten AI dan menyusun ringkasan serta saran usaha dari data toko Anda.</li>
            <li>Menagih langganan dan mengirim informasi penting tentang akun.</li>
            <li>Mendeteksi error, mencegah penyalahgunaan, dan menjaga keamanan akun.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">3. Peran Kami atas Data Pelanggan dan Karyawan Anda</h2>
          <p>
            Untuk data pelanggan dan karyawan yang Anda masukkan, Anda bertindak sebagai Pengendali Data dan kami sebagai Prosesor Data. Kami memproses data tersebut hanya untuk menjalankan Layanan bagi Anda. Anda bertanggung jawab memastikan pelanggan dan karyawan Anda mengetahui datanya dicatat, termasuk persetujuan pelanggan sebelum menerima pesan promosi.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">4. Pihak Ketiga yang Memproses Data</h2>
          <p>
            Kami tidak menjual atau menyewakan data Anda. Data dibagikan hanya kepada penyedia yang membantu menjalankan Layanan, sebatas yang dibutuhkan masing-masing:
          </p>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li><strong>Vultr (Singapura):</strong> Server tempat aplikasi dan database Selaris berjalan.</li>
            <li><strong>Cloudflare:</strong> Jaringan pengantar situs dan API, serta penyimpanan cadangan database (R2).</li>
            <li><strong>DeepSeek:</strong> Model AI untuk asisten chat, ringkasan Beranda, saran menu, dan bot WhatsApp. Pertanyaan Anda dan data toko yang relevan, seperti penjualan dan menu, dikirim untuk menyusun jawaban.</li>
            <li><strong>Anthropic:</strong> Model AI untuk membaca foto nota dan saran harga. Foto nota dan data harga yang relevan dikirim untuk diproses.</li>
            <li><strong>Xendit:</strong> Pemrosesan pembayaran QRIS dan pembayaran nontunai.</li>
            <li><strong>Fonnte:</strong> Pengiriman pesan WhatsApp: kode masuk, struk digital, dan notifikasi.</li>
            <li><strong>Sefrekuensi:</strong> Aplikasi milik perusahaan yang sama. Bila Anda memilih menerima kode masuk lewat Sefrekuensi, nomor HP Anda dicocokkan dengan akun Sefrekuensi untuk mengirim kode tersebut.</li>
            <li><strong>Google:</strong> Masuk dengan akun Google (Firebase Authentication), notifikasi aplikasi (Firebase Cloud Messaging), dan statistik kunjungan situs (Google Analytics).</li>
            <li><strong>Sentry:</strong> Pencatatan error teknis agar gangguan cepat diperbaiki.</li>
            <li><strong>OpenStreetMap (Nominatim):</strong> Mengubah koordinat outlet menjadi alamat.</li>
            <li><strong>Kewajiban hukum:</strong> Bila diwajibkan oleh hukum atau permintaan otoritas berwenang di Indonesia.</li>
          </ul>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">5. Lokasi Penyimpanan dan Transfer ke Luar Negeri</h2>
          <p>
            Server Selaris berada di Singapura. Sebagian penyedia di atas memproses data di negara lain, termasuk Amerika Serikat dan Tiongkok. Kami memilih penyedia yang menerapkan pelindungan data yang memadai, mengirim data sebatas yang dibutuhkan, dan memakai koneksi terenkripsi (HTTPS) untuk setiap pengiriman. Dengan menggunakan Layanan, Anda menyetujui transfer data tersebut sesuai Undang-Undang Pelindungan Data Pribadi.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">6. Keamanan dan Masa Simpan</h2>
          <p>
            Data setiap usaha dipisahkan di tingkat database (Row-Level Security). Password dan PIN disimpan dalam bentuk hash, kunci pembayaran Xendit disimpan terenkripsi, dan seluruh koneksi memakai HTTPS. Database dicadangkan secara berkala.
          </p>
          <p>
            Data disimpan selama akun Anda aktif. Sesudah akun dihapus, data dihapus dari sistem utama, kecuali catatan yang wajib kami simpan menurut hukum. Salinan di cadangan terhapus sesuai siklus cadangan.
          </p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">7. Hak Anda (Sesuai UU PDP)</h2>
          <p>Anda berhak untuk:</p>
          <ul className="list-disc pl-6 space-y-2 mb-6">
            <li>Meminta akses atau salinan data pribadi yang kami simpan.</li>
            <li>Memperbarui atau mengoreksi data pribadi Anda.</li>
            <li>Meminta penghapusan akun dan data pribadi Anda.</li>
            <li>Menarik kembali persetujuan, termasuk izin lokasi lewat pengaturan perangkat.</li>
          </ul>
          <p>Permintaan dapat dikirim lewat kontak di bawah dan kami proses paling lambat 3 x 24 jam sesuai UU PDP.</p>

          <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">8. Hubungi Kami</h2>
          <p>
            Jika Anda memiliki pertanyaan tentang Kebijakan Privasi ini atau ingin menggunakan hak Anda terkait data pribadi, Anda dapat menghubungi kami melalui WhatsApp di nomor layanan pelanggan kami: <strong>+62-852-7078-2220</strong>, atau email ke <a href={`mailto:${COMPANY_EMAIL}`}>{COMPANY_EMAIL}</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
