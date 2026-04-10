import { ImageResponse } from 'next/og';

export const alt = 'Kasira — POS Digital untuk UMKM Indonesia';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: 'linear-gradient(135deg, #ecfdf5 0%, #ffffff 50%, #f0fdf4 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 64,
              height: 64,
              background: '#10b981',
              borderRadius: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: 36,
              fontWeight: 900,
            }}
          >
            K
          </div>
          <span style={{ fontSize: 48, fontWeight: 900, color: '#111827' }}>
            kasira
          </span>
          <span style={{ fontSize: 48, fontWeight: 900, color: '#10b981' }}>
            .
          </span>
        </div>
        <div
          style={{
            fontSize: 36,
            fontWeight: 800,
            color: '#111827',
            textAlign: 'center',
            maxWidth: 800,
            lineHeight: 1.3,
          }}
        >
          Kasir Digital yang Benar-Benar Simpel
        </div>
        <div
          style={{
            fontSize: 20,
            color: '#6b7280',
            marginTop: 16,
            textAlign: 'center',
            maxWidth: 600,
          }}
        >
          POS modern + storefront gratis + QRIS tanpa komisi untuk cafe dan UMKM Indonesia
        </div>
        <div
          style={{
            display: 'flex',
            gap: 32,
            marginTop: 40,
          }}
        >
          {['Setup 5 Menit', 'Zero Komisi', 'Offline Mode'].map((text) => (
            <div
              key={text}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: '#f0fdf4',
                padding: '10px 20px',
                borderRadius: 12,
                border: '1px solid #bbf7d0',
              }}
            >
              <span style={{ color: '#10b981', fontSize: 16 }}>&#10003;</span>
              <span style={{ fontSize: 16, fontWeight: 600, color: '#065f46' }}>{text}</span>
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size }
  );
}
