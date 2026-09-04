'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getStorefrontOrder } from '@/app/actions/storefront';
import { rp, timeShort, waNumber, waLink, ORDER_TYPE_LABEL, Card, TopBar, EmptyState, Spinner, PoweredBy, btnPrimary, btnSecondary } from '../../_ui';
import { MessageCircle, MapPin, Utensils, Loader2, CheckCircle2, XCircle, Clock, ChefHat, PackageCheck, Receipt, RefreshCw, Upload } from 'lucide-react';

type Phase = 'awaiting_payment' | 'payment_failed' | 'awaiting_confirm' | 'preparing' | 'ready' | 'completed' | 'cancelled';

/**
 * Halaman lacak pesanan. Dibuka dari link WA yang dikirim backend, jadi
 * harus berdiri sendiri: nggak butuh keranjang, nggak butuh login.
 *
 * Fase dihitung dari status order + status pembayaran, karena "pending"
 * punya dua arti: belum bayar (QRIS) atau sudah bayar tapi toko belum
 * mengonfirmasi. Dua-duanya butuh kalimat yang berbeda.
 */
export default function OrderStatusPage() {
  const params = useParams();
  const slug = params.slug as string;
  const orderId = params.id as string;

  const [loading, setLoading] = useState(true);

  const [proofUploading, setProofUploading] = useState(false);

  const [proofMsg, setProofMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const onPickProof = async (e: React.ChangeEvent<HTMLInputElement>) => {

    const file = e.target.files?.[0];

    const pid = order?.payment?.payment_id;

    if (!file || !pid) return;

    setProofUploading(true);

    setProofMsg(null);

    try {

      const fd = new FormData();

      fd.append('file', file);

      const res = await fetch(`/api/proof/${pid}`, { method: 'POST', body: fd });

      const data = await res.json();

      if (res.ok) { setProofMsg({ ok: true, text: 'Bukti terkirim. Toko akan memeriksanya.' }); const fresh = await getStorefrontOrder(orderId); if (fresh) setOrder(fresh); }

      else setProofMsg({ ok: false, text: data.detail || 'Unggah gagal, coba lagi.' });

    } catch {

      setProofMsg({ ok: false, text: 'Unggah gagal, periksa koneksi.' });

    } finally {

      setProofUploading(false);

      e.target.value = '';

    }

  };
  const [order, setOrder] = useState<any>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let stopped = false;
    const load = async () => {
      const data = await getStorefrontOrder(orderId);
      if (stopped) return;
      if (data) setOrder(data);
      setLoading(false);
      return data;
    };
    load();
    const poll = setInterval(async () => {
      const data = await load();
      if (data && ['completed', 'cancelled'].includes(data.status) && data.payment?.status !== 'pending') clearInterval(poll);
    }, 5000);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => { stopped = true; clearInterval(poll); clearInterval(tick); };
  }, [orderId]);

  const phase: Phase | null = useMemo(() => {
    if (!order) return null;
    const pay = order.payment;
    if (order.status === 'cancelled') return 'cancelled';
    if (order.status === 'completed') return 'completed';
    if (order.status === 'ready' || order.status === 'served') return 'ready';
    if (order.status === 'preparing') return 'preparing';
    if (pay?.method === 'qris' && pay.status !== 'paid') {
      // QRIS statis toko: nggak ada webhook. Pelanggan bayar ke QR toko dan
      // kirim bukti, toko yang mengonfirmasi. Secara alur = menunggu toko.
      if (pay.channel === 'manual') return 'awaiting_confirm';
      return ['failed', 'cancelled', 'pending_manual_check'].includes(pay.status) ? 'payment_failed' : 'awaiting_payment';
    }
    return 'awaiting_confirm';
  }, [order]);

  if (loading) return <Spinner label="Memuat pesanan" />;
  if (!order || !phase) {
    return (
      <EmptyState title="Pesanan tidak ditemukan" body="Tautan pesanan tidak valid atau sudah tidak tersedia."
        action={<Link href={`/${slug}`} className={btnPrimary}>Kembali ke menu</Link>} />
    );
  }

  const outlet = order.outlet || {};
  const wa = waNumber(outlet.whatsapp);
  const typeKey = order.order_type as string;
  const typeLabel = ORDER_TYPE_LABEL[typeKey] || typeKey;

  const secondsLeft = (iso?: string | null) => (iso ? Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000)) : 0);
  const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const etaAt = order.accepted_at && order.eta_minutes
    ? new Date(new Date(order.accepted_at).getTime() + order.eta_minutes * 60000) : null;
  const readyWord = typeKey === 'delivery' ? 'siap diantar' : typeKey === 'dine_in' ? 'diantar ke meja' : 'siap diambil';

  const manualQrisUnpaid = order.payment?.method === 'qris' && order.payment?.channel === 'manual' && order.payment?.status !== 'paid';
  const proofSent = !!order.payment?.proof_image_url;
  const proofText = `Halo ${outlet.name || 'Kak'}, saya sudah membayar pesanan #${order.display_number} sebesar ${rp(order.total_amount)} lewat QRIS. Berikut bukti bayarnya.`;

  const hero: Record<Phase, { title: string; body: string; tone: string; icon: any }> = {
    awaiting_payment: {
      title: 'Selesaikan pembayaran',
      body: 'Pindai kode QR di bawah dengan aplikasi e-wallet atau m-banking. Setelah lunas, pesanan diteruskan ke toko.',
      tone: 'bg-[var(--surface-inverse)] text-white', icon: Clock,
    },
    payment_failed: {
      title: 'Pembayaran belum berhasil',
      body: 'Kode QR tidak tersedia atau sudah kedaluwarsa. Pesan ulang dengan pilihan bayar di kasir, atau hubungi toko.',
      tone: 'bg-[color-mix(in_srgb,var(--danger)_10%,white)] text-[var(--text-strong)]', icon: XCircle,
    },
    awaiting_confirm: {
      title: manualQrisUnpaid ? (proofSent ? 'Bukti bayar terkirim' : 'Bayar lalu unggah bukti') : 'Menunggu konfirmasi toko',
      body: manualQrisUnpaid
        ? (proofSent
          ? 'Toko sedang memeriksa bukti bayar Anda. Halaman ini berubah sendiri begitu pesanan dikonfirmasi.'
          : 'Pindai QRIS toko di bawah, lalu unggah tangkapan layar bukti bayar. Toko mengonfirmasi pesanan setelah bukti diterima.')
        : order.confirm_deadline
        ? `Toko merespons paling lambat pukul ${timeShort(order.confirm_deadline)}. Bila tidak, pesanan dibatalkan otomatis${order.payment?.status === 'paid' ? ' dan pembayaran dikembalikan' : ''}.`
        : 'Toko akan segera merespons pesanan Anda.',
      tone: 'text-white', icon: Loader2,
    },
    preparing: {
      title: 'Pesanan dikonfirmasi',
      body: etaAt ? `Toko sedang menyiapkan. Perkiraan ${readyWord} sekitar pukul ${timeShort(etaAt.toISOString())}.` : 'Toko sedang menyiapkan pesanan Anda.',
      tone: 'text-white', icon: ChefHat,
    },
    ready: {
      title: typeKey === 'delivery' ? 'Pesanan sedang diantar' : typeKey === 'dine_in' ? 'Pesanan menuju meja Anda' : 'Pesanan siap diambil',
      body: typeKey === 'delivery' ? 'Kurir toko sedang menuju alamat Anda.' : typeKey === 'dine_in' ? 'Selamat menikmati.' : `Silakan ambil di ${outlet.name}. Sebutkan nomor pesanan #${order.display_number}.`,
      tone: 'bg-[color-mix(in_srgb,var(--success)_16%,white)] text-[var(--text-strong)]', icon: PackageCheck,
    },
    completed: {
      title: 'Pesanan selesai',
      body: `Terima kasih sudah memesan di ${outlet.name}.`,
      tone: 'bg-[color-mix(in_srgb,var(--success)_16%,white)] text-[var(--text-strong)]', icon: CheckCircle2,
    },
    cancelled: {
      title: 'Pesanan dibatalkan',
      body: order.cancel_reason ? `Alasan: ${order.cancel_reason}.` : 'Pesanan ini dibatalkan.',
      tone: 'bg-[color-mix(in_srgb,var(--danger)_10%,white)] text-[var(--text-strong)]', icon: XCircle,
    },
  };
  const h = hero[phase];
  const HeroIcon = h.icon;
  const gradientHero = phase === 'awaiting_confirm' || phase === 'preparing';

  const steps = [
    { label: 'Pesanan dikirim', at: order.created_at, done: true },
    { label: 'Dikonfirmasi toko', at: order.accepted_at, done: !!order.accepted_at },
    { label: typeKey === 'delivery' ? 'Diantar' : 'Siap', at: order.ready_at, done: !!order.ready_at || phase === 'completed' },
    { label: 'Selesai', at: phase === 'completed' ? order.updated_at : null, done: phase === 'completed' },
  ];
  const currentStep = steps.filter((s) => s.done).length - 1;

  const qrisLeft = secondsLeft(order.payment?.qris_expired_at);
  const refund = order.refund;

  return (
    <div className="pb-28 md:pb-12">
      <TopBar back={`/${slug}`} title={
        <span className="block">
          <span className="block font-display font-extrabold text-[15px] text-[var(--text-strong)] leading-none">Pesanan #{order.display_number}</span>
          <span className="block text-[11px] text-[var(--text-muted)] mt-0.5">{outlet.name} · {timeShort(order.created_at)}</span>
        </span>
      } />

      <main className="max-w-2xl mx-auto px-4 pt-5 space-y-4">
        {/* Status utama */}
        <section className={`rounded-[28px] p-6 ${h.tone} relative overflow-hidden`} style={gradientHero ? { background: 'var(--gradient-aurora)' } : undefined}>
          <div className="flex items-start gap-4">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${gradientHero || phase === 'awaiting_payment' ? 'bg-white/15' : 'bg-white'}`}>
              <HeroIcon className={`w-6 h-6 ${phase === 'awaiting_confirm' ? 'animate-spin' : ''}`} />
            </div>
            <div className="min-w-0">
              <h1 className="font-display font-extrabold text-2xl tracking-tight leading-tight">{h.title}</h1>
              <p className={`mt-1.5 text-sm leading-relaxed ${gradientHero || phase === 'awaiting_payment' ? 'text-white/85' : 'text-[var(--text-body)]'}`}>{h.body}</p>
              {phase === 'awaiting_confirm' && order.confirm_deadline && (
                <p className="mt-3 inline-flex items-center gap-2 text-sm font-semibold bg-white/15 px-3 py-1.5 rounded-full">
                  <Clock className="w-4 h-4" /> {mmss(secondsLeft(order.confirm_deadline))} tersisa
                </p>
              )}
              {phase === 'preparing' && order.eta_minutes && (
                <p className="mt-3 inline-flex items-center gap-2 text-sm font-semibold bg-white/15 px-3 py-1.5 rounded-full">
                  <Clock className="w-4 h-4" /> Perkiraan {order.eta_minutes} menit
                </p>
              )}
            </div>
          </div>
        </section>

        {/* QRIS statis toko: gambar QR milik toko + tombol kirim bukti */}
        {phase === 'awaiting_confirm' && manualQrisUnpaid && (
          <Card className="p-6 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)] mb-4">QRIS {outlet.name}</p>
            {order.payment?.qris_static_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={order.payment.qris_static_image_url} alt={`QRIS ${outlet.name}`} className="w-60 h-60 mx-auto rounded-2xl border border-[var(--border-subtle)] object-contain bg-white" />
            ) : (
              <p className="text-sm text-[var(--text-muted)] py-4">Kode QRIS tersedia di kasir. Tunjukkan nomor pesanan #{order.display_number}.</p>
            )}
            <p className="mt-4 text-2xl font-extrabold text-[var(--text-strong)]">{rp(order.total_amount)}</p>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Bayar sesuai nominal, lalu unggah tangkapan layar buktinya.</p>
            <div className="mt-4 space-y-3">
              {proofSent && (
                <div className="rounded-2xl border border-[var(--border-subtle)] p-3 flex items-center gap-3 text-left">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={order.payment.proof_image_url} alt="Bukti bayar" className="w-14 h-14 rounded-lg object-cover border border-[var(--border-subtle)]" />
                  <div className="text-sm">
                    <p className="font-semibold text-[var(--text-strong)]">Bukti terkirim, menunggu toko</p>
                    <p className="text-[var(--text-muted)]">Salah unggah? Kirim ulang, yang terbaru dipakai.</p>
                  </div>
                </div>
              )}
              {order.payment?.payment_id && (
                <label className={`${btnPrimary} inline-flex items-center gap-2 cursor-pointer ${proofUploading ? 'opacity-60 pointer-events-none' : ''}`}>
                  {proofUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {proofUploading ? 'Mengunggah' : proofSent ? 'Kirim ulang bukti' : 'Unggah bukti bayar'}
                  <input type="file" accept="image/*" className="hidden" onChange={onPickProof} />
                </label>
              )}
              {proofMsg && <p className={`text-sm ${proofMsg.ok ? 'text-[var(--success)]' : 'text-[var(--danger)]'}`}>{proofMsg.text}</p>}
              {wa ? (
                <a href={waLink(wa, proofText)} target="_blank" rel="noopener noreferrer" className={`${btnSecondary} inline-flex items-center gap-2`}>
                  <MessageCircle className="w-4 h-4" /> Atau kirim lewat WhatsApp
                </a>
              ) : (
                <p className="text-xs text-[var(--text-muted)]">Tunjukkan bukti bayar ke kasir saat mengambil pesanan.</p>
              )}
            </div>
          </Card>
        )}

        {/* QRIS */}
        {phase === 'awaiting_payment' && (
          <Card className="p-6 text-center">
            {order.payment?.qris_url ? (
              <>
                <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)] mb-4">Pindai untuk membayar</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(order.payment.qris_url)}&size=240x240&margin=6`}
                  alt="Kode QRIS" className="w-56 h-56 mx-auto rounded-2xl border border-[var(--border-subtle)]" />
                <p className="mt-4 text-2xl font-extrabold text-[var(--text-strong)]">{rp(order.total_amount)}</p>
                {qrisLeft > 0
                  ? <p className="mt-1 text-sm text-[var(--text-muted)]">Berlaku <b className={qrisLeft < 60 ? 'text-[var(--danger)]' : 'text-[var(--text-strong)]'}>{mmss(qrisLeft)}</b></p>
                  : <button onClick={() => window.location.reload()} className="mt-2 text-sm font-semibold text-[var(--text-strong)] inline-flex items-center gap-1"><RefreshCw className="w-4 h-4" /> Kode kedaluwarsa, muat ulang</button>}
                <p className="mt-3 text-xs text-[var(--text-muted)]">Halaman ini memperbarui sendiri setelah pembayaran diterima.</p>
              </>
            ) : (
              <div className="py-6"><Loader2 className="w-7 h-7 animate-spin text-[var(--text-muted)] mx-auto mb-3" /><p className="text-sm text-[var(--text-muted)]">Menyiapkan kode QR</p></div>
            )}
          </Card>
        )}

        {/* Pengembalian dana */}
        {phase === 'cancelled' && order.payment?.method === 'qris' && (order.payment?.status === 'paid' || order.payment?.status === 'refunded' || refund) && (
          <Card className="p-5 flex gap-3">
            <Receipt className="w-5 h-5 shrink-0 text-[var(--text-muted)] mt-0.5" />
            <div className="text-sm">
              <p className="font-bold text-[var(--text-strong)]">Pengembalian dana {rp(refund?.amount ?? order.total_amount)}</p>
              <p className="text-[var(--text-body)] mt-0.5">
                {refund?.status === 'completed'
                  ? 'Dikembalikan ke metode pembayaran Anda, biasanya 1 sampai 3 hari kerja.'
                  : 'Sedang diproses toko. Bila belum diterima dalam 1 hari kerja, hubungi toko lewat WhatsApp.'}
              </p>
            </div>
          </Card>
        )}

        {/* Perjalanan pesanan */}
        {phase !== 'cancelled' && phase !== 'payment_failed' && (
          <Card className="p-5">
            <ol className="relative">
              {steps.map((s, i) => {
                const done = i <= currentStep;
                const current = i === currentStep && phase !== 'completed';
                return (
                  <li key={s.label} className="flex gap-4 relative pb-6 last:pb-0">
                    {i < steps.length - 1 && <span className={`absolute left-[11px] top-6 bottom-0 w-0.5 ${i < currentStep ? 'bg-[var(--text-strong)]' : 'bg-[var(--border-subtle)]'}`} />}
                    <span className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${done ? 'bg-[var(--text-strong)] text-white' : 'bg-[var(--bg-subtle)] border border-[var(--border-default)]'}`}>
                      {done && !current && <CheckCircle2 className="w-4 h-4" />}
                      {current && <span className="w-2 h-2 rounded-full bg-white animate-pulse" />}
                    </span>
                    <div className="flex-1 flex items-baseline justify-between gap-3 -mt-0.5">
                      <span className={`text-sm font-semibold ${done ? 'text-[var(--text-strong)]' : 'text-[var(--text-muted)]'}`}>{s.label}</span>
                      {s.at && done && <span className="text-xs text-[var(--text-muted)]">{timeShort(s.at)}</span>}
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>
        )}

        {/* Rincian */}
        <Card className="p-5 space-y-4">
          <h2 className="font-display font-extrabold text-[17px] text-[var(--text-strong)]">Rincian pesanan</h2>
          <ul className="space-y-2.5">
            {order.items.map((item: any) => (
              <li key={item.id} className="flex justify-between gap-3 text-sm">
                <div>
                  <p className="text-[var(--text-strong)]"><span className="font-bold">{item.quantity}x</span> {item.product_name}</p>
                  {item.notes && <p className="text-xs text-[var(--text-muted)]">{item.notes}</p>}
                </div>
                <span className="font-semibold text-[var(--text-strong)] shrink-0">{rp(item.subtotal ?? item.price * item.quantity)}</span>
              </li>
            ))}
          </ul>
          {order.notes && (
            <p className="text-sm bg-[var(--bg-subtle)] rounded-xl px-3 py-2 text-[var(--text-body)]"><span className="font-semibold text-[var(--text-strong)]">Catatan:</span> {order.notes}</p>
          )}
          <dl className="pt-3 border-t border-[var(--border-subtle)] grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-[var(--text-muted)]">Pemesan</dt><dd className="text-right font-medium text-[var(--text-strong)]">{order.customer_name || '-'}</dd>
            <dt className="text-[var(--text-muted)]">Cara menerima</dt><dd className="text-right font-medium text-[var(--text-strong)]">{typeLabel}{order.table_name ? ` · Meja ${order.table_name}` : ''}</dd>
            <dt className="text-[var(--text-muted)]">Pembayaran</dt>
            <dd className="text-right font-medium text-[var(--text-strong)]">
              {order.payment?.method === 'qris' ? 'QRIS' : order.payment?.method === 'cash' ? 'Di kasir' : 'Tagihan meja'}
              {order.payment?.status === 'paid' && ' · Lunas'}
              {order.payment?.status === 'refunded' && ' · Dikembalikan'}
            </dd>
            <dt className="text-[var(--text-muted)]">Waktu pesan</dt><dd className="text-right font-medium text-[var(--text-strong)]">{new Date(order.created_at).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</dd>
          </dl>
          {order.delivery_address && (
            <div className="flex gap-2 text-sm bg-[var(--bg-subtle)] rounded-xl px-3 py-2.5">
              <MapPin className="w-4 h-4 text-[var(--text-muted)] shrink-0 mt-0.5" />
              <p className="text-[var(--text-body)]">{order.delivery_address}</p>
            </div>
          )}
          {typeKey === 'dine_in' && !order.delivery_address && order.table_name && (
            <div className="flex gap-2 text-sm bg-[var(--bg-subtle)] rounded-xl px-3 py-2.5">
              <Utensils className="w-4 h-4 text-[var(--text-muted)] shrink-0 mt-0.5" />
              <p className="text-[var(--text-body)]">Meja {order.table_name}</p>
            </div>
          )}
          <div className="pt-3 border-t border-[var(--border-subtle)] flex justify-between items-center">
            <span className="font-bold text-[var(--text-strong)]">Total</span>
            <span className="text-xl font-extrabold text-[var(--text-strong)]">{rp(order.total_amount)}</span>
          </div>
        </Card>

        <div className="hidden md:flex gap-3">
          {wa && <a href={waLink(wa, `Halo ${outlet.name}, saya ingin bertanya tentang pesanan #${order.display_number}.`)} target="_blank" rel="noreferrer" className={`${btnSecondary} flex-1`}><MessageCircle className="w-4 h-4" /> Hubungi toko</a>}
          <Link href={`/${slug}`} className={`${btnPrimary} flex-1`}>{phase === 'completed' || phase === 'cancelled' ? 'Pesan lagi' : 'Kembali ke menu'}</Link>
        </div>
        <PoweredBy />
      </main>

      <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[var(--surface-card)] border-t border-[var(--border-subtle)] px-4 pt-3 pb-5 flex gap-3">
        {wa && <a href={waLink(wa, `Halo ${outlet.name}, saya ingin bertanya tentang pesanan #${order.display_number}.`)} target="_blank" rel="noreferrer" className={`${btnSecondary} flex-1`}><MessageCircle className="w-4 h-4" /> Hubungi toko</a>}
        <Link href={`/${slug}`} className={`${btnPrimary} flex-1`}>{phase === 'completed' || phase === 'cancelled' ? 'Pesan lagi' : 'Menu'}</Link>
      </div>
    </div>
  );
}
