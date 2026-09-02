import { SITE_URL } from '@/lib/brand';
import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/dashboard/', '/api/', '/onboarding/', '/superadmin/'],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
