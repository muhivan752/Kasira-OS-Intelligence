'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { rp, waNumber, waLink, Card, Spinner, EmptyState, PoweredBy, btnPrimary, btnSecondary, inputCls } from '../../_ui';
import { MapPin, MessageCircle, Navigation, Camera, CheckCircle2, XCircle, Bike, Loader2 } from 'lucide-react';

/**
 * Halaman tugas KURIR (delivery gelombang 2b, 5 Sep 2026).
 *
 * Kurir orang toko nggak selalu punya app kasir, dan memang nggak boleh
 * dipaksa punya. Link halaman ini dikirim ke WA kurir waktu kasir
 * menyerahkan pesanan: alamat, peta, chat pelanggan, tagihan COD, tombol
 * Sampai (foto dari kamera HP lewat browser, opsional) dan Gagal antar.
 * Kuncinya token `k` acak per order, BUKAN UUID order (itu sudah beredar di
 * link lacak pelanggan; pelanggan nggak boleh bisa menandai sendiri sampai).
 *
 * SEMUA hook di atas `return` awal (React #310, CLAUDE.md #31).
 */
type Task = {
  id: string; display_number: number; status: string; delivery_status: string | null; courier_name: string | null;
  outlet: { name: string; slug: string; whatsapp: string | null };
  customer_name: string | null; customer_phone: string | null;
  delivery_address: string | null; delivery_lat: number | null; delivery_lng: number | null; delivery_distance_km: number | null;
  notes: string | null; items: { product_name: string; quantity: number }[];
  total_amount: number; delivery_fee: number; grand_total: number; cod_pending: boolean;
  delivered_at: string | null; delivery_received_by: string | null; delivery_proof_url: string | null; delivery_failed_reason: string | null;
};

const FAIL_PRESETS = ['Alamat tidak ditemukan', 'Pelanggan tidak bisa dihubungi', 'Pelanggan menolak pesanan', 'Kendala di jalan'];

