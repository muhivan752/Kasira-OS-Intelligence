import type { Metadata } from 'next';
import Link from 'next/link';
import { MapPin, ArrowRight, Store, Coffee, Utensils } from 'lucide-react';
import Navbar from '@/components/landing/Navbar';
import { Logo } from '@/components/ui/logo';
import { BRAND, SITE_URL } from '@/lib/brand';

/**
 * Direktori toko publik (toko bisa ditemukan, 4 Sep 2026).
 *
 * Sumbernya endpoint yang sama dengan sitemap: GET /outlets/public/list
 * (outlet aktif, pemilik mengizinkan lewat outlets.directory_listed, punya
 * produk). Halaman ini yang bikin toko punya "tetangga" di mata Google:
 * satu halaman yang nautin ke semua toko, bukan cuma link yang disebar
 * pemilik lewat WA.
 */
// force-dynamic, bukan ISR: waktu `next build` backend nggak kejangkau, dan hasil
// kosong bakal nyangkut sampai revalidate. Cache-nya udah di Redis (5 menit).
export const dynamic = 'force-dynamic';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

type Listed = {
  slug: string;
  name: string;
  city?: string | null;
  province?: string | null;
  address?: string | null;
  cover_image_url?: string | null;
  business_type?: string;
  is_open: boolean;
  accepting_orders: boolean;
  product_count: number;
};

export const metadata: Metadata = {
  // Template layout udah nambahin "| Selaris", jadi judulnya jangan bawa merek lagi.
  title: 'Jelajah Toko',
  description: `Cari kafe, warung, dan toko di dekatmu yang menerima pesanan online lewat ${BRAND}. Pesan dari HP, dikonfirmasi toko, tanpa aplikasi tambahan.`,
  alternates: { canonical: `${SITE_URL}/jelajah` },
  openGraph: { title: `Jelajah Toko · ${BRAND}`, url: `${SITE_URL}/jelajah` },
};

async function getListed(): Promise<Listed[]> {
  try {
    const res = await fetch(`${API_URL}/outlets/public/list`, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.data || []) as Listed[];
  } catch {
    return [];
  }
}

const TYPE_LABEL: Record<string, string> = { cafe: 'Kafe', resto: 'Restoran', warung: 'Warung makan', other: 'Toko' };

function TypeIcon({ type }: { type?: string }) {
  const cls = 'h-4 w-4';
  if (type === 'cafe') return <Coffee className={cls} />;
  if (type === 'resto' || type === 'warung') return <Utensils className={cls} />;
  return <Store className={cls} />;
}

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
}

export default async function JelajahPage() {
  const listed = await getListed();

  // Kelompokkan per kota. Yang belum isi kota masuk "Kota lainnya" di bawah.
  const byCity = new Map<string, Listed[]>();
  for (const o of listed) {
    const key = (o.city || '').trim() || 'Kota lainnya';
    byCity.set(key, [...(byCity.get(key) || []), o]);
  }
  const cities = [...byCity.keys()].sort((a, b) => (a === 'Kota lainnya' ? 1 : b === 'Kota lainnya' ? -1 : a.localeCompare(b)));

  const itemListLd = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: `Toko yang menerima pesanan online lewat ${BRAND}`,
    itemListElement: listed.map((o, i) => ({ '@type': 'ListItem', position: i + 1, url: `${SITE_URL}/${o.slug}`, name: o.name })),
  };

  return (
    <main className="min-h-screen bg-[var(--bg-base)] text-[var(--text-body)]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListLd).replace(/</g, '\\u003c') }} />
      <Navbar />

      <section className="relative overflow-hidden px-4 pt-28 pb-10 sm:pt-32">
        <div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: 'var(--gradient-glow)' }} />
        <div className="relative mx-auto max-w-5xl">
          <p className="ks-eyebrow">Jelajah</p>
          <h1 className="ks-display mt-2 text-[34px] font-extrabold leading-tight text-[var(--text-strong)] sm:text-[48px]">
            Toko di dekatmu yang bisa dipesan dari HP
          </h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[var(--text-muted)]">
            Semua toko di sini memakai {BRAND}. Pesan langsung dari halaman toko, dikonfirmasi pemiliknya, statusnya bisa dilacak. Tanpa aplikasi tambahan, tanpa komisi buat toko.
          </p>
        </div>
      </section>

      <section className="px-4 pb-24">
        <div className="mx-auto max-w-5xl space-y-12">
          {listed.length === 0 && (
            <div className="ks-card p-10 text-center">
              <p className="text-[var(--text-muted)]">Belum ada toko yang tampil. Coba lagi sebentar lagi.</p>
            </div>
          )}

          {cities.map(city => (
            <div key={city}>
              <div className="mb-4 flex items-center gap-2">
                <MapPin className="h-4 w-4 text-[var(--brand-secondary)]" />
                <h2 className="ks-display text-xl font-extrabold text-[var(--text-strong)]">{city}</h2>
                <span className="text-sm text-[var(--text-muted)]">· {byCity.get(city)!.length} toko</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {byCity.get(city)!.map(o => (
                  <Link key={o.slug} href={`/${o.slug}`} className="ks-card group overflow-hidden p-0 transition-transform hover:-translate-y-0.5">
                    <div className="relative h-32 w-full overflow-hidden bg-[var(--brand-tint)]">
                      {o.cover_image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={o.cover_image_url} alt={o.name} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center">
                          <span className="ks-display text-3xl font-extrabold text-[var(--brand-secondary)]">{initials(o.name)}</span>
                        </div>
                      )}
                      <span
                        className="absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-semibold"
                        style={{
                          background: o.accepting_orders ? 'color-mix(in srgb, var(--success) 18%, white)' : 'color-mix(in srgb, var(--text-muted) 18%, white)',
                          color: o.accepting_orders ? 'var(--success)' : 'var(--text-muted)',
                        }}
                      >
                        {o.accepting_orders ? 'Buka, terima pesanan' : o.is_open ? 'Buka' : 'Tutup'}
                      </span>
                    </div>
                    <div className="p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-[var(--text-strong)]">{o.name}</p>
                          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
                            <TypeIcon type={o.business_type} />
                            {TYPE_LABEL[o.business_type || 'other'] || 'Toko'} · {o.product_count} menu
                          </p>
                        </div>
                        <ArrowRight className="mt-1 h-4 w-4 flex-shrink-0 text-[var(--text-muted)] transition-transform group-hover:translate-x-0.5" />
                      </div>
                      {o.address && <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-[var(--text-muted)]">{o.address}</p>}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}

          <div className="ks-card flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="ks-display text-lg font-extrabold text-[var(--text-strong)]">Punya usaha? Tokomu bisa tampil di sini.</p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">Daftar gratis, halaman toko langsung jadi, dan masuk daftar ini begitu menunya terisi.</p>
            </div>
            <Link href="/register" className="ks-btn whitespace-nowrap">Daftar {BRAND} <ArrowRight className="h-4 w-4" /></Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[var(--border-subtle)] px-4 py-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between text-xs text-[var(--text-muted)]">
          <Logo size="sm" variant="brand" />
          <span>© {new Date().getFullYear()} {BRAND}</span>
        </div>
      </footer>
    </main>
  );
}
