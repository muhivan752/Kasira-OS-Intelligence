'use client';

import { useEffect, useState } from 'react';
import { Smartphone, BellRing, CircleCheck, Download } from 'lucide-react';
import { getSefrekuensiStatus } from '@/app/actions/api';
import { SEFREKUENSI_NAME } from '@/lib/brand';

/**
 * Kartu Beranda (langkah 3 jembatan, 4 Sep 2026). Dua wujud dari satu status:
 * - belum punya: ajakan pasang, alasannya konkret (kabar pesanan masuk walau
 *   app kasir ditutup, tanpa bergantung WhatsApp).
 * - sudah punya: badge terhubung, plus catatan kalau push belum aktif.
 * Status dicek server ke server (cache 1 jam), pemilik nggak ditanya apa apa.
 * `enabled` false = fitur mati di server, kartu nggak dirender.
 */
export function SefrekuensiCard({ outletId }: { outletId?: string }) {
  const [st, setSt] = useState<Awaited<ReturnType<typeof getSefrekuensiStatus>>>(null);

  useEffect(() => {
    if (!outletId) return;
    getSefrekuensiStatus(outletId).then(setSt).catch(() => {});
  }, [outletId]);

  if (!st || !st.enabled) return null;

  if (st.connected) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] bg-white p-4 shadow-sm">
        <span className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full" style={{ background: 'color-mix(in srgb, var(--success) 14%, white)', color: 'var(--success)' }}>
          <CircleCheck className="h-[18px] w-[18px]" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-900">Terhubung ke {SEFREKUENSI_NAME}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-gray-500">
            Kabar pesanan online, reservasi, dan bukti bayar dikirim ke {SEFREKUENSI_NAME} di nomor {st.phone_masked || 'toko'}, walau app kasir ditutup.
            {!st.push && ` Notifikasi belum aktif: buka ${SEFREKUENSI_NAME} sekali di HP supaya kabarnya bisa masuk saat app ditutup.`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border p-4 shadow-sm sm:flex-row sm:items-center" style={{ background: 'var(--brand-tint-2)', borderColor: 'color-mix(in srgb, var(--brand-secondary) 28%, transparent)' }}>
      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full" style={{ background: 'color-mix(in srgb, var(--brand-secondary) 16%, transparent)', color: 'var(--brand-secondary)' }}>
        <BellRing className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-gray-900">Pesanan masuk saat app kasir ditutup? Kabarnya bisa langsung ke HP.</p>
        <p className="mt-0.5 text-xs leading-relaxed text-gray-600">
          Pasang {SEFREKUENSI_NAME} dengan nomor {st.phone_masked || 'toko'}. Pesanan online, reservasi, dan bukti bayar mendarat sebagai notifikasi, tanpa bergantung pada WhatsApp. Gratis.
        </p>
      </div>
      <a href={st.play_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-full px-4 py-2 text-xs font-semibold text-white" style={{ background: 'var(--brand-secondary)' }}>
        <Download className="h-3.5 w-3.5" /> Pasang {SEFREKUENSI_NAME}
      </a>
    </div>
  );
}
