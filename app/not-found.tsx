import Link from 'next/link';
import type { Metadata } from 'next';
import { BRAND } from '@/lib/brand';

/**
 * Halaman 404 bersama. Dipakai juga waktu slug toko nggak ada
 * (`app/[slug]/layout.tsx` manggil notFound()), jadi yang paling sering
 * mendarat di sini itu pelanggan yang salah ketik alamat toko. Karena itu
 * jalan keluarnya ke Jelajah, bukan ke halaman produk.
 */
export const metadata: Metadata = {
  title: 'Halaman tidak ditemukan',
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--bg-base)] px-4 text-[var(--text-body)]">
      <div className="ks-card w-full max-w-md p-8 text-center">
        <p className="ks-eyebrow">404</p>
        <h1 className="ks-display mt-2 text-[26px] font-extrabold leading-tight text-[var(--text-strong)]">
          Halaman ini tidak ada
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-[var(--text-muted)]">
          Alamatnya mungkin salah ketik, atau tokonya sudah tidak aktif. Coba periksa lagi tautan yang Anda terima.
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Link
            href="/jelajah"
            className="rounded-xl bg-[var(--brand-primary)] px-5 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Lihat toko yang ada
          </Link>
          <Link
            href="/"
            className="rounded-xl border border-[var(--border-default)] px-5 py-3 text-sm font-semibold text-[var(--text-body)] transition-colors hover:bg-[var(--brand-tint)]"
          >
            Beranda {BRAND}
          </Link>
        </div>
      </div>
    </main>
  );
}
