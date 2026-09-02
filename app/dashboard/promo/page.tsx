'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MessageCircle, Send, Loader2, AlertTriangle, CheckCircle2, Users, Trash2, RefreshCw, Sparkles } from 'lucide-react';
import { getOutlets } from '@/app/actions/api';
import { getSegmentSummary, getTags, getCampaigns, previewCampaign, createCampaign, sendCampaign, deleteCampaign, refreshSegments } from '@/app/actions/crm';

interface Segment { key: string; label: string; hint: string; count: number; reachable: number }
interface Tag { id: string; name: string; color: string; count: number }
interface Campaign { id: string; name: string; template: string; target: string; status: string; recipient_count: number; sent_count: number; failed_count: number; started_at?: string | null; finished_at?: string | null; created_at: string }

const TEMPLATES = [
  { label: 'Kangen', text: 'Halo {nama}! Udah lama nggak mampir ke {toko} 😊 Minggu ini ada diskon 10% buat kamu — tunjukin pesan ini ke kasir ya.' },
  { label: 'Menu baru', text: 'Halo {nama}, {toko} punya menu baru nih! Mampir yuk, cobain duluan sebelum yang lain 🙌' },
  { label: 'Terima kasih', text: 'Makasih udah jadi pelanggan setia {toko}, {nama}! Sebagai apresiasi, kunjungan berikutnya dapet gratis 1 minuman.' },
];

const STATUS: Record<string, { label: string; cls: string }> = {
  draft: { label: 'Draft', cls: 'bg-gray-100 text-gray-600' },
  sending: { label: 'Mengirim…', cls: 'bg-blue-100 text-blue-700' },
  done: { label: 'Terkirim', cls: 'bg-green-100 text-green-700' },
  failed: { label: 'Gagal', cls: 'bg-red-100 text-red-700' },
};

const tgl = (iso?: string | null) => iso ? new Date(iso).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—';

