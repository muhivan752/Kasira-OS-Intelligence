import Link from 'next/link';
import { Logo } from '@/components/ui/logo';
import { COMPANY_EMAIL, COMPANY_NAME, WA_LINK } from '@/lib/brand';

export default function Footer() {
  return <footer className="public-footer public-container">
    <div><Link href="/" aria-label="Selaris, beranda"><Logo size="sm" variant="light" /></Link>
      <p>Kasir dan pengelolaan usaha.</p>
      <p>© {new Date().getFullYear()} {COMPANY_NAME}<br /><a href={`mailto:${COMPANY_EMAIL}`}>{COMPANY_EMAIL}</a></p></div>
    <nav aria-label="Tautan bantuan">
      <Link href="/download">Download aplikasi</Link>
      <a href={WA_LINK} target="_blank" rel="noopener noreferrer">Hubungi tim Selaris</a>
      <Link href="/terms">Syarat & ketentuan</Link>
      <Link href="/privacy">Kebijakan privasi</Link>
    </nav>
  </footer>;
}
