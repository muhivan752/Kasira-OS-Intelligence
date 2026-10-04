import type {Metadata} from 'next';
import { Source_Sans_3, Source_Serif_4, Space_Mono } from 'next/font/google';
import './globals.css';

const sourceSans = Source_Sans_3({
  subsets: ['latin'],
  variable: '--font-source-sans',
  display: 'swap',
});

const sourceSerif = Source_Serif_4({
  subsets: ['latin'],
  variable: '--font-source-serif',
  display: 'swap',
});

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
    default: 'Selaris · POS Digital untuk UMKM Indonesia',
    template: '%s | Selaris',
  },
  description: 'Kelola kasir, stok, pembelian, pelanggan, dan laporan usaha dengan Selaris. Aplikasi Android untuk kasir dan dashboard web untuk pemilik.',
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
    title: 'Selaris · Kasir dan pengelolaan usaha',
    description: 'Kasir, stok, pembelian, pelanggan, dan laporan dalam satu sistem.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Selaris · Kasir dan pengelolaan usaha',
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
  // Google Search Console: cara verifikasi cadangan lewat meta tag. Jalur
  // utamanya TXT di DNS Cloudflare (satu properti buat semua subdomain);
  // isi env ini cuma kalau mau verifikasi per-URL dari HTML.
  verification: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
    ? { google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION }
    : undefined,
};

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || '';

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="id" className={`${sourceSans.variable} ${sourceSerif.variable} ${spaceMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: "try{document.documentElement.classList.toggle('dark',localStorage.getItem('selaris-theme')==='dark')}catch{}" }} />
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
