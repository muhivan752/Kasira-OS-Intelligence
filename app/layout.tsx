import type {Metadata} from 'next';
import './globals.css'; // Global styles

export const metadata: Metadata = {
  title: 'Kasira — POS Digital untuk UMKM Indonesia',
  description: 'Kasir digital modern dengan storefront gratis, QRIS tanpa komisi, dan AI insight untuk bisnis F&B dan UMKM Indonesia.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
