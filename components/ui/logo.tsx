import React from 'react';
import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'dark' | 'light' | 'brand' | 'outline';
  showWordmark?: boolean;
}

export function Logo({
  className,
  size = 'md',
  variant = 'dark',
  showWordmark = true,
}: LogoProps) {
  // Size mappings
  const sizeMap = {
    xs: { svg: 16, gap: 'gap-[5px]', text: 'text-[14px]', stroke: 3.5 },
    sm: { svg: 22, gap: 'gap-[7px]', text: 'text-[18px]', stroke: 3.5 },
    md: { svg: 32, gap: 'gap-[10px]', text: 'text-[26px]', stroke: 3.5 },
    lg: { svg: 48, gap: 'gap-[13px]', text: 'text-[38px]', stroke: 3.5 },
    xl: { svg: 64, gap: 'gap-[18px]', text: 'text-[52px]', stroke: 3.5 },
  };

  const s = sizeMap[size];

  // Variant mappings
  let iconBg = '#FF5C00';
  let iconStroke = 'white';
  let textColor = 'text-[#F5F0E8]'; // default dark variant (on dark bg)
  let iconOutline = 'none';

  if (variant === 'light') {
    textColor = 'text-[#0D0B07]';
  } else if (variant === 'brand') {
    iconBg = 'rgba(0,0,0,0.15)';
    textColor = 'text-black';
  } else if (variant === 'outline') {
    iconBg = 'transparent';
    iconStroke = '#FF5C00';
    iconOutline = '#FF5C00';
    textColor = 'text-[#0D0B07]'; // assuming outline is usually on light bg
  }

  return (
    <div className={cn('flex items-center select-none', s.gap, className)}>
      <div className="shrink-0 relative flex items-center justify-center">
        <svg
          width={s.svg}
          height={s.svg}
          viewBox="0 0 44 44"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect
            width="44"
            height="44"
            rx="11"
            fill={iconBg}
            stroke={iconOutline !== 'none' ? iconOutline : undefined}
            strokeWidth={iconOutline !== 'none' ? 1.5 : undefined}
          />
          <path
            d="M13.5 11.5 L13.5 32.5"
            stroke={iconStroke}
            strokeWidth={s.stroke}
            strokeLinecap="round"
          />
          <path
            d="M13.5 22 L27.5 11.5"
            stroke={iconStroke}
            strokeWidth={s.stroke}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M13.5 22 L27.5 32.5"
            stroke={iconStroke}
            strokeWidth={s.stroke}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      {showWordmark && (
        <div
          className={cn(
            'font-syne font-black leading-none tracking-[-0.03em]',
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
