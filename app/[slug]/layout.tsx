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
      alternates: { canonical: `${SITE_URL}/${slug}` },
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

/**
 * JSON-LD LocalBusiness (toko bisa ditemukan, 4 Sep 2026). Google baru mau
 * nampilin kartu toko + tombol "Pesan" kalau ada data terstruktur; tanpa ini
 * halaman toko cuma teks biasa buat mesin pencari. Jenis dari brands.type.
 */
const DAY_SCHEMA: Record<string, string> = { mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday', fri: 'Friday', sat: 'Saturday', sun: 'Sunday' };
function hoursSpec(h: Record<string, [string, string][]>) {
  const out: any[] = [];
  for (const d of Object.keys(DAY_SCHEMA)) for (const [opens, closes] of (h[d] || [])) out.push({ '@type': 'OpeningHoursSpecification', dayOfWeek: DAY_SCHEMA[d], opens, closes });
  return out;
}

function businessJsonLd(slug: string, o: any) {
  const typeMap: Record<string, string> = { cafe: 'CafeOrCoffeeShop', resto: 'Restaurant', warung: 'Restaurant', other: 'Store' };
  const url = `${SITE_URL}/${slug}`;
  const wa = (o?.whatsapp || '').replace(/\D/g, '');
  const data: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': typeMap[o?.business_type] || 'Store',
    name: o?.name,
    url,
    '@id': url,
    ...(o?.cover_image_url ? { image: o.cover_image_url } : {}),
    ...(wa ? { telephone: `+${wa}` } : {}),
    ...(o?.address ? {
      address: {
        '@type': 'PostalAddress',
        streetAddress: o.address,
        ...(o?.city ? { addressLocality: o.city } : {}),
        ...(o?.province ? { addressRegion: o.province } : {}),
        addressCountry: 'ID',
      },
    } : {}),
    ...(o?.latitude && o?.longitude ? { geo: { '@type': 'GeoCoordinates', latitude: o.latitude, longitude: o.longitude } } : {}),
    ...(o?.business_hours && o?.hours_mode === 'schedule'
      ? { openingHoursSpecification: hoursSpec(o.business_hours) }
      : o?.opening_hours ? { openingHours: o.opening_hours } : {}),
    hasMenu: url,
    acceptsReservations: o?.reservation_enabled ? 'True' : 'False',
    potentialAction: {
      '@type': 'OrderAction',
      target: { '@type': 'EntryPoint', urlTemplate: url, actionPlatform: ['http://schema.org/MobileWebPlatform', 'http://schema.org/DesktopWebPlatform'] },
      deliveryMethod: ['http://purl.org/goodrelations/v1#DeliveryModePickUp'],
    },
    priceRange: 'Rp',
  };
  return data;
}

export default async function StorefrontLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let jsonLd: Record<string, any> | null = null;
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}`, { cache: 'no-store' });
    if (res.ok) {
      const { data } = await res.json();
      if (data?.outlet?.name) jsonLd = businessJsonLd(slug, data.outlet);
    }
  } catch {}

  return (
    <CartProvider slug={slug}>
      {jsonLd && (
        <script
          type="application/ld+json"
          // JSON.stringify + escape "<" supaya nggak bisa nutup tag script dari nama toko.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
        />
      )}
      <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-body)]">
        {children}
      </div>
    </CartProvider>
  );
}
