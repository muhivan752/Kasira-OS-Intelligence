import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Login — Kasira POS',
  description: 'Masuk ke akun Kasira. Kelola kasir, pantau penjualan, dan atur bisnis dari mana saja.',
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
