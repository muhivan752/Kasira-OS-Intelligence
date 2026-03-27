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

export const metadata: Metadata = {
  title: 'Kasira — POS Digital untuk UMKM Indonesia',
  description: 'Kasir digital modern dengan storefront gratis, QRIS tanpa komisi, dan AI insight untuk bisnis F&B dan UMKM Indonesia.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="id" className={`${plusJakarta.variable} ${syne.variable}`}>
      <body className="font-sans antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
