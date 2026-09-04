'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getReservationPublic } from '@/app/actions/storefront';
import { rp, waNumber, waLink, Card, TopBar, EmptyState, Spinner, PoweredBy, btnPrimary, btnSecondary } from '../../_ui';
import { CalendarDays, Clock, Users, Armchair, CheckCircle2, XCircle, Loader2, MessageCircle, Upload, Landmark, QrCode, ShieldCheck } from 'lucide-react';

type Phase = 'awaiting_deposit' | 'proof_sent' | 'awaiting_confirm' | 'confirmed' | 'seated' | 'completed' | 'cancelled' | 'no_show';

/**
 * Halaman lacak reservasi. Satu tujuan: pelanggan tahu apa yang harus
 * dilakukan sekarang. Kalau toko minta DP, halaman ini tempat bayar dan
 * kirim bukti; sesudah itu status mengikuti keputusan toko.
 *
 * DP statis (QRIS toko / transfer) tidak punya webhook. "Lunas" baru tercatat
 * saat kasir mengonfirmasi reservasi. Bukti yang diunggah di sini muncul di
 * dashboard dan aplikasi kasir.
 */
export default function ReservationTrackPage() {
  const params = useParams();
  const slug = params.slug as string;
  const id = params.id as string;
  const [resv, setResv] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    const data = await getReservationPublic(id);
    if (data) setResv(data);
    setLoading(false);
    return data;
  };

  useEffect(() => {
    let stopped = false;
    load();
    const poll = setInterval(async () => {
      if (stopped) return;
      const data = await load();
      if (data && ['completed', 'cancelled', 'no_show'].includes(data.status)) clearInterval(poll);
    }, 8000);
    return () => { stopped = true; clearInterval(poll); };
  }, [id]);

  const phase: Phase | null = useMemo(() => {
    if (!resv) return null;
    const dep = resv.deposit;
    if (['cancelled', 'no_show', 'completed', 'seated', 'confirmed'].includes(resv.status)) return resv.status as Phase;
    if (dep && dep.amount && ['pending', 'pending_manual_check'].includes(dep.status)) {
      return dep.proof_image_url ? 'proof_sent' : 'awaiting_deposit';
    }
    return 'awaiting_confirm';
  }, [resv]);

  const onPickProof = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !resv?.deposit?.payment_id) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`/api/proof/${resv.deposit.payment_id}`, { method: 'POST', body: fd });
      const data = await res.json();
      if (res.ok) {
        setUploadMsg({ ok: true, text: 'Bukti terkirim. Toko akan memeriksanya.' });
        await load();
      } else {
        setUploadMsg({ ok: false, text: data.detail || 'Unggah gagal, coba lagi.' });
      }
    } catch {
      setUploadMsg({ ok: false, text: 'Unggah gagal, periksa koneksi.' });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  if (loading) return <Spinner label="Memuat reservasi" />;
  if (!resv || !phase) {
    return (
      <EmptyState title="Reservasi tidak ditemukan" body="Tautan yang Anda buka tidak valid atau reservasi sudah dihapus."
        action={<Link href={`/${slug}`} className={btnPrimary}>Kembali ke menu</Link>} />
    );
  }

  const outlet = resv.outlet || {};
  const wa = waNumber(outlet.whatsapp);
  const dep = resv.deposit;
  const dateLabel = resv.reservation_date
    ? new Date(resv.reservation_date + 'T00:00:00').toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long' })
    : '-';
  const proofText = `Halo ${outlet.name || 'Kak'}, saya ${resv.customer_name || ''} sudah membayar DP ${dep ? rp(dep.amount) : ''} untuk reservasi ${dateLabel} pukul ${resv.start_time}. Berikut buktinya.`;

  const hero: Record<Phase, { title: string; body: string; tone: string; icon: any }> = {
    awaiting_deposit: {
      title: 'Bayar DP untuk mengamankan meja',
      body: `Toko meminta DP ${dep ? rp(dep.amount) : ''}. Bayar lewat cara di bawah, lalu unggah buktinya. Reservasi dibatalkan otomatis bila DP belum diterima dalam ${resv.deposit_timeout_minutes ?? 60} menit.`,
      tone: 'bg-[var(--surface-inverse)] text-white', icon: Clock,
    },
    proof_sent: {
      title: 'Bukti bayar sudah terkirim',
      body: 'Toko sedang memeriksa DP Anda. Begitu dikonfirmasi, halaman ini berubah sendiri dan kami kirim kabar lewat WhatsApp.',
      tone: 'text-white', icon: Loader2,
    },
    awaiting_confirm: {
      title: 'Menunggu konfirmasi toko',
      body: 'Toko akan meninjau ketersediaan meja dan mengonfirmasi reservasi Anda.',
      tone: 'text-white', icon: Loader2,
    },
    confirmed: {
      title: 'Reservasi dikonfirmasi',
      body: `Meja Anda siap pada ${dateLabel} pukul ${resv.start_time}. Datang tepat waktu, sebutkan nama ${resv.customer_name || ''} di kasir.`,
      tone: 'bg-[color-mix(in_srgb,var(--success)_16%,white)] text-[var(--text-strong)]', icon: CheckCircle2,
    },
    seated: {
      title: 'Selamat menikmati',
      body: dep?.status === 'paid' ? `DP ${rp(dep.amount)} sudah dipotong dari tagihan meja Anda.` : 'Anda sudah duduk. Tagihan dibayar di kasir saat selesai.',
      tone: 'bg-[color-mix(in_srgb,var(--success)_16%,white)] text-[var(--text-strong)]', icon: Armchair,
    },
    completed: {
      title: 'Reservasi selesai',
      body: `Terima kasih sudah berkunjung ke ${outlet.name}.`,
      tone: 'bg-[color-mix(in_srgb,var(--success)_16%,white)] text-[var(--text-strong)]', icon: CheckCircle2,
    },
    cancelled: {
      title: 'Reservasi dibatalkan',
      body: dep?.status === 'paid' ? 'Hubungi toko untuk pengembalian DP.' : 'Reservasi ini dibatalkan. Anda bisa membuat reservasi baru kapan saja.',
      tone: 'bg-[color-mix(in_srgb,var(--danger)_10%,white)] text-[var(--text-strong)]', icon: XCircle,
    },
    no_show: {
      title: 'Reservasi hangus',
      body: 'Anda tidak hadir pada waktu reservasi. DP, bila ada, tidak dikembalikan sesuai ketentuan toko.',
      tone: 'bg-[color-mix(in_srgb,var(--danger)_10%,white)] text-[var(--text-strong)]', icon: XCircle,
    },
  };
  const h = hero[phase];
  const HeroIcon = h.icon;
  const gradientHero = phase === 'awaiting_confirm' || phase === 'proof_sent';
  const showPayBlock = phase === 'awaiting_deposit' || phase === 'proof_sent';

  return (
    <div className="pb-24 md:pb-12">
      <TopBar back={`/${slug}`} title={<span className="font-display font-extrabold text-[15px] text-[var(--text-strong)]">Reservasi Anda</span>} />
      <main className="max-w-xl mx-auto px-4 mt-4 space-y-4">
        <section className={`rounded-[24px] p-5 ${h.tone}`} style={gradientHero ? { background: 'var(--gradient-aurora)' } : undefined}>
          <div className="flex gap-4">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${gradientHero || phase === 'awaiting_deposit' ? 'bg-white/15' : 'bg-white'}`}>
              <HeroIcon className={`w-6 h-6 ${gradientHero ? 'animate-spin' : ''}`} />
            </div>
            <div className="min-w-0">
              <h1 className="font-display font-extrabold text-xl leading-tight">{h.title}</h1>
              <p className={`mt-1.5 text-sm leading-relaxed ${gradientHero || phase === 'awaiting_deposit' ? 'text-white/85' : 'text-[var(--text-body)]'}`}>{h.body}</p>
            </div>
          </div>
        </section>

        {showPayBlock && dep && (
          <Card className="p-6 text-center">
            <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)] mb-4">DP {outlet.name}</p>
            {dep.method === 'qris' && dep.channel === 'xendit' && dep.qris_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(dep.qris_url)}&size=240x240&margin=6`}
                alt="Kode QRIS" className="w-56 h-56 mx-auto rounded-2xl border border-[var(--border-subtle)]" />
            )}
            {dep.method === 'qris' && dep.channel === 'manual' && (
              dep.qris_static_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={dep.qris_static_image_url} alt={`QRIS ${outlet.name}`} className="w-60 h-60 mx-auto rounded-2xl border border-[var(--border-subtle)] object-contain bg-white" />
              ) : (
                <div className="py-6 text-[var(--text-muted)]"><QrCode className="w-10 h-10 mx-auto mb-2" /><p className="text-sm">Pindai QRIS toko. Bila belum ada, hubungi toko lewat WhatsApp untuk cara bayar.</p></div>
              )
            )}
            {dep.method === 'transfer' && (
              <div className="py-3">
                <Landmark className="w-8 h-8 mx-auto text-[var(--text-muted)] mb-2" />
                {dep.bank_account_number ? (
                  <>
                    <p className="text-xl font-extrabold text-[var(--text-strong)]">{dep.bank_name || 'Bank'} {dep.bank_account_number}</p>
                    {dep.bank_account_name && <p className="text-sm text-[var(--text-body)]">a.n. {dep.bank_account_name}</p>}
                  </>
                ) : (
                  <p className="text-sm text-[var(--text-muted)]">Rekening toko belum tercantum. Hubungi toko lewat WhatsApp untuk nomor rekening.</p>
                )}
              </div>
            )}
            <p className="mt-4 text-2xl font-extrabold text-[var(--text-strong)]">{rp(dep.amount)}</p>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Bayar sesuai nominal, lalu unggah tangkapan layar buktinya.</p>

            {dep.channel === 'manual' && (
              <div className="mt-5 space-y-3">
                {dep.proof_image_url ? (
                  <div className="rounded-2xl border border-[var(--border-subtle)] p-3 flex items-center gap-3 text-left">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={dep.proof_image_url} alt="Bukti bayar" className="w-14 h-14 rounded-lg object-cover border border-[var(--border-subtle)]" />
                    <div className="text-sm">
                      <p className="font-semibold text-[var(--text-strong)] inline-flex items-center gap-1"><ShieldCheck className="w-4 h-4" /> Bukti terkirim</p>
                      <p className="text-[var(--text-muted)]">Salah unggah? Kirim ulang, yang terbaru dipakai.</p>
                    </div>
                  </div>
                ) : null}
                <label className={`${btnPrimary} inline-flex items-center gap-2 cursor-pointer ${uploading ? 'opacity-60 pointer-events-none' : ''}`}>
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {uploading ? 'Mengunggah' : dep.proof_image_url ? 'Kirim ulang bukti' : 'Unggah bukti bayar'}
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onPickProof} />
                </label>
                {uploadMsg && <p className={`text-sm ${uploadMsg.ok ? 'text-[var(--success)]' : 'text-[var(--danger)]'}`}>{uploadMsg.text}</p>}
                {wa && (
                  <a href={waLink(wa, proofText)} target="_blank" rel="noopener noreferrer" className={`${btnSecondary} inline-flex items-center gap-2`}>
                    <MessageCircle className="w-4 h-4" /> Atau kirim lewat WhatsApp
                  </a>
                )}
              </div>
            )}
            {dep.channel === 'xendit' && <p className="mt-3 text-xs text-[var(--text-muted)]">Halaman ini memperbarui sendiri setelah pembayaran diterima.</p>}
          </Card>
        )}

        <Card className="p-5">
          <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)] mb-3">Detail reservasi</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-start gap-2"><CalendarDays className="w-4 h-4 mt-0.5 text-[var(--text-muted)]" /><div><p className="text-[var(--text-muted)] text-xs">Tanggal</p><p className="font-semibold text-[var(--text-strong)]">{dateLabel}</p></div></div>
            <div className="flex items-start gap-2"><Clock className="w-4 h-4 mt-0.5 text-[var(--text-muted)]" /><div><p className="text-[var(--text-muted)] text-xs">Jam</p><p className="font-semibold text-[var(--text-strong)]">{resv.start_time}{resv.end_time ? ` sampai ${resv.end_time}` : ''}</p></div></div>
            <div className="flex items-start gap-2"><Users className="w-4 h-4 mt-0.5 text-[var(--text-muted)]" /><div><p className="text-[var(--text-muted)] text-xs">Tamu</p><p className="font-semibold text-[var(--text-strong)]">{resv.guest_count} orang</p></div></div>
            <div className="flex items-start gap-2"><Armchair className="w-4 h-4 mt-0.5 text-[var(--text-muted)]" /><div><p className="text-[var(--text-muted)] text-xs">Meja</p><p className="font-semibold text-[var(--text-strong)]">{resv.table_name || 'Ditentukan toko'}</p></div></div>
          </div>
          {dep && dep.amount ? (
            <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] flex items-center justify-between text-sm">
              <span className="text-[var(--text-muted)]">DP</span>
              <span className="font-semibold text-[var(--text-strong)]">
                {rp(dep.amount)} · {dep.status === 'paid' ? 'lunas' : dep.status === 'cancelled' ? 'dibatalkan' : dep.proof_image_url ? 'bukti terkirim' : 'belum dibayar'}
              </span>
            </div>
          ) : null}
          <p className="mt-4 text-xs text-[var(--text-muted)]">Atas nama {resv.customer_name}. {outlet.address ? `Lokasi: ${outlet.address}.` : ''}</p>
        </Card>

        <div className="flex flex-col sm:flex-row gap-2">
          {wa && (
            <a href={waLink(wa, `Halo ${outlet.name}, saya ingin bertanya soal reservasi ${dateLabel} pukul ${resv.start_time} atas nama ${resv.customer_name || ''}.`)} target="_blank" rel="noopener noreferrer" className={`${btnSecondary} flex-1 inline-flex items-center justify-center gap-2`}>
              <MessageCircle className="w-4 h-4" /> Hubungi toko
            </a>
          )}
          <Link href={`/${slug}`} className={`${btnSecondary} flex-1 text-center`}>Lihat menu</Link>
        </div>
        <PoweredBy />
      </main>
    </div>
  );
}