export default function PromoPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState('');
  const [waConnected, setWaConnected] = useState(false);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [toast, setToast] = useState<{ ok: boolean; text: string } | null>(null);

  // form
  const [name, setName] = useState('');
  // ?target=segment:hilang dari halaman Pelanggan. Dibaca di effect, bukan
  // useSearchParams: hook itu maksa Suspense boundary waktu build statis.
  const [target, setTarget] = useState('all');
  const [template, setTemplate] = useState(TEMPLATES[0].text);
  const [preview, setPreview] = useState<{ recipient_count: number; sample: { name: string; phone: string }[]; wa_connected: boolean; rendered_example: string } | null>(null);
  const [busy, setBusy] = useState<'preview' | 'send' | ''>('');

  const showToast = (ok: boolean, text: string) => { setToast({ ok, text }); setTimeout(() => setToast(null), ok ? 4000 : 8000); };

  const reload = async (oid = outletId) => {
    const [s, t, c] = await Promise.all([getSegmentSummary(), getTags(), oid ? getCampaigns(oid) : Promise.resolve([])]);
    setSegments(s); setTags(t); setCampaigns(c);
  };

  useEffect(() => {
    try { const t = new URLSearchParams(window.location.search).get('target'); if (t) setTarget(t); } catch {}
    (async () => {
      try {
        const outlets = await getOutlets();
        if (!outlets?.length) return;
        setOutletId(outlets[0].id); setWaConnected(!!outlets[0].wa_connected);
        await reload(outlets[0].id);
      } finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // polling ringan waktu ada campaign yang lagi ngirim
  useEffect(() => {
    if (!campaigns.some(c => c.status === 'sending')) return;
    const t = setInterval(() => reload(), 4000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaigns]);

  const doPreview = async () => {
    setBusy('preview'); setPreview(null);
    try { setPreview(await previewCampaign({ outlet_id: outletId, name: name || 'Promo', template, target })); }
    catch (e: any) { showToast(false, e.message); }
    finally { setBusy(''); }
  };

  const doSend = async () => {
    if (!preview) return;
    if (!confirm(`Kirim ke ${preview.recipient_count} pelanggan dari nomor WA toko sekarang?`)) return;
    setBusy('send');
    try {
      const c = await createCampaign({ outlet_id: outletId, name: name.trim() || `Promo ${new Date().toLocaleDateString('id-ID')}`, template, target });
      const r = await sendCampaign(c.id);
      showToast(true, r.message); setPreview(null); setName('');
      await reload();
    } catch (e: any) { showToast(false, e.message); }
    finally { setBusy(''); }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-500">Memuat...</div>;
  if (!outletId) return <div className="bg-white rounded-xl border p-8 text-center text-gray-500">Belum ada outlet.</div>;

  const reachableTotal = segments.reduce((s, x) => s + x.reachable, 0);
  const targetLabel = target === 'all' ? 'Semua yang setuju' : target.startsWith('segment:') ? (segments.find(s => `segment:${s.key}` === target)?.label || target) : (tags.find(t => `tag:${t.id}` === target)?.name || target);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Promo WhatsApp</h1>
        <p className="text-gray-500">Kirim pesan ke pelanggan dari nomor WA toko kamu sendiri. Hanya ke yang udah setuju dikirimi promo.</p>
      </div>

      {toast && (
        <div className={`rounded-lg px-4 py-3 text-sm flex items-start gap-2 border ${toast.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
          {toast.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />}<span>{toast.text}</span>
        </div>
      )}

      {!waConnected && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-2"><MessageCircle className="w-4 h-4" /> WhatsApp toko belum tersambung — promo belum bisa dikirim.</span>
          <Link href="/dashboard/settings" className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700">Sambungkan di Pengaturan</Link>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        {/* Form */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
          <div>
            <label className="text-xs font-semibold text-gray-500">Kirim ke siapa</label>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <button onClick={() => setTarget('all')} className={`px-3 py-1.5 rounded-full text-sm border ${target === 'all' ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-gray-200 text-gray-700'}`}>Semua yang setuju <span className="opacity-70">({reachableTotal})</span></button>
              {segments.filter(s => s.count > 0).map(s => (
                <button key={s.key} onClick={() => setTarget(`segment:${s.key}`)} title={s.hint} className={`px-3 py-1.5 rounded-full text-sm border ${target === `segment:${s.key}` ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-gray-200 text-gray-700'}`}>
                  {s.label} <span className="opacity-70">({s.reachable}/{s.count})</span>
                </button>
              ))}
              {tags.filter(t => t.count > 0).map(t => (
                <button key={t.id} onClick={() => setTarget(`tag:${t.id}`)} className={`px-3 py-1.5 rounded-full text-sm border ${target === `tag:${t.id}` ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-gray-200 text-gray-700'}`}>#{t.name} <span className="opacity-70">({t.count})</span></button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-gray-400">Angka (bisa dikirimi / total). Segmen dihitung otomatis dari transaksi. <button onClick={async () => { try { const r = await refreshSegments(); showToast(true, r.message); await reload(); } catch (e: any) { showToast(false, e.message); } }} className="text-blue-600 hover:underline inline-flex items-center gap-1"><RefreshCw className="w-3 h-3" /> hitung ulang</button></p>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-500">Nama promo (buat catatan kamu)</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="mis. Promo kangen September" className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-gray-500">Isi pesan</label>
              <div className="flex gap-1">
                {TEMPLATES.map(t => <button key={t.label} onClick={() => setTemplate(t.text)} className="text-xs px-2 py-1 rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200">{t.label}</button>)}
              </div>
            </div>
            <textarea value={template} onChange={e => setTemplate(e.target.value)} rows={5} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            <p className="text-xs text-gray-400 mt-1">Pakai <code className="bg-gray-100 px-1 rounded">{'{nama}'}</code> dan <code className="bg-gray-100 px-1 rounded">{'{toko}'}</code>. Baris "Balas STOP untuk berhenti" ditambahin otomatis.</p>
          </div>

          <div className="flex gap-2">
            <button onClick={doPreview} disabled={busy !== '' || template.trim().length < 5} className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 flex items-center justify-center gap-2">
              {busy === 'preview' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Users className="w-4 h-4" />} Cek penerima & contoh
            </button>
            <button onClick={doSend} disabled={!preview || preview.recipient_count === 0 || !preview.wa_connected || busy !== ''} className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {busy === 'send' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Kirim ke {preview ? preview.recipient_count : '…'}
            </button>
          </div>
        </div>

        {/* Preview */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5">
          <h2 className="font-bold text-gray-900 flex items-center gap-2"><Sparkles className="w-4 h-4 text-blue-500" /> Contoh yang diterima pelanggan</h2>
          {!preview ? (
            <p className="mt-3 text-sm text-gray-500">Klik "Cek penerima & contoh" dulu. Kamu lihat berapa orang yang bakal dapet dan pesannya jadi seperti apa.</p>
          ) : (
            <div className="mt-3 space-y-3">
              <div className="rounded-2xl rounded-tl-sm bg-[#DCF8C6] px-4 py-3 text-sm text-gray-900 whitespace-pre-wrap max-w-[340px]">{preview.rendered_example}</div>
              <div className="text-sm text-gray-600">
                <p><b className="text-gray-900">{preview.recipient_count} pelanggan</b> di "{targetLabel}" bakal dapet pesan ini.</p>
                {preview.sample.length > 0 && <p className="text-xs text-gray-400 mt-1">Contoh: {preview.sample.map(s => `${s.name} (${s.phone})`).join(', ')}</p>}
                {preview.recipient_count === 0 && <p className="text-xs text-amber-700 mt-2">Belum ada yang setuju dikirimi promo di target ini. Centang "setuju promo" di profil pelanggan, atau minta izin waktu kirim struk WA.</p>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Riwayat */}
      <div className="bg-white rounded-2xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-bold text-gray-900">Riwayat promo</h2>
          <span className="text-sm text-gray-500">{campaigns.length}</span>
        </div>
        {campaigns.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">Belum ada promo terkirim.</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {campaigns.map(c => {
              const st = STATUS[c.status] || STATUS.draft;
              return (
                <div key={c.id} className="px-5 py-3 flex items-center gap-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-900 truncate">{c.name} <span className={`ml-2 text-[11px] font-semibold px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span></p>
                    <p className="text-xs text-gray-500 truncate">{tgl(c.started_at || c.created_at)} · {c.sent_count}/{c.recipient_count} terkirim{c.failed_count ? ` · ${c.failed_count} gagal` : ''} · {c.template.slice(0, 60)}{c.template.length > 60 ? '…' : ''}</p>
                  </div>
                  {c.status !== 'sending' && (
                    <button onClick={async () => { if (!confirm('Hapus dari riwayat?')) return; try { await deleteCampaign(c.id); await reload(); } catch (e: any) { showToast(false, e.message); } }} className="p-2 text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
