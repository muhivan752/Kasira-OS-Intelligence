import { CartProvider } from './CartContext';

export const dynamic = 'force-dynamic';

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
