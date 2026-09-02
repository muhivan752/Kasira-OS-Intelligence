import type {Metadata} from 'next';
import { Plus_Jakarta_Sans, Gabarito, Space_Mono } from 'next/font/google';
import './globals.css'; // Global styles

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta',
  display: 'swap',
});

// Display font for the "Aurora" redesign (headlines, brand wordmark, buttons)
const gabarito = Gabarito({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800', '900'],
  variable: '--font-gabarito',
  display: 'swap',
});

// Mono for numeric / receipt-style values
const spaceMono = Space_Mono({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-space-mono',
  display: 'swap',
});

import { SITE_URL } from '@/lib/brand';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'Selaris — POS Digital untuk UMKM Indonesia',
    template: '%s | Selaris',
  },
  description: 'Kasir digital yang ngisi pembukuan sendiri: stok, HPP, utang supplier, dan pelanggan terbentuk otomatis dari transaksi, nota belanja, dan nomor WA. Untuk cafe & UMKM Indonesia.',
  keywords: [
    'POS', 'kasir digital', 'kasir online', 'QRIS', 'aplikasi kasir',
    'storefront', 'cafe', 'UMKM', 'Indonesia', 'point of sale',
    'kasir gratis', 'manajemen stok', 'laporan penjualan',
  ],
  authors: [{ name: 'Selaris' }],
  creator: 'Selaris',
  openGraph: {
    type: 'website',
    locale: 'id_ID',
    url: SITE_URL,
    siteName: 'Selaris',
    title: 'Selaris — Kasir yang ngisi pembukuan sendiri',
    description: 'Kasir + stok + pembelian + pelanggan dalam satu aplikasi. Foto nota, HPP ke-update. QRIS tanpa komisi.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Selaris — Kasir yang ngisi pembukuan sendiri',
    description: 'Kasir + stok + pembelian + pelanggan dalam satu aplikasi untuk cafe dan UMKM Indonesia.',
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

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || '';

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="id" className={`${plusJakarta.variable} ${gabarito.variable} ${spaceMono.variable}`}>
      <head>
        {GA_ID && (
          <>
            <script async src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} />
            <script dangerouslySetInnerHTML={{ __html: `
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', '${GA_ID}');
            `}} />
          </>
        )}
      </head>
      <body className="font-sans antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
