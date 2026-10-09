'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

type Outlet = { id: string; name: string };
type Message = { role: 'user' | 'assistant'; content: string };

export function ScopedAIChat() {
  const [outlets, setOutlets] = useState<Outlet[]>([]), [outletId, setOutletId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]), [text, setText] = useState('');
  const [busy, setBusy] = useState(false), [loading, setLoading] = useState(true), [error, setError] = useState('');
  const [conversation, setConversation] = useState<string>(), [canDraft, setCanDraft] = useState(false);
  const request = useRef<AbortController | null>(null), revision = useRef(0);
  const history = useRef<HTMLDivElement>(null), input = useRef<HTMLTextAreaElement>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    void fetch('/api/ai/outlet', { cache: 'no-store' }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Akses AI belum dapat dimuat.');
      if (active) { setOutlets(data.outlets); setOutletId(data.outlet_id); setCanDraft(data.can_draft); }
    }).catch(error => { if (active) setError(error.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; revision.current++; request.current?.abort(); };
  }, [reload]);
  useEffect(() => { if (history.current) history.current.scrollTop = history.current.scrollHeight; }, [messages, busy]);

  function clear() {
    revision.current++; request.current?.abort(); setMessages([]); setConversation(undefined); setError(''); setBusy(false);
  }
  async function send() {
    if (!text.trim() || busy || !outletId) return;
    const current = ++revision.current, content = text.trim();
    const controller = new AbortController(); request.current = controller;
    setMessages(value => [...value, { role: 'user', content }]); setText(''); setError(''); setBusy(true);
    try {
      const response = await fetch('/api/ai', { method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: content, outlet_id: outletId, conversation_id: conversation }) });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || 'Pesan belum dapat diproses. Coba lagi.');
      }
      const reader = response.body?.getReader();
      if (!reader) throw new Error('Jawaban belum dapat dibaca. Coba lagi.');
      const decoder = new TextDecoder(); let pending = '', answer = '', failure = '', nextConversation;
      function consume(event: string) {
        const line = event.split('\n').find(value => value.startsWith('data: '));
        if (!line) return;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === 'chunk') answer += payload.content || '';
        if (payload.type === 'error') failure = payload.message;
        if (payload.type === 'done') nextConversation = payload.conversation_id;
      }
      while (true) {
        const result = await reader.read();
        pending += decoder.decode(result.value || new Uint8Array(), { stream: !result.done });
        const events = pending.split('\n\n'); pending = events.pop() || '';
        for (const event of events) consume(event);
        if (result.done) break;
      }
      if (pending.trim()) consume(pending);
      if (failure) throw new Error(failure);
      if (!answer) throw new Error('Jawaban belum tersedia. Coba lagi.');
      if (current === revision.current) { setMessages(value => [...value, { role: 'assistant', content: answer }]); setConversation(nextConversation); }
    } catch (error) {
      if (current === revision.current && !controller.signal.aborted) setError(error instanceof Error ? error.message : 'Koneksi terputus. Coba lagi.');
    } finally { if (current === revision.current) { setBusy(false); input.current?.focus(); } }
  }

  return <div className="hpp-workspace space-y-5 max-w-3xl">
    <header className="space-y-2"><h1 className="text-2xl font-semibold">Selaris AI</h1><p>Tanyakan data yang sesuai akses akun. Perubahan dicatat lewat halaman modulnya.</p></header>
    {loading ? <p role="status">Memuat outlet dan akses AI…</p> : <>
      {outlets.length > 0 && <div className="flex flex-wrap items-end gap-3"><label className="flex-1 min-w-0">Outlet<select className="hpp-control w-full" aria-label="Outlet AI" value={outletId} disabled={busy} onChange={event => { clear(); setOutletId(event.target.value); }}>{outlets.map(outlet => <option key={outlet.id} value={outlet.id}>{outlet.name}</option>)}</select></label><button className="hpp-button" disabled={busy || !messages.length} onClick={clear}>Percakapan baru</button></div>}
      <div ref={history} role="log" aria-label="Percakapan AI" className="hpp-panel space-y-4 max-h-[55vh] overflow-y-auto">
        {!messages.length && <p>Belum ada percakapan. Tulis pertanyaan untuk outlet yang dipilih.</p>}
        {messages.map((message, index) => <article key={index} className="space-y-1"><h2 className="font-semibold">{message.role === 'user' ? 'Anda' : 'Asisten'}</h2><p className="whitespace-pre-wrap break-words">{message.content}</p></article>)}
        {busy && <p role="status">Menyiapkan jawaban…</p>}
      </div>
      {error && <div className="space-y-2"><p role="alert">{error}</p>{!outlets.length && <button className="hpp-button" onClick={() => setReload(value => value + 1)}>Muat ulang akses AI</button>}</div>}
      {!!outlets.length && <form className="space-y-3" onSubmit={event => { event.preventDefault(); void send(); }}><label htmlFor="scoped-ai-message">Pertanyaan Anda</label><textarea ref={input} id="scoped-ai-message" className="hpp-control w-full" rows={3} value={text} disabled={busy} maxLength={100000} onChange={event => setText(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send(); } }} /><div className="flex flex-wrap gap-3"><button className="hpp-button hpp-primary" disabled={busy || !text.trim()} type="submit">Kirim pertanyaan</button>{canDraft && <Link className="hpp-button" href={`/dashboard/hpp/chat?outlet=${outletId}`}>Susun draft HPP</Link>}</div></form>}
    </>}
  </div>;
}
