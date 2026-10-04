'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { approveHppChat, createHppChat, getHppChat, listHppChats, sendHppChat } from '@/app/actions/api';
import { useProGuard } from '@/app/hooks/use-pro-guard';
import type { HppChatMode, HppChatSession, HppChatListItem } from '@/lib/hpp-chat';
import { hppMoney, hppNumber } from '@/lib/hpp';

const labels: Record<string, string> = { user: 'Dari cerita Anda', estimate: 'Estimasi', existing: 'Data bahan toko', unknown: 'Belum diisi' };
const actions = { create: 'Bahan baru', reuse: 'Pakai bahan toko', update_price: 'Ubah harga bahan toko' };
const format = (value: string | null) => value === null ? 'Belum diisi' : hppNumber(Number(value));
const formatCost = (value: string) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: 8 }).format(Number(value));

export function HppChat({ initialProduct }: { initialProduct: string }) {
  const allowed = useProGuard('Setup HPP lewat percakapan');
  const [list, setList] = useState<HppChatListItem[]>([]);
  const [session, setSession] = useState<HppChatSession | null>(null);
  const [mode, setMode] = useState<HppChatMode>('manual');
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirmed, setConfirmed] = useState(false);
  const [replacing, setReplacing] = useState(false);
  const lock = useRef(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const startingProduct = useRef(initialProduct);
  const preview = session?.preview;

  useEffect(() => {
    if (history.current) history.current.scrollTop = history.current.scrollHeight;
  }, [session?.id, session?.revision, session?.turns.length]);

  useEffect(() => {
    const element = history.current;
    if (!element) return;
    const observer = new ResizeObserver(() => { element.scrollTop = element.scrollHeight; });
    observer.observe(element);
    return () => observer.disconnect();
  }, [loading, session?.id]);

  function receive(data: HppChatSession) {
    setSession(data); setMode(data.mode); setConfirmed(false); setReplacing(false);
    try {
      const key = `hpp-chat-request:${data.id}`;
      const pending = JSON.parse(localStorage.getItem(key) || 'null');
      const stored = pending && data.turns.find(turn => turn.id === pending.request_id);
      if (stored) {
        if (localStorage.getItem(`hpp-chat-input:${data.id}`) === pending.message) {
          localStorage.removeItem(`hpp-chat-input:${data.id}`); setText('');
        }
        if (stored.reply) localStorage.removeItem(key);
      }
    } catch {}
  }

  useEffect(() => {
    if (loading || busy) return;
    const url = new URL(window.location.href);
    if (session) url.searchParams.set('conversation', session.id);
    else url.searchParams.delete('conversation');
    if (url.href !== window.location.href) window.history.replaceState(null, '', url);
  }, [session?.id, loading, busy]);

  async function reloadList() {
    const result = await listHppChats();
    if (result.success) setList(result.data); else setError(result.message);
  }

  useEffect(() => {
    if (!allowed) return;
    let active = true;
    (async () => {
      try {
        const result = await listHppChats();
        if (!active) return;
        if (result.success) setList(result.data); else setError(result.message);
        const id = new URL(window.location.href).searchParams.get('conversation');
        if (id) {
          const chat = await getHppChat(id);
          if (!active) return;
          if (chat.success) receive(chat.data); else setError(chat.message);
        }
      } catch { if (active) setError('Percakapan belum bisa dimuat. Coba lagi.'); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [allowed]);

  useEffect(() => {
    if (!session) return;
    try { setText(localStorage.getItem(`hpp-chat-input:${session.id}`) || ''); } catch {}
  }, [session?.id]);

  useEffect(() => {
    if (!allowed || !session?.pending) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const id = session.id;
    async function poll() {
      if (stopped) return;
      if (!lock.current) {
        try {
          const result = await getHppChat(id);
          if (stopped) return;
          if (result.success) { receive(result.data); if (!result.data.pending) return; }
          else setError(result.message);
        } catch { if (!stopped) setError('Percakapan belum bisa diperiksa. Tekan Periksa percakapan untuk mencoba lagi.'); }
      }
      if (!stopped) timer = setTimeout(poll, 2500);
    }
    timer = setTimeout(poll, 2500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [allowed, session?.id, session?.pending]);

  function changeText(value: string) {
    setText(value); setConfirmed(false);
    if (session) try { localStorage.setItem(`hpp-chat-input:${session.id}`, value); } catch {}
  }

  async function run(work: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try { await work(); }
    catch { setError('Koneksi terputus. Periksa percakapan terbaru sebelum mencoba lagi.'); }
    finally { lock.current = false; setBusy(false); }
  }

  async function refresh() {
    await run(async () => {
      if (session) {
        const result = await getHppChat(session.id);
        if (result.success) receive(result.data); else setError(result.message);
      }
      await reloadList();
    });
  }

  async function choose(id: string) {
    if (text.trim() && !window.confirm('Teks yang belum dikirim tetap disimpan di percakapan ini. Buka percakapan lain?')) return;
    await run(async () => {
      if (!id) { setSession(null); setText(''); setConfirmed(false); setReplacing(false);
        startingProduct.current = '';
        return; }
      const result = await getHppChat(id);
      if (result.success) receive(result.data); else setError(result.message);
    });
  }

  async function send(retry = false) {
    const unanswered = session?.turns.slice().reverse().find(turn => !turn.reply);
    const content = retry ? unanswered?.message : text;
    if (!content?.trim()) return;
    await run(async () => {
      let chat = session;
      if (!chat) {
        const created = await createHppChat(mode, startingProduct.current);
        if (!created.success) { setError(created.message); return; }
        chat = created.data; receive(chat);
        try { localStorage.setItem(`hpp-chat-input:${chat.id}`, content); } catch {}
      }
      const key = `hpp-chat-request:${chat.id}`;
      let requestId = retry ? unanswered?.id : undefined;
      if (!requestId) {
        try {
          const cached = JSON.parse(localStorage.getItem(key) || 'null');
          if (cached?.message === content && cached?.mode === mode && cached?.revision === chat.revision) requestId = cached.request_id;
        } catch {}
      }
      requestId ||= crypto.randomUUID();
      const payload = { request_id: requestId, revision: chat.revision,
        mode: retry && unanswered ? unanswered.mode : mode, message: content };
      try { localStorage.setItem(key, JSON.stringify(payload)); } catch {}
      const result = await sendHppChat(chat.id, payload);
      if (!result.success) { setError(result.message); return; }
      receive(result.data);
      if (result.data.turns.some(turn => turn.id === requestId)) {
        setText('');
        try {
          localStorage.removeItem(`hpp-chat-input:${chat.id}`);
          if (result.data.turns.some(turn => turn.id === requestId && turn.reply)) localStorage.removeItem(key);
        } catch {}
      }
      await reloadList();
      end.current?.scrollIntoView({ block: 'nearest' });
      input.current?.focus();
    });
  }

  async function approve() {
    if (!session || !preview || !confirmed || text.trim() || (preview.replaces_recipe && !replacing)) return;
    await run(async () => {
      const result = await approveHppChat(session.id, session.revision, preview.fingerprint, replacing);
      if (result.success) { receive(result.data); await reloadList(); }
      else setError(result.message);
    });
  }

  return <div className="hpp-workspace hpp-chat space-y-6 max-w-6xl">
    <header className="space-y-2"><h1 className="text-2xl sm:text-3xl font-semibold">Siapkan HPP lewat percakapan</h1>
      <p className="max-w-2xl text-muted">Ceritakan menu, bahan, dan cara Anda membuatnya. Periksa draft sebelum menyimpan bahan dan resep.</p>
      <Link className="hpp-button hpp-text-button" href="/dashboard/hpp">Isi resep dengan form</Link></header>
    {!allowed || loading ? <p role="status">Memuat percakapan...</p> : <>
      <div className="flex flex-wrap items-end gap-3"><div className="flex-1 min-w-0 max-w-xl"><label className="block mb-1 font-semibold" htmlFor="hpp-conversation">Percakapan tersimpan</label>
        <select id="hpp-conversation" className="hpp-control w-full" disabled={busy} value={session?.id || ''} onChange={event => void choose(event.target.value)}>
          <option value="">Resep baru</option>{session && !list.some(item => item.id === session.id) && <option value={session.id}>Percakapan ini</option>}
          {list.map(item => <option key={item.id} value={item.id}>{item.name}{item.status === 'applied' ? ' · Sudah disetujui' : ' · Draft'}</option>)}</select></div>
        <button className="hpp-button" disabled={busy} onClick={() => void refresh()}>Periksa percakapan</button>
        {session && <button className="hpp-button" disabled={busy} onClick={() => void choose('')}>Resep baru</button>}</div>
      {error && <div role="alert" className="hpp-panel space-y-2"><p>{error}</p>{error.includes('Sesi') && <Link className="hpp-button" href="/login">Masuk kembali</Link>}</div>}
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <section className="min-w-0 space-y-5" aria-labelledby="hpp-chat-heading"><h2 id="hpp-chat-heading" className="font-semibold text-xl">Percakapan</h2>
          <div ref={history} role="log" aria-label="Riwayat setup HPP" className="hpp-chat-history space-y-5">
            {!session?.turns.length && <p className="text-muted">Mulai dari satu menu. Sebutkan bahan yang Anda tahu; harga dan takaran bisa dilengkapi sambil jalan.</p>}
            {session?.turns.map(turn => <article key={turn.id} className="space-y-3"><div className="border-l-2 border-[var(--control-border)] pl-4"><p className="font-semibold mb-1">Anda</p><p className="whitespace-pre-wrap break-words">{turn.message}</p></div>
              {turn.reply && <div className="pl-4"><p className="font-semibold mb-1">Asisten resep</p><p className="whitespace-pre-wrap break-words">{turn.reply}</p></div>}</article>)}
            <div ref={end} /></div>
          {session?.status === 'applied' ? <div className="hpp-panel space-y-3" role="status"><p className="font-semibold">Bahan dan resep sudah tersimpan.</p>
            <p>Stok fisik dicatat melalui Bahan Baku. {session.result?.new_product && 'Menu baru masih nonaktif; atur harga jual dan aktifkan melalui Menu.'}</p>
            <Link className="hpp-button" href={`/dashboard/hpp?product=${session.result?.product_id}`}>Lihat resep tersimpan</Link>
            <Link className="hpp-button" href="/dashboard/bahan-baku">Catat stok bahan</Link>{session.result?.new_product && <Link className="hpp-button" href="/dashboard/menu">Atur menu baru</Link>}</div>
            : <form className="space-y-4 border-t border-[var(--border-default)] pt-5" onSubmit={event => { event.preventDefault(); void send(); }}>
              <fieldset disabled={busy || !!session?.pending} className="space-y-2"><legend className="font-semibold mb-2">Cara menyiapkan data</legend>
                <label className="hpp-chat-choice"><input type="radio" name="hpp-mode" checked={mode === 'manual'} onChange={() => { setMode('manual'); setConfirmed(false); }} /><span><strong>Manual</strong><span className="block text-sm text-muted">Gunakan harga dan takaran nyata dari cerita Anda.</span></span></label>
                <label className="hpp-chat-choice"><input type="radio" name="hpp-mode" checked={mode === 'estimate'} onChange={() => { setMode('estimate'); setConfirmed(false); }} /><span><strong>Estimasi</strong><span className="block text-sm text-muted">Minta usulan untuk data yang belum Anda tahu. Bisa dikoreksi sebelum approve.</span></span></label></fieldset>
              <div><label className="block font-semibold mb-2" htmlFor="hpp-chat-message">Cerita atau koreksi Anda</label>
                <textarea ref={input} id="hpp-chat-message" className="hpp-control w-full min-h-36" disabled={busy || !!session?.pending} value={text} onChange={event => changeText(event.target.value)}
                  placeholder="Saya mau membuat nasi ayam penyet. Bahannya ayam, nasi, tempe, sambal..." />
                <p className="mt-2 text-sm text-muted">Boleh bercerita panjang. Sebutkan apakah takaran untuk satu porsi atau satu batch.</p></div>
              <button className="hpp-button hpp-primary" disabled={busy || !!session?.pending || !text.trim()} type="submit">{busy ? 'Menyiapkan draft...' : 'Kirim cerita'}</button>
              {(busy || session?.pending) && <p role="status" className="text-sm">Pesan sedang diproses. Percakapan disimpan agar bisa dilanjutkan.</p>}
              {session?.error && <p role="alert">{session.error}</p>}
              {session?.retry_allowed && session.turns.some(turn => !turn.reply) && <button type="button" className="hpp-button" disabled={busy} onClick={() => void send(true)}>Proses ulang pesan terakhir</button>}
            </form>}
        </section>
        <aside className="hpp-panel min-w-0 space-y-5 self-start lg:sticky lg:top-24" aria-labelledby="hpp-draft-heading">
          <div><h2 id="hpp-draft-heading" className="text-xl font-semibold">{preview?.product_name || 'Draft resep'}</h2>
            <p className="mt-1 text-sm text-muted">{session ? `Revisi ${session.revision}` : 'Belum ada draft'} · Perhitungan sistem</p>
            <p className="mt-4 text-sm font-semibold">{preview?.is_estimated ? 'Estimasi HPP bahan per porsi' : 'HPP bahan per porsi'}</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums" data-testid="hpp-chat-total">{preview?.total_cost ? hppMoney(Number(preview.total_cost)) : 'Belum lengkap'}</p>
            <p className="mt-2 text-sm text-muted">Belum termasuk gas, gaji, sewa, dan biaya operasional lainnya.</p></div>
          {!preview ? <p className="text-muted">Bahan, takaran, dan sumber harga akan muncul setelah cerita Anda diproses.</p> : <>
            <p className="text-sm">Resep untuk {format(preview.servings)} porsi. Jumlah porsi: {labels[preview.servings_source]}.</p>
            {preview.notes && <p className="text-sm">Catatan resep: {preview.notes}</p>}
            {preview.new_product && <p className="text-sm">Akan membuat menu baru dalam keadaan nonaktif. Atur harga jual melalui Menu setelah approve.</p>}
            <ol className="divide-y divide-[var(--border-default)]">{preview.lines.map((line, index) => <li key={index} className="py-4 space-y-2">
              <div className="flex justify-between gap-3 flex-wrap"><h3 className="font-semibold">{line.name}{line.is_optional && ' (opsional)'}</h3><span>{line.line_cost === null ? 'Belum lengkap' : hppMoney(Number(line.line_cost))}</span></div>
              <p className="text-sm">{actions[line.action]} · {format(line.quantity)} {line.unit} per porsi</p>
              {line.basis === 'batch' && <p className="text-sm text-muted">Dari {format(line.input_quantity)} {line.input_unit} per batch, dibagi {format(preview.servings)} porsi.</p>}
              <p className="text-sm">Takaran: {labels[line.quantity_source]}. Harga: {labels[line.price_source]}.</p>
              <p className="text-sm text-muted">Biaya satuan: {line.unit_cost === null ? 'Belum diisi' : `${formatCost(line.unit_cost)} Rp/${line.unit}`}.</p>
              {line.old_unit_cost !== null && <p className="text-sm">Sebelumnya {formatCost(line.old_unit_cost)} Rp/{line.unit}.</p>}
              {line.action !== 'reuse' && line.buy_price !== null && <p className="text-sm">Pembelian: {hppMoney(Number(line.buy_price))} untuk {format(line.buy_qty)} {line.unit}.</p>}
              {line.purchase_description && <p className="text-sm text-muted">Dari {line.purchase_description}.</p>}
              {line.affected_products.length > 0 && <p className="text-sm">Harga baru juga mengubah HPP: {line.affected_products.join(', ')}.</p>}
              {line.notes && <p className="text-sm text-muted">{line.notes}</p>}
              {(line.quantity_evidence || line.price_evidence) && <details className="text-sm"><summary className="hpp-chat-evidence">Lihat sumber dari cerita</summary><p className="whitespace-pre-wrap break-words mt-2">{[line.quantity_evidence, line.price_evidence].filter(Boolean).join('\n')}</p></details>}
            </li>)}</ol>
            {preview.missing.length > 0 && <div className="space-y-2"><h3 className="font-semibold">Masih perlu dilengkapi</h3><ul className="list-disc pl-5 text-sm space-y-2">{preview.missing.map((item, index) => <li key={index}>{item}</li>)}</ul><p className="text-sm text-muted">Jawab atau koreksi melalui percakapan.</p></div>}
            <details className="text-sm"><summary className="hpp-chat-evidence">Lihat rumus HPP</summary><p className="mt-2">Biaya satuan = total harga beli ÷ jumlah beli dalam satuan bahan. Biaya bahan = takaran per porsi × biaya satuan. HPP = jumlah biaya bahan wajib. Takaran batch dibagi jumlah porsi. Biaya satuan disimpan hingga 8 desimal; total tampilan dibulatkan ke 2 desimal.</p></details>
            {session?.status !== 'applied' && <div className="space-y-3 border-t border-[var(--border-default)] pt-4">
              {preview.is_estimated && <p className="text-sm">Harga atau takaran estimasi perlu diperiksa. Setelah approve, resep tetap diberi label estimasi.</p>}
              <label className="hpp-chat-choice"><input type="checkbox" checked={confirmed} disabled={busy || !preview.ready || !!session?.pending || !!session?.error || !!text.trim()} onChange={event => setConfirmed(event.target.checked)} /><span>Saya sudah memeriksa bahan, harga, takaran, dan jumlah porsi pada revisi ini.</span></label>
              {preview.replaces_recipe && <label className="hpp-chat-choice"><input type="checkbox" checked={replacing} disabled={busy} onChange={event => setReplacing(event.target.checked)} /><span>Ganti resep aktif produk ini dengan draft di atas.</span></label>}
              <button className="hpp-button hpp-primary w-full" disabled={busy || !preview.ready || !confirmed || !!session?.pending || !!session?.error || !!text.trim() || (preview.replaces_recipe && !replacing)} onClick={() => void approve()}>{busy ? 'Memproses...' : preview.replaces_recipe ? 'Approve dan ganti resep' : 'Approve dan simpan resep'}</button>
              {!!text.trim() && <p className="text-sm">Kirim koreksi yang belum diproses sebelum approve.</p>}
              <p className="text-sm text-muted">Persetujuan menyimpan bahan dan resep. Stok fisik dan mode stok diatur melalui halaman masing-masing.</p>
            </div>}
          </>}
        </aside>
      </div>
    </>}
  </div>;
}
