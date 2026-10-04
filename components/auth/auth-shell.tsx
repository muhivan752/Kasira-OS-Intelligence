'use client';

import Link from 'next/link';
import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/ui/theme-toggle';

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="auth-layout">
      <header className="auth-topbar">
        <Link href="/" aria-label="Beranda Selaris"><Logo size="sm" variant="mono" /></Link>
        <ThemeToggle />
      </header>
      <section className="auth-content">{children}</section>
      <footer className="auth-footer"><Link href="/terms">Ketentuan layanan</Link><span>dan</span><Link href="/privacy">Kebijakan privasi</Link></footer>
    </main>
  );
}
