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
      <linearGradient id="ga" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#8A16D6"/><stop offset="1" stopColor="#FF3D63"/></linearGradient>
      <linearGradient id="gb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#FF3D63"/><stop offset="1" stopColor="#8A16D6"/></linearGradient>
    </defs>
    <rect x="15" y="14" width="42" height="18" rx="9" transform="rotate(-30 36 23)" fill="url(#ga)"/>
    <rect x="7" y="32" width="42" height="18" rx="9" transform="rotate(-30 28 41)" fill="url(#gb)"/>
        </svg>
      </div>
    ),
    { ...size }
  );
}
