'use client';

import { Loader2, Smartphone, Download, MessageCircle } from 'lucide-react';
import { SEFREKUENSI_NAME, SEFREKUENSI_PLAY_URL } from '@/lib/brand';

/**
 * Iklan halus Sefrekuensi di layar masuk & daftar (keputusan Ivan 4 Sep).
 *
 * Dua wujud, satu komponen:
 * - Biasa: tawaran "kirim kode lewat Sefrekuensi". Yang punya dapat kode
 *   tanpa WhatsApp, yang belum cuma lihat mereknya. WhatsApp tetap tombol
 *   utama di luar kartu ini supaya orang baru nggak kepaksa pasang app kedua.
 * - notFound: server bilang nomornya belum ada di Sefrekuensi. Jangan buntu:
 *   tawarkan Pasang (Play Store) atau kirim lewat WhatsApp saja.
 */
export function SefrekuensiOtpCard({
  loading,
  notFound,
  onPick,
  onFallbackWhatsapp,
}: {
  loading: boolean;
  notFound: boolean;
  onPick: () => void;
  onFallbackWhatsapp: () => void;
}) {
  return (
    <div
      className="rounded-[var(--radius-lg)] p-4"
      style={{
        background: 'var(--brand-tint)',
        border: '1px solid color-mix(in srgb, var(--brand-secondary) 28%, transparent)',
      }}
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full"
          style={{ background: 'color-mix(in srgb, var(--brand-secondary) 16%, transparent)', color: 'var(--brand-secondary)' }}
        >
          <Smartphone className="h-[18px] w-[18px]" />
        </span>
        <div className="min-w-0 flex-1">
          {notFound ? (
            <>
              <p className="text-sm font-semibold text-[var(--text-strong)]">Nomor ini belum ada di {SEFREKUENSI_NAME}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-muted)]">
                Pasang {SEFREKUENSI_NAME} dengan nomor yang sama, lalu coba lagi. Atau kirim kodenya lewat WhatsApp saja.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a
                  href={SEFREKUENSI_PLAY_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-semibold text-white"
                  style={{ background: 'var(--brand-secondary)' }}
                >
                  <Download className="h-3.5 w-3.5" /> Pasang {SEFREKUENSI_NAME}
                </a>
                <button
                  type="button"
                  onClick={onFallbackWhatsapp}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs font-semibold text-[var(--text-body)] disabled:opacity-60"
                  style={{ borderColor: 'var(--border-default)', background: 'var(--surface-card)' }}
                >
                  <MessageCircle className="h-3.5 w-3.5" /> Kirim lewat WhatsApp saja
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm font-semibold text-[var(--text-strong)]">Untuk pengalaman yang lebih baik</p>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-muted)]">
                Punya {SEFREKUENSI_NAME}? Kode masuk datang sebagai pesan di sana, tanpa lewat WhatsApp.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
                <button
                  type="button"
                  onClick={onPick}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-semibold text-white disabled:opacity-60"
                  style={{ background: 'var(--brand-secondary)' }}
                >
                  {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Smartphone className="h-3.5 w-3.5" />}
                  Kirim kode ke {SEFREKUENSI_NAME}
                </button>
                <a
                  href={SEFREKUENSI_PLAY_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-[var(--text-muted)] underline-offset-2 hover:underline"
                >
                  Belum punya? Pasang di Play Store
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
