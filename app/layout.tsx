import type {Metadata} from 'next';
import { Plus_Jakarta_Sans, Syne } from 'next/font/google';
import './globals.css'; // Global styles

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta',
  display: 'swap',
});

const syne = Syne({
  subsets: ['latin'],
  variable: '--font-syne',
  display: 'swap',
});

const SITE_URL = 'https://kasira.online';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'Kasira — POS Digital untuk UMKM Indonesia',
    template: '%s | Kasira',
  },
  description: 'Kasir digital modern dengan storefront gratis, QRIS tanpa komisi, dan AI insight untuk bisnis F&B dan UMKM Indonesia. Setup 5 menit, langsung jalan.',
  keywords: [
    'POS', 'kasir digital', 'kasir online', 'QRIS', 'aplikasi kasir',
    'storefront', 'cafe', 'UMKM', 'Indonesia', 'point of sale',
    'kasir gratis', 'manajemen stok', 'laporan penjualan',
  ],
  authors: [{ name: 'Kasira' }],
  creator: 'Kasira',
  openGraph: {
    type: 'website',
    locale: 'id_ID',
    url: SITE_URL,
    siteName: 'Kasira',
    title: 'Kasira — POS Digital untuk UMKM Indonesia',
    description: 'POS modern + storefront gratis + QRIS tanpa komisi. Masuk lewat WhatsApp, langsung jalan.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Kasira — POS Digital untuk UMKM Indonesia',
    description: 'POS modern + storefront gratis + QRIS tanpa komisi untuk cafe dan UMKM Indonesia.',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: SITE_URL,
  },
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="id" className={`${plusJakarta.variable} ${syne.variable}`}>
      <body className="font-sans antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
