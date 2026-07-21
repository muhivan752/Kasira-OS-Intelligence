import React from 'react';
import { cn } from '@/lib/utils';

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
 * Kasira "Aurora" brand mark — aurora-gradient rounded square with a
 * white equalizer / soundwave motif. Wordmark in Gabarito.
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
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
        aria-hidden="true"
      >
        {!mono && (
          <defs>
            <linearGradient id="kasira-mark" x1="6" y1="6" x2="42" y2="42" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#0E8F63" />
              <stop offset="1" stopColor="#0B7A55" />
            </linearGradient>
          </defs>
        )}
        {/* Struk dengan tepi bawah bergerigi. Menggantikan motif equalizer —
            equalizer itu bahasa visual audio (identitas Sefrekuensi), bukan kasir.
            Gerigi cuma 4 dan dalam, supaya tetap kebaca waktu ikon mengecil. */}
        <rect x="0" y="0" width="48" height="48" rx="11" fill={mono ? 'currentColor' : 'url(#kasira-mark)'} />
        <path
          d="M13.5 13a2.5 2.5 0 0 1 2.5-2.5h16a2.5 2.5 0 0 1 2.5 2.5v18l-2.625 6-2.625-6-2.625 6-2.625-6-2.625 6-2.625-6-2.625 6-2.625-6z"
          fill={mono ? 'var(--surface-card, #fff)' : '#fff'}
        />
        <rect x="18" y="16.5" width="12" height="3.1" rx="1.55" fill={mono ? 'currentColor' : '#0B7A55'} />
        <rect x="18" y="22.5" width="7.5" height="3.1" rx="1.55" fill={mono ? 'currentColor' : '#0B7A55'} />
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
          Kasira
        </div>
      )}
    </div>
  );
}
