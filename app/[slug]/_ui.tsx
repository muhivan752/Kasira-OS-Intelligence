'use client';

/**
 * Bahan bersama storefront (halaman menu, checkout, lacak pesanan).
 *
 * Satu bahasa untuk pelanggan dan toko: label status di sini SAMA dengan
 * teks WA yang dikirim backend (services/online_orders.py) dan badge di
 * app kasir. Kalau ubah kata di satu tempat, ubah di tiga tempat.
 */

import Link from 'next/link';
import { useEffect, type ReactNode } from 'react';
import { Logo } from '@/components/ui/logo';

export const rp = (n: number | string | null | undefined) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(Number(n) || 0);

export const timeShort = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) : '';

export const ORDER_TYPE_LABEL: Record<string, string> = {
  pickup: 'Ambil sendiri',
  takeaway: 'Ambil sendiri',
  delivery: 'Antar ke alamat',
  dine_in: 'Makan di tempat',
};

/** Nomor WA yang diterbitkan toko, dinormalkan ke 62xxx. Null = toko belum mengisi. */
export function waNumber(raw?: string | null): string | null {
  if (!raw) return null;
  const digits = String(raw).replace(/\D/g, '');
  if (!digits || digits.includes('*')) return null;
  return digits.startsWith('0') ? '62' + digits.slice(1) : digits;
}

export function waLink(num: string, text: string) {
  return `https://wa.me/${num}?text=${encodeURIComponent(text)}`;
}

/* ── Penyimpanan ringan di browser pelanggan ─────────────────────────── */

export type SavedCustomer = { name: string; phone: string };
const customerKey = 'selaris_customer';
const lastOrderKey = (slug: string) => `selaris_last_order_${slug}`;

export function loadCustomer(): SavedCustomer | null {
  try { const v = localStorage.getItem(customerKey); return v ? JSON.parse(v) : null; } catch { return null; }
}
export function saveCustomer(c: SavedCustomer) {
  try { localStorage.setItem(customerKey, JSON.stringify(c)); } catch { /* abaikan */ }
}
export function saveLastOrder(slug: string, id: string, displayNumber: number) {
  try { localStorage.setItem(lastOrderKey(slug), JSON.stringify({ id, displayNumber, at: Date.now() })); } catch { /* abaikan */ }
}
export function loadLastOrder(slug: string): { id: string; displayNumber: number; at: number } | null {
  try {
    const v = localStorage.getItem(lastOrderKey(slug));
    if (!v) return null;
    const o = JSON.parse(v);
    // Cuma tampil 12 jam: pesanan kemarin bukan lagi "pesanan terakhir".
    return Date.now() - o.at < 12 * 3600 * 1000 ? o : null;
  } catch { return null; }
}

/* ── Potongan tampilan ───────────────────────────────────────────────── */

export function StoreAvatar({ name, size = 44 }: { name: string; size?: number }) {
  const initials = name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('');
  return (
    <div
      className="shrink-0 rounded-2xl flex items-center justify-center text-white font-display font-extrabold"
      style={{ width: size, height: size, background: 'var(--gradient-aurora)', fontSize: size * 0.38 }}
      aria-hidden
    >
      {initials || 'S'}
    </div>
  );
}

