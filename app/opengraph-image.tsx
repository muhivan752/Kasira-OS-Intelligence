import { ImageResponse } from 'next/og';

export const alt = 'Selaris — Kasir yang ngisi pembukuan kamu sendiri';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

/**
 * Gambar share (WA/IG/Twitter). Palet Aurora: kanvas neutral-50, tinta
 * neutral-900, gradien pink → ungu buat mark + satu aksen. Font system —
 * next/og nggak bisa muat Gabarito tanpa fetch, dan preview share nggak
 * butuh presisi tipografi.
 */
export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: 72,
          background: '#FCF7FB',
          fontFamily: 'system-ui, sans-serif',
          position: 'relative',
        }}
      >
        {/* glow atas ala hero */}
        <div
          style={{
            position: 'absolute',
            top: -200,
            left: 300,
            width: 600,
            height: 500,
            borderRadius: 9999,
            background: 'radial-gradient(circle, rgba(255,46,126,0.22) 0%, rgba(124,58,237,0.06) 55%, rgba(0,0,0,0) 80%)',
          }}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <svg width="56" height="56" viewBox="0 0 64 64">
            <defs>
      <linearGradient id="ga" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#8A16D6"/><stop offset="1" stopColor="#FF3D63"/></linearGradient>
      <linearGradient id="gb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#FF3D63"/><stop offset="1" stopColor="#8A16D6"/></linearGradient>
    </defs>
    <rect x="15.5" y="12" width="34" height="13.5" rx="6.75" transform="rotate(-32 32.5 18.75)" fill="url(#ga)"/>
    <rect x="15" y="37.25" width="34" height="13.5" rx="6.75" transform="rotate(-32 32 44)" fill="url(#gb)"/>
          </svg>
          <span style={{ fontSize: 44, fontWeight: 800, color: '#1C1426', letterSpacing: -1.5 }}>Selaris</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ fontSize: 64, fontWeight: 800, color: '#1C1426', lineHeight: 1.05, letterSpacing: -2, maxWidth: 980 }}>
            Kasir yang ngisi pembukuan kamu sendiri.
          </div>
          <div style={{ fontSize: 26, color: '#4C3E4F', maxWidth: 900, lineHeight: 1.4 }}>
            Transaksi, nota belanja, dan nomor WA pelanggan otomatis jadi stok, HPP, utang supplier, dan daftar pelanggan yang perlu disapa.
          </div>
        </div>

        <div style={{ display: 'flex', gap: 14 }}>
          {['Kasir offline', 'Foto nota → HPP', 'QRIS 0% komisi', 'Gratis 30 hari'].map((t) => (
            <div
              key={t}
              style={{
                display: 'flex',
                padding: '12px 22px',
                borderRadius: 999,
                background: '#FFFFFF',
                border: '1px solid #ECE0EA',
                fontSize: 20,
                fontWeight: 600,
                color: '#1C1426',
              }}
            >
              {t}
            </div>
          ))}
          <div
            style={{
              display: 'flex',
              padding: '12px 22px',
              borderRadius: 999,
              background: 'linear-gradient(120deg, #FF2E7E 0%, #7C3AED 100%)',
              fontSize: 20,
              fontWeight: 700,
              color: '#FFFFFF',
            }}
          >
            selaris.id
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
