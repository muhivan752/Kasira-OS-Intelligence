import Link from 'next/link';
import { ChevronDown } from 'lucide-react';
import Navbar from '@/components/landing/Navbar';
import Footer from '@/components/landing/Footer';
import LandingChat from '@/components/landing/LandingChat';
import { BRAND, SITE_URL, WA_LINK, DEMO_SLUG } from '@/lib/brand';

const modules = [
  ['Kasir & pembayaran', 'Pesanan, varian produk, diskon, shift, dan struk. Kasir Android mendukung transaksi tunai saat offline.'],
  ['Stok & resep', 'Kelola stok produk jadi. Pada paket Pro, gunakan resep untuk menghitung pemakaian bahan dan HPP.'],
  ['Pembelian', 'Catat pembelian, supplier, tagihan, dan jatuh tempo. Unggah nota untuk membantu pengisian data belanja.'],
  ['Keuangan & laporan', 'Periksa penjualan, laba rugi, arus kas, dan pengeluaran dari dashboard pemilik.'],
  ['Pelanggan & promo', 'Simpan riwayat pelanggan. Kelola loyalitas dan promo WhatsApp sesuai paket dan konfigurasi toko.'],
  ['Toko online', 'Bagikan halaman menu, terima pesanan, dan pantau statusnya. Pelanggan memesan melalui browser.'],
];

const plans = [
  { name: 'Starter', price: '99.000', audience: 'Untuk warung, kios, dan toko kecil.', href: '/register',
    features: ['1 outlet dan 1 kasir', 'Kasir Android dengan mode offline', 'Halaman toko online', 'Pembelian dan tagihan supplier', 'Pelanggan dan laporan penjualan'] },
  { name: 'Pro', price: '299.000', audience: 'Untuk kafe dan restoran yang mengelola bahan baku.', href: '/register?tier=pro',
    features: ['Seluruh fitur Starter', 'Resep, bahan baku, dan HPP', 'Split bill dan reservasi meja', 'Program loyalitas dan layar dapur', 'Asisten usaha melalui WhatsApp'] },
];

const faqs = [
  { q: 'Apa yang perlu disiapkan untuk mulai?', a: 'Daftarkan akun, isi informasi usaha, lalu tambahkan menu atau produk. Dashboard tersedia melalui browser; aplikasi kasir dapat diunduh untuk Android.' },
  { q: 'Bagaimana masa uji coba 30 hari berlaku?', a: 'Anda dapat mencoba Selaris selama 30 hari tanpa kartu kredit. Setelah masa uji coba selesai, pilih paket berlangganan untuk melanjutkan penggunaan.' },
  { q: 'Apa perbedaan stok sederhana dan stok berbasis HPP?', a: 'Stok sederhana menghitung jumlah produk jadi. Mode HPP pada paket Pro menghitung bahan baku berdasarkan resep. Siapkan bahan dan resep setiap menu sebelum beralih mode.' },
  { q: 'Apakah transaksi QRIS dikenakan biaya?', a: 'Selaris tidak menambahkan komisi saat toko menghubungkan akun payment gateway sendiri. Biaya transaksi mengikuti ketentuan penyedia pembayaran. Aktivasi dilakukan melalui pengaturan toko.' },
  { q: 'Apakah kasir bisa digunakan tanpa internet?', a: 'Aplikasi kasir Android mendukung transaksi tunai saat offline. Sinkronisasi dan layanan yang terhubung ke server memerlukan koneksi internet.' },
];

const jsonLd = [
  { '@context': 'https://schema.org', '@type': 'SoftwareApplication', name: BRAND, url: SITE_URL,
    applicationCategory: 'BusinessApplication', operatingSystem: 'Android, Web',
    description: 'Kasir, stok, pembelian, pelanggan, dan laporan untuk usaha.',
    offers: plans.map(plan => ({ '@type': 'Offer', name: plan.name, price: plan.price.replace('.', ''), priceCurrency: 'IDR' })) },
  { '@context': 'https://schema.org', '@type': 'Organization', name: BRAND, url: SITE_URL, logo: `${SITE_URL}/favicon.svg` },
  { '@context': 'https://schema.org', '@type': 'FAQPage', mainEntity: faqs.map(f => ({ '@type': 'Question', name: f.q, acceptedAnswer: { '@type': 'Answer', text: f.a } })) },
];

