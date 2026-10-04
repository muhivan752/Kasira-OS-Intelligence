'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';
import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/ui/theme-toggle';

const links = [
  { name: 'Cara kerja', href: '/#cara-kerja' },
  { name: 'Tampilan', href: '/#tampilan' },
  { name: 'Modul', href: '/#modul' },
  { name: 'Harga', href: '/#harga' },
  { name: 'Jelajah toko', href: '/jelajah' },
  { name: 'Download', href: '/download' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    menu.current?.querySelector<HTMLAnchorElement>('a')?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        trigger.current?.focus();
      }
    };
    const resize = () => { if (window.innerWidth >= 1024) setOpen(false); };
    window.addEventListener('keydown', close);
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('keydown', close);
      window.removeEventListener('resize', resize);
    };
  }, [open]);

  return <header className="public-nav">
    <nav aria-label="Navigasi utama" className="public-container">
      <div className="public-nav-row">
        <Link href="/" aria-label="Selaris, beranda" className="public-brand"><Logo size="md" variant="light" /></Link>
        <div className="hidden lg:flex items-center gap-1">
          {links.map(link => <Link className="public-nav-link" href={link.href} key={link.name}>{link.name}</Link>)}
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link className="public-nav-link hidden sm:inline-flex" href="/login">Masuk</Link>
          <button ref={trigger} type="button" aria-label={open ? 'Tutup menu' : 'Buka menu'}
            aria-expanded={open} aria-controls="public-menu" onClick={() => setOpen(!open)}
            className="public-menu-trigger lg:hidden">{open ? <X size={22} /> : <Menu size={22} />}</button>
        </div>
      </div>
      {open && <div ref={menu} id="public-menu" className="public-menu lg:hidden">
        {links.map(link => <Link href={link.href} key={link.name} onClick={() => setOpen(false)}>{link.name}</Link>)}
        <Link href="/login" onClick={() => setOpen(false)}>Masuk ke akun</Link>
        <Link href="/register" onClick={() => setOpen(false)}>Daftarkan usaha</Link>
      </div>}
    </nav>
  </header>;
}
