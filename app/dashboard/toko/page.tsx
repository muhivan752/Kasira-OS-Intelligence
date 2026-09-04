'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import QRCode from 'qrcode';
import { getOutlets, getProducts, updateOutlet } from '@/app/actions/api';
import { BRAND, SITE_URL } from '@/lib/brand';
import {
  Globe, Copy, Check, Share2, Download, Printer, ExternalLink, MapPin, Image as ImageIcon,
  MessageCircle, Clock, UtensilsCrossed, CircleCheck, CircleAlert, ChevronRight, Search, Loader2,
} from 'lucide-react';

/**
 * Halaman "Toko Online" (toko bisa ditemukan, 4 Sep 2026).
 *
 * Masalah yang diselesaikan: storefront cuma bisa ditemukan kalau pemilik
 * nyebar link-nya sendiri. Halaman ini ngasih pemilik SEMUA pintu masuk ke
 * tokonya di satu tempat: link, QR yang bisa diunduh dan dicetak jadi stiker,
 * bagikan ke WA, saklar tampil di /jelajah dan Google, daftar periksa
 * kelengkapan profil (yang dibaca Google lewat JSON-LD), dan panduan
 * Google Business Profile + Instagram.
 */
export default function TokoOnlinePage() {
  const [outlet, setOutlet] = useState<any>(null);
  const [productCount, setProductCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [qr, setQr] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [savingListed, setSavingListed] = useState(false);

  const url = useMemo(() => (outlet?.slug ? `${SITE_URL}/${outlet.slug}` : ''), [outlet?.slug]);
  const shortUrl = url.replace(/^https?:\/\//, '');

  useEffect(() => {
    (async () => {
      try {
        const outlets = await getOutlets();
        const o = outlets?.[0] || null;
        setOutlet(o);
        if (o?.brand_id) {
          const products = await getProducts(o.brand_id);
          setProductCount((products || []).filter((p: any) => p.is_active !== false).length);
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!url) return;
    QRCode.toDataURL(url, { width: 640, margin: 2, errorCorrectionLevel: 'M', color: { dark: '#111111', light: '#FFFFFF' } })
      .then(setQr)
      .catch(() => setQr(''));
  }, [url]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {}
  };

  const shareWa = () => {
    const text = `Halo! Sekarang ${outlet?.name} bisa dipesan online. Lihat menu dan pesan di sini: ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener');
  };

  const downloadQr = () => {
    if (!qr) return;
    const a = document.createElement('a');
    a.href = qr;
    a.download = `qr-${outlet?.slug || 'toko'}.png`;
    a.click();
  };

  const printSticker = () => {
    if (!qr) return;
    const w = window.open('', '_blank', 'noopener,width=720,height=900');
    if (!w) return;
    const esc = (s: string) => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string));
    w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Stiker ${esc(outlet?.name || '')}</title>
<style>
  @page { size: A5 portrait; margin: 12mm; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; color: #111; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
  .card { width: 118mm; border: 1.2mm solid #111; border-radius: 8mm; padding: 10mm; text-align: center; box-sizing: border-box; }
  .eyebrow { font-size: 11pt; letter-spacing: .12em; text-transform: uppercase; color: #7c3aed; font-weight: 700; }
  h1 { font-size: 22pt; margin: 3mm 0 1mm; line-height: 1.15; }
  .sub { font-size: 11pt; color: #444; margin-bottom: 6mm; }
  img { width: 72mm; height: 72mm; }
  .url { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12pt; font-weight: 700; margin-top: 4mm; word-break: break-all; }
  .foot { font-size: 9pt; color: #666; margin-top: 5mm; }
  @media print { .noprint { display: none } }
</style></head><body>
<div class="card">
  <div class="eyebrow">Scan untuk pesan</div>
  <h1>${esc(outlet?.name || '')}</h1>
  <div class="sub">Lihat menu dan pesan dari HP, tanpa antre</div>
  <img src="${qr}" alt="QR" />
  <div class="url">${esc(shortUrl)}</div>
  <div class="foot">Didukung ${esc(BRAND)}</div>
</div>
<script>window.onload=function(){setTimeout(function(){window.print()},250)}</script>
</body></html>`);
    w.document.close();
  };

  const toggleListed = async () => {
    if (!outlet) return;
    const next = !outlet.directory_listed;
    setSavingListed(true);
    const res = await updateOutlet(outlet.id, { directory_listed: next });
    setSavingListed(false);
    if (res?.success !== false) setOutlet((o: any) => ({ ...o, directory_listed: next }));
  };

  if (loading) {
    return <div className="flex min-h-[60vh] items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" /></div>;
  }
  if (!outlet?.slug) {
    return <div className="ks-card p-8 text-center text-[var(--text-muted)]">Outlet belum punya alamat toko. Lengkapi dulu di Pengaturan.</div>;
  }

  const checks: { ok: boolean; label: string; why: string; href: string }[] = [
    { ok: !!outlet.cover_image_url, label: 'Foto sampul toko', why: 'Tampil di kartu Jelajah dan pratinjau saat link dibagikan di WA.', href: '/dashboard/settings' },
    { ok: !!outlet.address, label: 'Alamat lengkap', why: 'Google memakai alamat untuk mencocokkan toko dengan pencarian "dekat saya".', href: '/dashboard/settings' },
    { ok: !!outlet.whatsapp_number, label: 'Nomor WhatsApp toko', why: 'Tombol chat di halaman toko dan nomor telepon di hasil pencarian.', href: '/dashboard/settings' },
    { ok: !!(outlet.latitude && outlet.longitude), label: 'Titik lokasi di peta', why: 'Koordinat dikirim ke Google dan dipakai untuk menghitung jarak antar.', href: '/dashboard/settings' },
    { ok: !!outlet.opening_hours, label: 'Jam buka', why: 'Tampil di halaman toko dan hasil pencarian.', href: '/dashboard/settings' },
    { ok: (productCount ?? 0) > 0, label: `Menu terisi${productCount != null ? ` (${productCount})` : ''}`, why: 'Toko tanpa menu tidak dimasukkan ke Jelajah dan sitemap.', href: '/dashboard/menu' },
  ];
  const done = checks.filter(c => c.ok).length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="ks-eyebrow">Toko Online</p>
          <h1 className="ks-display mt-1 text-[28px] font-extrabold text-[var(--text-strong)]">Supaya toko kamu ketemu</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Satu link untuk semua pintu masuk: stiker di kasir, bio Instagram, Google, dan struk.</p>
        </div>
        <a href={url} target="_blank" rel="noopener noreferrer" className="ks-btn ks-btn-outline ks-btn-sm">
          Buka halaman toko <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Kiri: link + QR */}
        <div className="space-y-6 lg:col-span-2">
          <div className="ks-card p-6">
            <label className="ks-field-label">Link toko</label>
            <div className="flex gap-2">
              <input readOnly value={url} className="ks-mono w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--surface-sunken)] px-3 py-2 text-sm text-[var(--text-body)] outline-none" />
              <button type="button" onClick={copy} className="ks-btn ks-btn-sm whitespace-nowrap" aria-label="Salin link">
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Tersalin' : 'Salin'}
              </button>
            </div>

            <div className="mt-5 flex flex-col items-center rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-white p-4">
              {qr ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={qr} alt={`QR ${outlet.name}`} className="h-56 w-56" />
              ) : (
                <div className="flex h-56 w-56 items-center justify-center text-sm text-[var(--text-muted)]">Membuat QR...</div>
              )}
              <p className="ks-mono mt-2 text-xs text-[var(--text-muted)]">{shortUrl}</p>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button type="button" onClick={downloadQr} className="ks-btn ks-btn-outline ks-btn-sm"><Download className="h-4 w-4" /> Unduh QR</button>
              <button type="button" onClick={printSticker} className="ks-btn ks-btn-outline ks-btn-sm"><Printer className="h-4 w-4" /> Cetak stiker</button>
              <button type="button" onClick={shareWa} className="ks-btn ks-btn-sm col-span-2"><Share2 className="h-4 w-4" /> Bagikan ke WhatsApp</button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--text-muted)]">
              Tempel stiker di meja kasir, pintu, dan tiap meja. Pelanggan scan, lihat menu, pesan dari HP sendiri.
            </p>
          </div>

          <div className="ks-card p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="flex items-center gap-2 font-semibold text-[var(--text-strong)]"><Globe className="h-4 w-4 text-[var(--brand-secondary)]" /> Tampil di Jelajah dan Google</p>
                <p className="mt-1 text-xs leading-relaxed text-[var(--text-muted)]">
                  Toko masuk halaman <Link href="/jelajah" target="_blank" className="font-semibold text-[var(--brand-secondary)] hover:underline">{BRAND} Jelajah</Link> dan peta situs yang dibaca Google. Matikan kalau usaha kamu tidak untuk umum.
                </p>
              </div>
              <button
                type="button"
                onClick={toggleListed}
                disabled={savingListed}
                role="switch"
                aria-checked={!!outlet.directory_listed}
                className="relative mt-1 h-7 w-12 flex-shrink-0 rounded-full transition-colors disabled:opacity-60"
                style={{ background: outlet.directory_listed ? 'var(--brand-secondary)' : 'var(--border-default)' }}
              >
                <span className="absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all" style={{ left: outlet.directory_listed ? 26 : 4 }} />
              </button>
            </div>
          </div>
        </div>

        {/* Kanan: daftar periksa + panduan */}
        <div className="space-y-6 lg:col-span-3">
          <div className="ks-card p-6">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-[var(--text-strong)]">Kelengkapan profil</p>
              <span className="text-sm text-[var(--text-muted)]">{done} dari {checks.length}</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-sunken)]">
              <div className="h-full rounded-full transition-all" style={{ width: `${(done / checks.length) * 100}%`, background: 'var(--brand-secondary)' }} />
            </div>
            <ul className="mt-4 divide-y divide-[var(--border-subtle)]">
              {checks.map(c => (
                <li key={c.label} className="flex items-start gap-3 py-3">
                  {c.ok
                    ? <CircleCheck className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--success)]" />
                    : <CircleAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--warning,#d97706)]" />}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--text-strong)]">{c.label}</p>
                    <p className="text-xs leading-relaxed text-[var(--text-muted)]">{c.why}</p>
                  </div>
                  {!c.ok && (
                    <Link href={c.href} className="mt-0.5 inline-flex items-center gap-0.5 text-xs font-semibold text-[var(--brand-secondary)] hover:underline">
                      Lengkapi <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="ks-card p-6">
            <p className="font-semibold text-[var(--text-strong)]">Pasang link ini di tempat orang mencari</p>
            <ol className="mt-4 space-y-4">
              <Step n={1} icon={<Search className="h-4 w-4" />} title="Google Business Profile (paling penting)">
                Buka <a href="https://business.google.com" target="_blank" rel="noopener noreferrer" className="font-semibold text-[var(--brand-secondary)] hover:underline">business.google.com</a>, klaim atau buat profil tokomu.
                Di bagian <b>Situs web</b> isi link toko di atas. Kalau ada pilihan <b>Pemesanan</b> atau <b>Menu</b>, isi link yang sama.
                Setelah itu tombol pesan muncul langsung di Google Maps dan hasil pencarian.
              </Step>
              <Step n={2} icon={<ImageIcon className="h-4 w-4" />} title="Bio Instagram dan TikTok">
                Tempel link toko di bio. Satu link cukup, tidak perlu layanan link tambahan.
              </Step>
              <Step n={3} icon={<MessageCircle className="h-4 w-4" />} title="WhatsApp Business">
                Di pengaturan profil bisnis, isi <b>Situs web</b> dengan link toko dan pakai link yang sama di pesan sapaan otomatis.
              </Step>
              <Step n={4} icon={<Printer className="h-4 w-4" />} title="Stiker di meja dan kasir">
                Cetak stiker dari tombol di kiri. Pelanggan yang sudah di tempat pun bisa pesan dari meja tanpa antre di kasir.
              </Step>
              <Step n={5} icon={<UtensilsCrossed className="h-4 w-4" />} title="Struk">
                Sudah otomatis. Tiap struk kertas dan struk WhatsApp membawa link toko, jadi pelanggan yang pernah datang bisa pesan lagi dari rumah.
              </Step>
            </ol>
            <div className="mt-5 rounded-[var(--radius-md)] bg-[var(--surface-sunken)] p-3 text-xs leading-relaxed text-[var(--text-muted)]">
              <Clock className="mr-1 inline h-3.5 w-3.5" />
              Google butuh sekitar 1 sampai 4 minggu untuk mengindeks halaman baru. Cara cek: ketik <span className="ks-mono">site:{shortUrl}</span> di Google.
              <MapPin className="ml-2 mr-1 inline h-3.5 w-3.5" />
              Lengkapi alamat dan titik lokasi supaya masuk pencarian "dekat saya".
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Step({ n, icon, title, children }: { n: number; icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold" style={{ background: 'var(--brand-tint-2)', color: 'var(--brand-secondary)' }}>{n}</span>
      <div className="min-w-0">
        <p className="flex items-center gap-1.5 text-sm font-semibold text-[var(--text-strong)]">{icon} {title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-muted)]">{children}</p>
      </div>
    </li>
  );
}
