import { ImageResponse } from 'next/og';

export const size = { width: 32, height: 32 };
export const contentType = 'image/png';

/**
 * Tanda Kasira: struk dengan tepi bawah bergerigi.
 * Gerigi sengaja cuma 4 dan dibikin dalam — versi 6 gigi yang dangkal hilang
 * jadi garis samar begitu ikonnya mengecil ke 16px.
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          background: '#0B7A55',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 7,
        }}
      >
        <svg width="24" height="24" viewBox="0 0 48 48">
          <path
            d="M13.5 13a2.5 2.5 0 0 1 2.5-2.5h16a2.5 2.5 0 0 1 2.5 2.5v18l-2.625 6-2.625-6-2.625 6-2.625-6-2.625 6-2.625-6-2.625 6-2.625-6z"
            fill="#fff"
          />
          <rect x="18" y="16.5" width="12" height="3.1" rx="1.55" fill="#0B7A55" />
          <rect x="18" y="22.5" width="7.5" height="3.1" rx="1.55" fill="#0B7A55" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
