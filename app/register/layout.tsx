import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Daftar Gratis — Kasira POS Digital',
  description: 'Daftar Kasira gratis, langsung pakai. Setup 5 menit, bisa transaksi hari ini. Kasir digital untuk cafe, warung, dan UMKM Indonesia.',
  openGraph: {
    title: 'Daftar Gratis — Kasira POS Digital',
    description: 'Buat akun Kasira gratis. POS + storefront + QRIS langsung jalan dalam 5 menit.',
  },
};

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return children;
}
