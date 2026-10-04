'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const sync = () => setDark(document.documentElement.classList.contains('dark'));
    sync();
    window.addEventListener('selaris-theme-change', sync);
    return () => window.removeEventListener('selaris-theme-change', sync);
  }, []);
  function toggle() {
    const next = !dark;
    document.documentElement.classList.toggle('dark', next);
    try { localStorage.setItem('selaris-theme', next ? 'dark' : 'light'); } catch {}
    window.dispatchEvent(new Event('selaris-theme-change'));
  }
  return <button className="auth-theme" onClick={toggle} type="button"
    aria-label={dark ? 'Gunakan tema terang' : 'Gunakan tema gelap'} aria-pressed={dark}>
    {dark ? <Sun size={20} /> : <Moon size={20} />}
  </button>;
}
