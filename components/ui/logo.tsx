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
  const fill = mono ? 'currentColor' : 'url(#selaris-mark)';

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
            <linearGradient id="selaris-mark" x1="0" y1="64" x2="64" y2="0" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="var(--violet-500, #7C3AED)" />
              <stop offset="1" stopColor="var(--pink-500, #FF2E7E)" />
            </linearGradient>
          </defs>
        )}
        <rect x="16" y="4" width="46" height="23" rx="11.5" transform="rotate(28 39 15.5)" fill={fill} />
        <rect x="2" y="37" width="46" height="23" rx="11.5" transform="rotate(28 25 48.5)" fill={fill} />
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
