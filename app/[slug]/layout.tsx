import { SITE_URL, BRAND } from '@/lib/brand';
import type { Metadata } from 'next';
import { CartProvider } from './CartContext';

export const dynamic = 'force-dynamic';

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}`, { cache: 'no-store' });
    if (!res.ok) return {};
    const { data } = await res.json();
    const name = data?.outlet?.name || slug;
    const desc = `Pesan langsung dari ${name}. Dikonfirmasi toko, status pesanan bisa dilacak, bayar QRIS atau di kasir. Didukung ${BRAND}.`;
    return {
      title: `${name} · Pesan Online`,
      description: desc,
      openGraph: {
        title: `${name} · Pesan Online`,
        description: desc,
        url: `${SITE_URL}/${slug}`,
        images: data?.outlet?.cover_image_url ? [data.outlet.cover_image_url] : undefined,
      },
    };
  } catch {
    return {};
  }
}

export default async function StorefrontLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  return (
    <CartProvider slug={slug}>
      <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-body)]">
        {children}
      </div>
    </CartProvider>
  );
}
