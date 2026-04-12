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
    const desc = `Pesan online dari ${name}. Menu lengkap, harga transparan, bayar via QRIS. Powered by Kasira.`;
    return {
      title: `${name} — Menu & Pesan Online`,
      description: desc,
      openGraph: {
        title: `${name} — Menu & Pesan Online`,
        description: desc,
        url: `https://kasira.online/${slug}`,
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
      <div className="min-h-screen bg-gray-50">
        {children}
      </div>
    </CartProvider>
  );
}
