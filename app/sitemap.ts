import { SITE_URL } from '@/lib/brand';
import { MetadataRoute } from 'next';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

// Sitemap dibaca Google, bukan orang: no-store supaya nggak nyangkut hasil kosong
// dari waktu build. Backend udah nge-cache daftarnya 5 menit di Redis.
export const dynamic = 'force-dynamic';

type Listed = { slug: string; updated_at?: string | null };

async function getStorefronts(): Promise<Listed[]> {
  try {
    // Direktori publik (outlets.py:public_outlet_list, mig 105). Dulu 404 sejak
    // lahir, jadi nol toko yang pernah masuk sitemap.
    const res = await fetch(`${API_URL}/outlets/public/list`, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.data || []).filter((o: any) => o?.slug);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = SITE_URL;

  const staticPages: MetadataRoute.Sitemap = [
    { url: baseUrl, lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
    { url: `${baseUrl}/register`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.9 },
    { url: `${baseUrl}/pulsa-agen`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.85 },
    { url: `${baseUrl}/login`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.5 },
    { url: `${baseUrl}/download`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.7 },
    { url: `${baseUrl}/jelajah`, lastModified: new Date(), changeFrequency: 'daily', priority: 0.8 },
  ];

  // Halaman storefront. lastModified dari `updated_at` toko, BUKAN new Date():
  // sitemap yang nulis "semua berubah barusan" tiap kali diminta bikin Google
  // berhenti percaya tanggalnya.
  const outlets = await getStorefronts();
  const storefrontPages: MetadataRoute.Sitemap = outlets.map((o) => ({
    url: `${baseUrl}/${o.slug}`,
    lastModified: o.updated_at ? new Date(o.updated_at) : new Date(),
    changeFrequency: 'daily' as const,
    priority: 0.8,
  }));

  return [...staticPages, ...storefrontPages];
}
