'use client';

import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import Link from 'next/link';
import { ArrowUp, History, Plus, X } from 'lucide-react';
import { approveHppChat, createHppChat, getHppChat, listHppChats, sendHppChat } from '@/app/actions/api';
import { useProGuard } from '@/app/hooks/use-pro-guard';
import type { HppChatMode, HppChatSession, HppChatListItem } from '@/lib/hpp-chat';
import { hppMoney } from '@/lib/hpp';
import { HppReview } from './review';

export function HppChat({ initialProduct, initialOutlet }: { initialProduct: string; initialOutlet?: string }) {
  const allowed = useProGuard('Setup HPP lewat percakapan');
  const [list, setList] = useState<HppChatListItem[]>([]);
  const [session, setSession] = useState<HppChatSession | null>(null);
  const [mode, setMode] = useState<HppChatMode>('estimate');
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirmed, setConfirmed] = useState(false);
  const [replacing, setReplacing] = useState(false);
  const [sendingText, setSendingText] = useState('');
  const [panel, setPanel] = useState<'history' | 'recipe' | null>(null);
  const lock = useRef(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const nearEnd = useRef(true);
  const startingProduct = useRef(initialProduct);
  const preview = session?.preview;
  const waiting = !!session?.pending;

  function scrollToLatest() {
    if (history.current && nearEnd.current) history.current.scrollTop = history.current.scrollHeight;
  }
  useEffect(scrollToLatest, [session?.id, session?.revision, session?.turns.length, sendingText, waiting]);
  useEffect(() => {
    const element = history.current;
    if (!element) return;
    const observer = new ResizeObserver(scrollToLatest);
    observer.observe(element);
    return () => observer.disconnect();
  }, [loading, session?.id]);

  useEffect(() => {
    const element = input.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = Math.min(element.scrollHeight, 160) + 'px';
  }, [text, loading, session?.status]);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (panel && !element.open) element.showModal();
    if (!panel && element.open) {
      element.close();
      returnFocus.current?.focus();
    }
  }, [panel]);

  function openPanel(next: 'history' | 'recipe') {
    returnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setPanel(next);
  }
  function trapFocus(event: KeyboardEvent<HTMLDialogElement>) {
    if (event.key !== 'Tab') return;
    const items = [...event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), summary, select:not(:disabled), textarea:not(:disabled)')]
      .filter(element => element.getClientRects().length > 0);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  function receive(data: HppChatSession) {
    setSession(data); setMode(data.mode); setConfirmed(false); setReplacing(false);
    try {
      const key = 'hpp-chat-request:' + data.id;
      const pending = JSON.parse(localStorage.getItem(key) || 'null');
      const stored = pending && data.turns.find(turn => turn.id === pending.request_id);
      if (stored) {
        if (localStorage.getItem('hpp-chat-input:' + data.id) === pending.message) {
          localStorage.removeItem('hpp-chat-input:' + data.id); setText('');
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
    const result = await listHppChats(initialOutlet);
    if (result.success) setList(result.data); else setError(result.message);
  }
  useEffect(() => {
    if (!allowed) return;
    let active = true;
    (async () => {
      try {
        const result = await listHppChats(initialOutlet);
        if (!active) return;
        if (result.success) setList(result.data); else setError(result.message);
        const id = new URL(window.location.href).searchParams.get('conversation');
        if (id) {
          const chat = await getHppChat(id, initialOutlet);
          if (!active) return;
          if (chat.success) receive(chat.data); else setError(chat.message);
        }
      } catch { if (active) setError('Obrolan belum bisa dimuat. Coba lagi.'); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [allowed]);
  useEffect(() => {
    nearEnd.current = true;
    if (!session) return;
    try { setText(localStorage.getItem('hpp-chat-input:' + session.id) || ''); } catch {}
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
          const result = await getHppChat(id, initialOutlet);
          if (stopped) return;
          if (result.success) { receive(result.data); if (!result.data.pending) return; }
          else setError(result.message);
        } catch { if (!stopped) setError('Jawaban belum bisa diperiksa. Coba muat ulang obrolan.'); }
      }
      if (!stopped) timer = setTimeout(poll, 2500);
    }
    timer = setTimeout(poll, 2500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [allowed, session?.id, session?.pending]);

  function changeText(value: string) {
    setText(value); setConfirmed(false);
    if (session) try { localStorage.setItem('hpp-chat-input:' + session.id, value); } catch {}
  }
  async function run(work: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try { await work(); }
    catch { setError('Koneksi terputus. Periksa obrolan terbaru sebelum mencoba lagi.'); }
    finally { lock.current = false; setBusy(false); setSendingText(''); }
  }
  async function refresh() {
    await run(async () => {
      if (session) {
        const result = await getHppChat(session.id, initialOutlet);
        if (result.success) receive(result.data); else setError(result.message);
      }
      await reloadList();
    });
  }
  async function choose(id: string) {
    if (text.trim() && !window.confirm('Masih ada pesan yang belum dikirim. Pindah obrolan?')) return;
    await run(async () => {
      nearEnd.current = true;
      if (!id) {
        setSession(null); setMode('estimate'); setText(''); setConfirmed(false); setReplacing(false);
        startingProduct.current = ''; setPanel(null);
        return;
      }
      const result = await getHppChat(id, initialOutlet);
      if (result.success) { receive(result.data); setPanel(null); } else setError(result.message);
    });
  }
  async function send(retry = false, assistance = false) {
    const unanswered = session?.turns.slice().reverse().find(turn => !turn.reply);
    const content = retry ? unanswered?.message : assistance ? 'Bantu lengkapi estimasi resep ini. Isi perkiraan takaran dan harga yang masih kosong, lalu betulkan satuan estimasi yang belum cocok. Pertahankan data nyata, pilihan bahan, dan koreksi yang sudah aku ceritakan.' : text;
    const selectedMode = assistance ? 'estimate' : mode;
    if (assistance && text.trim()) return;
    if (!content?.trim() || lock.current || (waiting && !retry)) return;
    await run(async () => {
      nearEnd.current = true; setSendingText(retry ? '' : content);
      let chat = session;
      if (!chat) {
        const created = await createHppChat(selectedMode, startingProduct.current, initialOutlet);
        if (!created.success) { setError(created.message); return; }
        chat = created.data; receive(chat);
        try { localStorage.setItem('hpp-chat-input:' + chat.id, content); } catch {}
      }
      const key = 'hpp-chat-request:' + chat.id;
      let requestId = retry ? unanswered?.id : undefined;
      if (!requestId) {
        try {
          const cached = JSON.parse(localStorage.getItem(key) || 'null');
          if (cached?.message === content && cached?.mode === selectedMode && cached?.revision === chat.revision) requestId = cached.request_id;
        } catch {}
      }
      requestId ||= crypto.randomUUID();
      const payload = { request_id: requestId, revision: chat.revision,
        mode: retry && unanswered ? unanswered.mode : selectedMode, message: content };
      try { localStorage.setItem(key, JSON.stringify(payload)); } catch {}
      const result = await sendHppChat(chat.id, payload, initialOutlet);
      if (!result.success) { setError(result.message); return; }
      receive(result.data);
      if (result.data.turns.some(turn => turn.id === requestId)) {
        if (!retry || text === content) setText('');
        try {
          if (!retry || text === content) localStorage.removeItem('hpp-chat-input:' + chat.id);
          if (result.data.turns.some(turn => turn.id === requestId && turn.reply)) localStorage.removeItem(key);
        } catch {}
      }
      await reloadList();
    });
  }
  async function approve() {
    if (!session || session.can_approve === false || !preview || !confirmed || text.trim() || (preview.replaces_recipe && !replacing)) return;
    await run(async () => {
      const result = await approveHppChat(session.id, session.revision, preview.fingerprint, replacing, initialOutlet);
      if (result.success) { receive(result.data); setPanel(null); nearEnd.current = true; await reloadList(); }
      else setError(result.message);
    });
  }

  const problem = error || session?.error;
  const recovery = <div className="hpp-chat-error" role="alert">
    <p>{problem}</p>
    {error.includes('Sesi') ? <Link className="hpp-button" href="/login">Masuk kembali</Link>
      : <button className="hpp-button" disabled={busy} onClick={() => void refresh()}>Periksa percakapan</button>}
  </div>;

  return <div className="hpp-workspace hpp-chat">
    <header className="hpp-chat-toolbar">
      <div className="min-w-0"><h1>Resep &amp; HPP</h1><p>{preview?.product_name || 'Asisten resep'}</p></div>
      <div className="hpp-chat-tools">
        <button className="hpp-chat-tool" aria-label="Riwayat obrolan" disabled={busy || loading} onClick={() => openPanel('history')}><History size={19} /><span>Riwayat</span></button>
        <button className="hpp-chat-tool" aria-label="Resep baru" disabled={busy || loading} onClick={() => void choose('')}><Plus size={21} /><span className="hpp-chat-new-label">Resep baru</span></button>
      </div>
    </header>
    {!allowed || loading ? <p className="hpp-chat-loading" role="status">Memuat obrolan...</p> : <>
      <div ref={history} role="log" aria-label="Riwayat setup HPP" className="hpp-chat-history"
        onScroll={event => { const el = event.currentTarget; nearEnd.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; }}>
        <div className="hpp-chat-messages">
          {!session?.turns.length && !sendingText && <div className="hpp-chat-welcome">
            <h2>Mau cek bahan atau bikin resep?</h2><p>{mode === 'estimate' ? 'Tanya bahan dan resep yang ada di toko, atau sebutkan menu yang mau diestimasikan.' : 'Tanya isi toko, atau ceritakan bahan, takaran, dan harga yang kamu pakai.'}</p>
          </div>}
          {session?.turns.map(turn => <div key={turn.id} className="hpp-chat-turn">
            <article className="hpp-chat-message hpp-chat-user" aria-label="Pesan Anda"><p>{turn.message}</p></article>
            {turn.reply && <article className="hpp-chat-message hpp-chat-assistant" aria-label="Jawaban asisten"><p>{turn.reply}</p></article>}
          </div>)}
          {sendingText && !session?.turns.some(turn => turn.message === sendingText && !turn.reply) &&
            <article className="hpp-chat-message hpp-chat-user" aria-label="Pesan sedang dikirim"><p>{sendingText}</p></article>}
          {(waiting || sendingText) && <p className="hpp-chat-processing" role="status">Menyiapkan jawaban...</p>}
          {preview && <section className="hpp-chat-recipe" aria-label="Ringkasan resep">
            <div><p className="hpp-chat-recipe-state">{session?.status === 'applied' ? 'Resep tersimpan' : preview.is_estimated ? 'Estimasi HPP per porsi' : 'HPP per porsi'}</p>
              <h2>{preview.product_name}</h2></div>
            <p className="hpp-chat-price" data-testid="hpp-chat-total">{preview.total_cost !== null ? hppMoney(Number(preview.total_cost)) : 'Belum lengkap'}</p>
            <p className="hpp-chat-recipe-meta">{preview.lines.filter(line => !line.is_optional).length} bahan utama · {preview.servings || '?'} porsi{waiting && ' · Draft sebelumnya'}</p>
            <button className="hpp-button" onClick={() => openPanel('recipe')}>Lihat resep</button>
            {!preview.ready && session?.status !== 'applied' && <button className="hpp-button hpp-primary ml-2" disabled={busy || waiting || !!text.trim()} onClick={() => void send(false, true)}>Lengkapi estimasi</button>}
          </section>}
          {session?.status === 'applied' && <div className="hpp-chat-saved" role="status">
            <p>Bahan dan resep sudah tersimpan.</p>
            {session.result?.new_product && <p>Menu baru masih nonaktif. Atur harga jualnya dulu di Menu.</p>}
            <div className="hpp-chat-saved-links">
              <Link className="hpp-button" href={'/dashboard/hpp?product=' + session.result?.product_id}>Lihat resep tersimpan</Link>
              <Link className="hpp-button" href="/dashboard/bahan-baku">Catat stok bahan</Link>
              {session.result?.new_product && <Link className="hpp-button" href="/dashboard/menu">Atur menu baru</Link>}
            </div>
          </div>}
          {problem && !panel && recovery}
          {session?.retry_allowed && session.turns.some(turn => !turn.reply) &&
            <button className="hpp-button" disabled={busy} onClick={() => void send(true)}>Proses ulang pesan terakhir</button>}
        </div>
      </div>
      <form className="hpp-chat-composer" onSubmit={event => { event.preventDefault(); void send(); }}>
        <label className="sr-only" htmlFor="hpp-chat-message">Tulis pesan</label>
        <textarea ref={input} id="hpp-chat-message" className="hpp-control" rows={1} disabled={busy}
          value={text} onChange={event => changeText(event.target.value)} placeholder="Tulis pesan..."
          aria-describedby="hpp-chat-keyboard" onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !busy && !waiting) {
              event.preventDefault(); void send();
            }
          }} />
        <div className="hpp-chat-composer-bottom">
          <fieldset className="hpp-chat-modes" disabled={busy || waiting}><legend className="sr-only">Cara menyiapkan resep</legend>
            <label className="hpp-chat-mode"><input type="radio" name="hpp-mode" checked={mode === 'manual'} onChange={() => { setMode('manual'); setConfirmed(false); }} /><span>Manual</span></label>
            <label className="hpp-chat-mode"><input type="radio" name="hpp-mode" checked={mode === 'estimate'} onChange={() => { setMode('estimate'); setConfirmed(false); }} /><span>Estimasi</span></label>
          </fieldset>
          <button className="hpp-button hpp-primary hpp-chat-send" aria-label="Kirim pesan" type="submit" disabled={busy || waiting || !text.trim()}><ArrowUp size={21} /></button>
        </div>
        <p className="sr-only" id="hpp-chat-keyboard">Enter untuk kirim. Shift+Enter untuk baris baru.</p>
      </form>
    </>}
    <dialog ref={dialog} className={'hpp-chat-dialog' + (panel === 'history' ? ' hpp-chat-dialog-history' : '')}
      aria-labelledby="hpp-chat-panel-title" onCancel={() => setPanel(null)} onClose={() => setPanel(null)} onKeyDown={trapFocus}>
      <header className="hpp-chat-dialog-header"><h2 id="hpp-chat-panel-title">{panel === 'history' ? 'Riwayat obrolan' : preview?.product_name || 'Resep'}</h2>
        <button autoFocus className="hpp-chat-tool" aria-label="Tutup panel" onClick={() => setPanel(null)}><X size={21} /></button></header>
      <div className="hpp-chat-dialog-body">
        {problem && recovery}
        {panel === 'history' ? <div className="hpp-chat-session-list">
          <button className="hpp-button" disabled={busy} onClick={() => void refresh()}>Periksa percakapan</button>
          {!list.length && <p>Belum ada obrolan tersimpan. Mulai dari satu menu.</p>}
          {list.map(item => <button className="hpp-chat-session" key={item.id} disabled={busy} aria-current={session?.id === item.id ? 'true' : undefined}
            onClick={() => void choose(item.id)}><span>{item.name}</span><small>{item.status === 'applied' ? 'Tersimpan' : 'Draft'}</small></button>)}
          <Link className="hpp-button" href="/dashboard/hpp">Isi resep dengan form</Link>
        </div> : preview && session && <HppReview session={session} preview={preview} busy={busy} hasUnsent={!!text.trim()} hasError={!!problem}
          confirmed={confirmed} replacing={replacing} onConfirmed={setConfirmed} onReplacing={setReplacing} onApprove={() => void approve()} />}
      </div>
    </dialog>
  </div>;
}
