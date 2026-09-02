import React from 'react';
import { cn } from '@/lib/utils';
import { BRAND } from '@/lib/brand';

interface LogoProps {
  className?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /**
   * dark   → wordmark light (use on dark backgrounds)
   * light  → wordmark dark  (use on light backgrounds)
   * brand  → gradient wordmark (aurora), mark stays gradient
   * mono   → single-color mark + wordmark (inherits currentColor)
   */
  variant?: 'dark' | 'light' | 'brand' | 'mono';
  showWordmark?: boolean;
}

/**
 * Selaris brand mark — dua pil miring bergradien pink → ungu (logo Selaris
 * milik Ivan, sama dengan favicon selaris.id), wordmark Gabarito.
 *
 * Mark lama (kotak hijau bermotif struk) dibuang bareng rebrand 2026-09-02.
 * Gradien pakai token Aurora (pink-500 → violet-500) biar satu palet dengan
 * app POS dan dashboard, bukan hex terpisah.
 */
export function Logo({
  className,
  size = 'md',
  variant = 'dark',
  showWordmark = true,
}: LogoProps) {
  const sizeMap = {
    xs: { svg: 18, gap: 'gap-[6px]', text: 'text-[15px]' },
    sm: { svg: 24, gap: 'gap-[8px]', text: 'text-[19px]' },
    md: { svg: 34, gap: 'gap-[10px]', text: 'text-[27px]' },
    lg: { svg: 50, gap: 'gap-[13px]', text: 'text-[40px]' },
    xl: { svg: 66, gap: 'gap-[18px]', text: 'text-[54px]' },
  };
  const s = sizeMap[size];

  let textColor = 'text-[var(--text-strong)]';
  if (variant === 'dark') textColor = 'text-[var(--text-inverse)]';
  else if (variant === 'light') textColor = 'text-[var(--text-strong)]';
  else if (variant === 'mono') textColor = '';

  const mono = variant === 'mono';
  
  return (
    <div className={cn('flex items-center select-none', s.gap, className)}>
      <svg
        width={s.svg}
        height={s.svg}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
        aria-hidden="true"
      >
        {!mono && (
          <defs>
            <linearGradient id="selaris-a" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#8A16D6" /><stop offset="1" stopColor="#FF3D63" /></linearGradient>
            <linearGradient id="selaris-b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#FF3D63" /><stop offset="1" stopColor="#8A16D6" /></linearGradient>
          </defs>
        )}
        {/* Logo resmi Selaris (file dari Ivan, 2 Sep): dua pil naik ke kanan,
            pil atas ungu→pink, pil bawah pink→ungu. Palet #FF3D63 / #8A16D6. */}
        <rect x="15.5" y="12" width="34" height="13.5" rx="6.75" transform="rotate(-32 32.5 18.75)" fill={mono ? 'currentColor' : 'url(#selaris-a)'} />
        <rect x="15" y="37.25" width="34" height="13.5" rx="6.75" transform="rotate(-32 32 44)" fill={mono ? 'currentColor' : 'url(#selaris-b)'} />
      </svg>
      {showWordmark && (
        <div
          className={cn(
            'font-[family-name:var(--font-gabarito)] font-extrabold leading-none tracking-[-0.03em]',
            variant === 'brand' && 'ks-gradient-text',
            textColor,
            s.text
          )}
        >
          {BRAND}
        </div>
      )}
    </div>
  );
}
