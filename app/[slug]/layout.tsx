'use client';

import { CartProvider } from './CartContext';
import { useParams } from 'next/navigation';

export default function StorefrontLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const slug = params.slug as string;

  return (
    <CartProvider slug={slug}>
      <div className="min-h-screen bg-gray-50 pb-24">
        {children}
      </div>
    </CartProvider>
  );
}