export function StatusPill({ tone, children }: { tone: 'open' | 'closed' | 'muted'; children: ReactNode }) {
  const cls = {
    open: 'bg-[color-mix(in_srgb,var(--success)_14%,white)] text-[var(--success)]',
    closed: 'bg-[color-mix(in_srgb,var(--danger)_12%,white)] text-[var(--danger)]',
    muted: 'bg-[var(--surface-sunken)] text-[var(--text-muted)]',
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-[var(--radius-xl)] shadow-[var(--shadow-xs)] ${className}`}>
      {children}
    </section>
  );
}

export function SectionTitle({ step, title, hint }: { step?: number; title: string; hint?: string }) {
  return (
    <div className="flex items-start gap-3 mb-4">
      {step !== undefined && (
        <span className="w-7 h-7 rounded-full bg-[var(--surface-inverse)] text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
          {step}
        </span>
      )}
      <div>
        <h2 className="font-display font-extrabold text-[17px] text-[var(--text-strong)] tracking-tight">{title}</h2>
        {hint && <p className="text-sm text-[var(--text-muted)] mt-0.5">{hint}</p>}
      </div>
    </div>
  );
}

export const btnPrimary =
  'inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--surface-inverse)] text-white font-semibold px-5 py-3.5 transition hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed';
export const btnSecondary =
  'inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--surface-card)] border border-[var(--border-default)] text-[var(--text-strong)] font-semibold px-5 py-3.5 transition hover:bg-[var(--bg-subtle)] disabled:opacity-40';
export const inputCls =
  'w-full px-4 py-3.5 bg-[var(--bg-subtle)] border border-transparent rounded-2xl text-[15px] text-[var(--text-strong)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--focus-ring)] focus:bg-white transition';

export function Stepper({ qty, onDec, onInc, dark = false }: { qty: number; onDec: () => void; onInc: () => void; dark?: boolean }) {
  const btn = dark
    ? 'w-8 h-8 rounded-full bg-white/15 text-white hover:bg-white/25'
    : 'w-8 h-8 rounded-full bg-[var(--surface-card)] text-[var(--text-strong)] shadow-[var(--shadow-xs)] hover:bg-[var(--bg-subtle)]';
  return (
    <div className={`inline-flex items-center gap-1 rounded-full p-1 ${dark ? 'bg-white/10' : 'bg-[var(--bg-subtle)]'}`}>
      <button type="button" onClick={onDec} aria-label="Kurangi" className={`${btn} flex items-center justify-center text-lg leading-none`}>−</button>
      <span className={`w-7 text-center text-sm font-bold ${dark ? 'text-white' : 'text-[var(--text-strong)]'}`}>{qty}</span>
      <button type="button" onClick={onInc} aria-label="Tambah" className={`${btn} flex items-center justify-center text-lg leading-none`}>+</button>
    </div>
  );
}

/** Lembar bawah (mobile) atau dialog tengah (desktop). Tutup lewat latar atau Escape. */
export function Sheet({ open, onClose, children, title }: { open: boolean; onClose: () => void; children: ReactNode; title?: string }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-[2px] p-0 sm:p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal
        className="w-full sm:max-w-md bg-[var(--surface-card)] rounded-t-[28px] sm:rounded-[28px] p-5 pb-8 sm:pb-5 max-h-[85vh] overflow-y-auto shadow-[var(--shadow-xl)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-[var(--border-default)] sm:hidden" />
        {title && <h3 className="font-display font-extrabold text-lg text-[var(--text-strong)] mb-3">{title}</h3>}
        {children}
      </div>
    </div>
  );
}

export function PoweredBy({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-col items-center gap-1.5 py-8 ${className}`}>
      <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">Pemesanan online oleh</p>
      <Link href="/" className="opacity-80 hover:opacity-100 transition"><Logo size="xs" variant="light" /></Link>
      <p className="text-[11px] text-[var(--text-muted)]">Tanpa komisi untuk toko</p>
    </div>
  );
}

export function TopBar({ back, title, right }: { back?: string; title: ReactNode; right?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 bg-[color-mix(in_srgb,var(--bg-base)_88%,transparent)] backdrop-blur-md border-b border-[var(--border-subtle)]">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
        {back && (
          <Link href={back} aria-label="Kembali" className="w-9 h-9 -ml-1 rounded-full flex items-center justify-center text-[var(--text-strong)] hover:bg-[var(--bg-subtle)]">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
          </Link>
        )}
        <div className="flex-1 min-w-0">{title}</div>
        {right}
      </div>
    </header>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center px-6">
      <div className="w-16 h-16 rounded-3xl bg-[var(--bg-subtle)] flex items-center justify-center mb-5">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="text-[var(--text-muted)]"><path d="M6 6h15l-1.5 9h-12z" /><path d="M6 6L5 3H2" /><circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" /></svg>
      </div>
      <h1 className="font-display font-extrabold text-2xl text-[var(--text-strong)] mb-2">{title}</h1>
      <p className="text-[var(--text-muted)] max-w-sm">{body}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
      <div className="w-9 h-9 rounded-full border-[3px] border-[var(--border-default)] border-t-[var(--text-strong)] animate-spin" />
      {label && <p className="text-sm text-[var(--text-muted)]">{label}</p>}
    </div>
  );
}