export default function HomePage() {
  return <div className="public-shell">
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }} />
    <Navbar />
    <main>
      <section className="public-container landing-hero">
        <div className="landing-intro">
          <p className="public-label">Selaris untuk usaha Anda</p>
          <h1>Kasir dan catatan usaha,<br className="hidden sm:block" /> dalam satu tempat.</h1>
          <p className="public-lead">Kelola penjualan, stok, pembelian, dan pelanggan. Gunakan aplikasi kasir di toko, lalu periksa laporan melalui dashboard pemilik.</p>
          <div className="public-actions">
            <Link className="ks-btn" href="/register">Daftarkan usaha</Link>
            <Link className="ks-btn ks-btn-outline" href={`/${DEMO_SLUG}`}>Lihat toko demo</Link>
          </div>
          <p className="public-caption">Uji coba 30 hari. Tanpa kartu kredit.</p>
        </div>
        <figure className="landing-product">
          <div className="landing-product-label"><span>Dashboard pemilik</span><span>Data toko demo</span></div>
          {/* Existing captures show the product; the caption identifies demo data. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/app/web-overview.png" alt="Dashboard Selaris dengan ringkasan penjualan dan daftar produk terlaris dari toko demo" width={1440} height={900} fetchPriority="high" />
          <figcaption>Laporan penjualan dan aktivitas toko dalam satu tampilan.</figcaption>
        </figure>
      </section>

      <section id="cara-kerja" className="public-container public-section work-section">
        <div>
          <p className="public-label">Pembelian & persediaan</p>
          <h2>Catat belanja dari nota.</h2>
          <p className="public-lead">Unggah nota, periksa hasilnya, lalu simpan pembelian.</p>
          <p>Data pembelian, harga bahan, dan tagihan supplier dapat diperiksa dari dashboard. Anda tetap meninjau hasil pembacaan nota sebelum menyimpannya.</p>
          <Link href="/#modul" className="public-text-link">Lihat fitur pengelolaan toko</Link>
        </div>
        <figure className="public-figure">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/app/web-pembelian.png" alt="Halaman pembelian Selaris, menampilkan nota dan tagihan supplier dari toko demo" width={1440} height={900} loading="lazy" />
          <figcaption>Pembelian dan tagihan supplier · Data toko demo</figcaption>
        </figure>
      </section>

      <section id="tampilan" className="public-section app-section">
        <div className="public-container app-layout">
          <div>
            <p className="public-label">Toko online</p>
            <h2>Menu toko di ponsel pelanggan.</h2>
            <p className="public-lead">Bagikan halaman toko. Pelanggan dapat memilih produk, mengisi pesanan, dan memantau statusnya melalui browser.</p>
            <Link className="public-text-link" href={`/${DEMO_SLUG}`}>Buka menu toko demo</Link>
          </div>
          <div className="app-captures">
            {[
              { src: '/app/web-storefront.png', label: 'Menu toko demo' },
              { src: '/app/web-cart.png', label: 'Keranjang pesanan demo' },
            ].map(shot => <figure key={shot.src}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={shot.src} alt={`${shot.label} pada Selaris`} width={390} height={844} loading="lazy" />
              <figcaption>{shot.label}</figcaption>
            </figure>)}
          </div>
        </div>
      </section>

      <section id="modul" className="public-container public-section module-section">
        <div><p className="public-label">Pengelolaan toko</p><h2>Dari penjualan<br />sampai laporan.</h2>
          <p>Fitur tersedia sesuai paket dan pengaturan usaha.</p></div>
        <dl className="module-list">{modules.map(([title, description]) => <div key={title}>
          <dt>{title}</dt><dd>{description}</dd>
        </div>)}</dl>
      </section>

      <section id="harga" className="public-container public-section pricing-section">
        <div className="section-heading"><div><p className="public-label">Paket berlangganan</p><h2>Pilih sesuai kebutuhan toko.</h2></div>
          <p>Coba selama 30 hari sebelum berlangganan.</p></div>
        <div className="plan-list">{plans.map(plan => <article className="plan" key={plan.name}>
          <div><h3>{plan.name}</h3><p>{plan.audience}</p>
            <p className="plan-price"><span>Rp{plan.price}</span> / bulan</p></div>
          <ul>{plan.features.map(feature => <li key={feature}>{feature}</li>)}</ul>
          <Link href={plan.href} className={`ks-btn ${plan.name === 'Starter' ? 'ks-btn-outline' : ''}`}>Daftar paket {plan.name}</Link>
        </article>)}</div>
        <p className="public-caption">Mengelola lebih banyak outlet? <a href={WA_LINK} target="_blank" rel="noopener noreferrer">Diskusikan kebutuhan usaha Anda.</a></p>
      </section>

      <section className="public-container public-section faq-section">
        <div><p className="public-label">Sebelum mendaftar</p><h2>Pertanyaan umum.</h2>
          <a className="public-text-link" href={WA_LINK} target="_blank" rel="noopener noreferrer">Tanya tim Selaris</a></div>
        <div>{faqs.map(faq => <details key={faq.q}>
          <summary>{faq.q}<ChevronDown size={18} aria-hidden="true" /></summary><p>{faq.a}</p>
        </details>)}</div>
      </section>
      <section className="public-container registration-section">
        <div><h2>Siapkan toko Anda di Selaris.</h2><p>Mulai dari informasi usaha dan produk pertama.</p></div>
        <Link className="ks-btn" href="/register">Daftarkan usaha</Link>
      </section>
    </main>
    <Footer />
    <LandingChat waLink={WA_LINK} />
  </div>;
}
