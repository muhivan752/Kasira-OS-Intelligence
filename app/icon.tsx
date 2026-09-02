import { ImageResponse } from 'next/og';

export const size = { width: 32, height: 32 };
export const contentType = 'image/png';

/**
 * Favicon Selaris: dua pil miring bergradien pink → ungu (logo Selaris,
 * sama dengan components/ui/logo.tsx dan public/favicon.svg). Di 16px dua
 * pilnya masih kebaca sebagai bentuk "S" miring — makanya mark-nya cuma
 * dua elemen, tanpa detail kecil.
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'transparent',
        }}
      >
        <svg width="32" height="32" viewBox="0 0 64 64">
          <defs>
            <linearGradient id="g" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0" stopColor="#7C3AED" />
              <stop offset="1" stopColor="#FF2E7E" />
            </linearGradient>
          </defs>
          <rect x="16" y="4" width="46" height="23" rx="11.5" transform="rotate(28 39 15.5)" fill="url(#g)" />
          <rect x="2" y="37" width="46" height="23" rx="11.5" transform="rotate(28 25 48.5)" fill="url(#g)" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
