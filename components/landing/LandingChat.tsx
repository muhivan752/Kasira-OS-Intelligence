'use client';

import { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';

type Msg = { role: 'user' | 'assistant'; content: string };
const suggestions = ['Apa perbedaan Starter dan Pro?', 'Bagaimana mengelola stok bahan?', 'Bagaimana memasang aplikasi kasir?'];

export default function LandingChat({ waLink }: { waLink: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const sessionId = useRef('');
  const panel = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const scroll = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    panel.current?.querySelector<HTMLInputElement>('input')?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); }
    };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [open]);
  useEffect(() => { scroll.current?.scrollTo({ top: scroll.current.scrollHeight }); }, [messages, loading, error]);

  async function send(text: string) {
    const value = text.trim();
    if (!value || loading) return;
    if (!sessionId.current) sessionId.current = crypto.randomUUID();
    const next: Msg[] = [...messages, { role: 'user', content: value }];
    setMessages(next); setDraft(''); setLoading(true); setError('');
    try {
      const response = await fetch('/api/landing-chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId.current, messages: next }),
      });
      const data = await response.json();
      if (!response.ok || !data.reply) throw new Error('chat unavailable');
      setMessages(previous => [...previous, { role: 'assistant', content: data.reply }]);
    } catch { setError('Jawaban belum tersedia. Coba kirim kembali atau hubungi tim melalui WhatsApp.'); setDraft(value); }
    finally { setLoading(false); }
  }

  return <>
    <button ref={trigger} type="button" aria-expanded={open} aria-controls="landing-chat" aria-label="Tanya Selaris"
      onClick={() => setOpen(!open)} className="chat-trigger"><MessageCircle size={19} /><span>Tanya Selaris</span></button>
    {open && <aside ref={panel} id="landing-chat" className="chat-panel" aria-label="Asisten Selaris">
      <header><div><h2>Tanya Selaris</h2><p>Asisten untuk fitur dan paket usaha</p></div>
        <button type="button" aria-label="Tutup" onClick={() => { setOpen(false); trigger.current?.focus(); }}><X size={20} /></button></header>
      <div ref={scroll} className="chat-messages" aria-live="polite">
        {messages.length === 0 && <><p>Pilih pertanyaan atau tulis kebutuhan toko Anda.</p>
          <div className="chat-suggestions">{suggestions.map(text => <button type="button" key={text} onClick={() => send(text)}>{text}</button>)}</div></>}
        {messages.map((message, index) => <p className={`chat-message ${message.role}`} key={index}>{message.content}</p>)}
        {loading && <p role="status">Menyiapkan jawaban…</p>}
        {error && <p role="alert" className="chat-error">{error}</p>}
      </div>
      <form onSubmit={event => { event.preventDefault(); send(draft); }}>
        <label className="sr-only" htmlFor="chat-question">Pertanyaan untuk Selaris</label>
        <div><input id="chat-question" value={draft} onChange={event => setDraft(event.target.value)} maxLength={2000} placeholder="Tanya soal Selaris…" />
          <button type="submit" aria-label="Kirim" disabled={loading || !draft.trim()}><Send size={18} /></button></div>
        <p>Jawaban asisten perlu diperiksa. <a href={waLink} target="_blank" rel="noopener noreferrer">Hubungi tim Selaris</a></p>
      </form>
    </aside>}
  </>;
}
