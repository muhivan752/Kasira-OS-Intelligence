/**
 * Identitas produk — SATU sumber. Semua halaman web baca dari sini.
 *
 * Rebrand Kasira → Selaris (2 Sep 2026). Domain lama kasira.online SENGAJA
 * tetap dilayani: APK yang udah terpasang hardcode base URL lama, dan webhook
 * Xendit tiap tenant (BYOK) didaftarin ke kasira.online/api/v1/... — dua-duanya
 * gak boleh putus. Jadi yang berubah cuma nama + URL kanonik yang ditampilin;
 * API jalan di dua domain.
 *
 * NEXT_PUBLIC_SITE_URL di .env nentuin URL yang DITAMPILIN (struk, share link,
 * sitemap). Sebelum DNS selaris.id nunjuk ke server ini, env tetap
 * kasira.online — jangan diflip duluan atau link di WA pelanggan mati.
 */
export const BRAND = 'Selaris';
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || 'https://selaris.id').replace(/\/$/, '');
export const SITE_HOST = SITE_URL.replace(/^https?:\/\//, '');
export const WA_NUMBER = '6285270782220';
export const WA_LINK = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(`Halo ${BRAND}, saya tertarik coba`)}`;
export const DEMO_SLUG = 'kasira-coffee';
