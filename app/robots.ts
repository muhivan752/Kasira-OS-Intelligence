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
    sitemap: 'https://kasira.online/sitemap.xml',
  };
}