export default function CourierTaskPage() {
  const params = useParams();
  const search = useSearchParams();
  const slug = params.slug as string;
  const id = params.id as string;
  const k = search.get('k') || '';

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<'idle' | 'delivered' | 'failed'>('idle');
  const [receivedBy, setReceivedBy] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [failReason, setFailReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const base = useMemo(() => `/api/antar/${slug}/${id}?k=${encodeURIComponent(k)}`, [slug, id, k]);

  useEffect(() => {
    if (!slug || !id) return;
    (async () => {
      try {
        const res = await fetch(base, { cache: 'no-store' });
        const data = await res.json();
        if (res.ok) setTask(data.data);
      } catch {}
      setLoading(false);
    })();
  }, [base, slug, id]);

  useEffect(() => {
    if (!photo) { setPreview(null); return; }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  async function submitDelivered() {
    setBusy(true); setErr(null);
    try {
      const fd = new FormData();
      if (receivedBy.trim()) fd.append('received_by', receivedBy.trim());
      if (photo) fd.append('file', photo, photo.name || 'bukti.jpg');
      const res = await fetch(base, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) { setErr(typeof data?.detail === 'string' ? data.detail : 'Gagal menandai sampai'); return; }
      setTask(data.data); setMode('idle');
    } catch { setErr('Tidak ada koneksi. Coba lagi.'); }
    finally { setBusy(false); }
  }

  async function submitFailed() {
    if (failReason.trim().length < 3) return;
    setBusy(true); setErr(null);
    try {
      const res = await fetch(`${base}&action=failed`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: failReason.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setErr(typeof data?.detail === 'string' ? data.detail : 'Gagal menyimpan'); return; }
      setTask(data.data); setMode('idle');
    } catch { setErr('Tidak ada koneksi. Coba lagi.'); }
    finally { setBusy(false); }
  }

  if (loading) return <Spinner label="Memuat tugas" />;
  if (!task) {
    return (
      <EmptyState
        title="Link tugas tidak berlaku"
        body="Link ini salah atau sudah tidak aktif. Minta link baru ke kasir toko."
      />
    );
  }

  const done = task.delivery_status === 'delivered';
  const failed = task.delivery_status === 'failed';
  const cancelled = task.status === 'cancelled';
  const custWa = waNumber(task.customer_phone);
  const mapsHref = task.delivery_lat != null && task.delivery_lng != null
    ? `https://www.google.com/maps/dir/?api=1&destination=${task.delivery_lat},${task.delivery_lng}`
    : task.delivery_address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(task.delivery_address)}` : null;

  return (
    <div className="pb-12">
      <header className="sticky top-0 z-30 border-b border-[var(--border-subtle)] bg-[color-mix(in_srgb,var(--bg-base)_88%,transparent)] backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-xl items-center gap-3 px-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--brand-tint)]"><Bike className="h-5 w-5 text-[var(--brand-secondary)]" /></span>
          <div className="min-w-0 flex-1">
            <p className="font-display text-[15px] font-extrabold leading-none text-[var(--text-strong)]">Antar #{task.display_number}</p>
            <p className="mt-0.5 text-[11px] text-[var(--text-muted)]">{task.outlet.name}{task.courier_name ? ` · ${task.courier_name}` : ''}</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-xl space-y-4 px-4 pt-4">
        {/* Status atas */}
        {cancelled ? (
          <Card className="p-5 bg-[color-mix(in_srgb,var(--danger)_10%,white)]">
            <p className="font-display text-lg font-extrabold text-[var(--text-strong)]">Pesanan dibatalkan toko</p>
            <p className="mt-1 text-sm text-[var(--text-body)]">Tidak perlu diantar. Hubungi kasir kalau barangnya sudah terlanjur dibawa.</p>
          </Card>
        ) : done ? (
          <Card className="p-5 bg-[color-mix(in_srgb,var(--success)_16%,white)]">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-[var(--success)]" />
              <div>
                <p className="font-display text-lg font-extrabold text-[var(--text-strong)]">Sudah sampai. Terima kasih.</p>
                <p className="mt-1 text-sm text-[var(--text-body)]">
                  {task.delivery_received_by ? `Diterima ${task.delivery_received_by}. ` : ''}Toko dan pelanggan sudah dikabari.
                </p>
              </div>
            </div>
            {task.delivery_proof_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={task.delivery_proof_url} alt="Bukti serah terima" className="mt-4 max-h-56 w-full rounded-xl object-cover" />
            )}
          </Card>
        ) : failed ? (
          <Card className="p-5 bg-[color-mix(in_srgb,var(--danger)_10%,white)]">
            <div className="flex items-start gap-3">
              <XCircle className="mt-0.5 h-6 w-6 shrink-0 text-[var(--danger)]" />
              <div>
                <p className="font-display text-lg font-extrabold text-[var(--text-strong)]">Ditandai gagal antar</p>
                <p className="mt-1 text-sm text-[var(--text-body)]">Alasan: {task.delivery_failed_reason}. Kasir sudah dikabari. Kalau akhirnya ketemu, tekan Sampai di bawah.</p>
              </div>
            </div>
          </Card>
        ) : (
          <Card className={`p-5 ${task.cod_pending ? 'bg-[var(--surface-inverse)] text-white' : ''}`}>
            <p className={`text-xs uppercase tracking-wide ${task.cod_pending ? 'text-white/70' : 'text-[var(--text-muted)]'}`}>
              {task.cod_pending ? 'Tagih tunai ke pelanggan' : 'Sudah dibayar, tidak perlu tagih'}
            </p>
            <p className="mt-1 font-display text-3xl font-extrabold">{task.cod_pending ? rp(task.grand_total) : rp(0)}</p>
            {task.cod_pending && task.delivery_fee > 0 && (
              <p className="mt-1 text-xs text-white/70">Pesanan {rp(task.total_amount)} + ongkir {rp(task.delivery_fee)}</p>
            )}
          </Card>
        )}

        {/* Alamat + peta + pelanggan */}
        <Card className="p-5 space-y-4">
          <div className="flex items-start gap-3">
            <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-[var(--text-muted)]" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-[var(--text-strong)]">{task.delivery_address || 'Alamat tidak diisi, hubungi pelanggan'}</p>
              {task.delivery_distance_km != null && <p className="text-xs text-[var(--text-muted)]">{task.delivery_distance_km.toFixed(1)} km dari toko</p>}
            </div>
          </div>
          {task.notes && (
            <p className="rounded-xl bg-[color-mix(in_srgb,var(--warning)_14%,white)] px-3 py-2 text-sm text-[var(--text-strong)]">Catatan: {task.notes}</p>
          )}
          <div className="grid grid-cols-2 gap-2">
            {mapsHref && (
              <a href={mapsHref} target="_blank" rel="noreferrer" className={btnPrimary}><Navigation className="h-4 w-4" /> Buka peta</a>
            )}
            {custWa ? (
              <a href={waLink(custWa, `Halo ${task.customer_name || ''}, saya kurir dari ${task.outlet.name}, membawa pesanan #${task.display_number}.`)} target="_blank" rel="noreferrer" className={btnSecondary}>
                <MessageCircle className="h-4 w-4" /> Chat pelanggan
              </a>
            ) : (
              <span className={`${btnSecondary} opacity-50`}>Nomor pelanggan kosong</span>
            )}
          </div>
          <p className="text-sm text-[var(--text-muted)]">Pemesan: <span className="font-semibold text-[var(--text-strong)]">{task.customer_name || '-'}</span></p>
        </Card>

        {/* Isi pesanan */}
        <Card className="p-5">
          <p className="mb-2 text-xs uppercase tracking-wide text-[var(--text-muted)]">Yang dibawa</p>
          <ul className="space-y-1.5">
            {task.items.map((it, i) => (
              <li key={i} className="flex gap-3 text-sm text-[var(--text-strong)]"><span className="w-8 font-bold">{it.quantity}x</span><span>{it.product_name}</span></li>
            ))}
          </ul>
        </Card>

        {/* Aksi */}
        {!cancelled && !done && (
          <Card className="p-5 space-y-3">
            {mode === 'idle' && (
              <>
                <button onClick={() => { setMode('delivered'); setErr(null); }} className={`${btnPrimary} w-full`}>
                  <CheckCircle2 className="h-5 w-5" /> {task.cod_pending ? 'Sampai, tunai diterima' : 'Sudah sampai'}
                </button>
                {!failed && (
                  <button onClick={() => { setMode('failed'); setErr(null); }} className={`${btnSecondary} w-full text-[var(--danger)]`}>
                    <XCircle className="h-5 w-5" /> Gagal antar
                  </button>
                )}
              </>
            )}

            {mode === 'delivered' && (
              <>
                <p className="font-display text-lg font-extrabold text-[var(--text-strong)]">Pesanan #{task.display_number} sampai?</p>
                <p className="text-sm text-[var(--text-muted)]">
                  {task.cod_pending ? `Pastikan tunai ${rp(task.grand_total)} sudah diterima. ` : ''}Foto dan nama penerima boleh dikosongkan.
                </p>
                <input className={inputCls} placeholder="Diterima oleh (opsional)" value={receivedBy} onChange={(e) => setReceivedBy(e.target.value)} maxLength={80} />
                <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => setPhoto(e.target.files?.[0] || null)} />
                {preview ? (
                  <div className="relative">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={preview} alt="Foto bukti" className="max-h-56 w-full rounded-xl object-cover" />
                    <button onClick={() => fileRef.current?.click()} className="absolute bottom-2 right-2 rounded-full bg-black/60 px-3 py-1.5 text-xs font-semibold text-white">Ganti foto</button>
                  </div>
                ) : (
                  <button onClick={() => fileRef.current?.click()} className={`${btnSecondary} w-full`}><Camera className="h-5 w-5" /> Foto bukti serah terima (opsional)</button>
                )}
                {err && <p className="text-sm text-[var(--danger)]">{err}</p>}
                <button onClick={submitDelivered} disabled={busy} className={`${btnPrimary} w-full`}>
                  {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />} {busy ? 'Mengirim' : 'Tandai sampai'}
                </button>
                <button onClick={() => setMode('idle')} disabled={busy} className={`${btnSecondary} w-full`}>Batal</button>
              </>
            )}

            {mode === 'failed' && (
              <>
                <p className="font-display text-lg font-extrabold text-[var(--text-strong)]">Kenapa gagal?</p>
                <p className="text-sm text-[var(--text-muted)]">Pesanan tidak dibatalkan. Kasir yang memutuskan kirim ulang atau batal.</p>
                <div className="flex flex-wrap gap-2">
                  {FAIL_PRESETS.map((p) => (
                    <button key={p} onClick={() => setFailReason(p)} className={`rounded-full px-3 py-1.5 text-sm font-semibold ${failReason === p ? 'bg-[var(--surface-inverse)] text-white' : 'bg-[var(--bg-subtle)] text-[var(--text-strong)]'}`}>{p}</button>
                  ))}
                </div>
                <input className={inputCls} placeholder="Atau tulis alasan lain" value={failReason} onChange={(e) => setFailReason(e.target.value)} maxLength={120} />
                {err && <p className="text-sm text-[var(--danger)]">{err}</p>}
                <button onClick={submitFailed} disabled={busy || failReason.trim().length < 3} className={`${btnPrimary} w-full bg-[var(--danger)]`}>
                  {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <XCircle className="h-5 w-5" />} Tandai gagal antar
                </button>
                <button onClick={() => setMode('idle')} disabled={busy} className={`${btnSecondary} w-full`}>Batal</button>
              </>
            )}
          </Card>
        )}

        {task.outlet.whatsapp && waNumber(task.outlet.whatsapp) && (
          <a href={waLink(waNumber(task.outlet.whatsapp)!, `Halo, soal tugas antar #${task.display_number}.`)} target="_blank" rel="noreferrer" className="block text-center text-sm font-semibold text-[var(--text-muted)] underline">
            Hubungi kasir toko
          </a>
        )}
        <PoweredBy />
      </main>
    </div>
  );
}
