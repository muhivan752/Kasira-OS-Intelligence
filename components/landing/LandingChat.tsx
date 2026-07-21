'use client';

import { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, Send, Loader2 } from 'lucide-react';

type Msg = { role: 'user' | 'assistant'; content: string };

const SUGGESTIONS = [
  { label: 'Kasira cocok buat warkop kecil?', text: 'Kasira cocok buat warkop kecil?' },
  { label: 'Bedanya sama Moka/Pawoon apa?', text: 'Bedanya Kasira sama Moka atau Pawoon apa?' },
  { label: 'QRIS beneran nol komisi?', text: 'QRIS-nya beneran nol komisi? Jelasin dong' },
  { label: 'Berapa harganya buat 1 cafe?', text: 'Berapa total biayanya buat 1 cafe kecil?' },
];

export default function LandingChat({ waLink }: { waLink: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function send(text: string) {
    const t = text.trim();
    if (!t || loading) return;

    const next: Msg[] = [...messages, { role: 'user', content: t }];
    setMessages(next);
    setDraft('');
    setLoading(true);

    try {
      const res = await fetch('/api/landing-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: next.map((m) => ({ role: m.role, content: m.content })) }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data?.reply || 'Hmm, coba tanya lagi ya.' },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Waduh, lagi ada gangguan. Boleh lanjut tanya via WhatsApp ya 🙏' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Tombol pemicu */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Tanya Kasira"
          className="fixed bottom-5 right-5 z-[120] flex items-center gap-2.5 rounded-full bg-[#0B1512] py-3.5 pl-4 pr-5 text-white shadow-[0_18px_40px_-12px_rgba(11,21,18,0.55)] transition hover:scale-[1.03] active:scale-95"
        >
          <span className="relative flex h-7 w-7 items-center justify-center rounded-full bg-[#10B981]">
            <MessageCircle className="h-4 w-4 text-[#04231A]" />
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-[#0B1512] bg-[#34D399]" />
          </span>
          <span className="text-[14.5px] font-semibold">Tanya Kasira</span>
        </button>
      )}

      {/* Panel */}
      {open && (
        <div className="fixed inset-x-3 bottom-3 z-[120] flex max-h-[min(560px,85vh)] flex-col overflow-hidden rounded-2xl border border-[#E7E5DE] bg-white shadow-[0_30px_80px_-24px_rgba(11,21,18,0.45)] sm:inset-x-auto sm:right-5 sm:bottom-5 sm:w-[380px]">
          <header className="flex items-center gap-3 border-b border-[#EAE8E1] bg-[#0B1512] px-4 py-3.5 text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#10B981] text-[15px] font-extrabold text-[#04231A]">
              k
            </span>
            <div className="flex-1">
              <p className="text-[14.5px] font-bold leading-tight">Tanya Kasira</p>
              <p className="flex items-center gap-1.5 text-[11.5px] text-[#8CA095]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#34D399]" />
                Biasanya bales instan
              </p>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Tutup" className="rounded-lg p-1.5 text-[#8CA095] transition hover:bg-white/10 hover:text-white">
              <X className="h-4.5 w-4.5" />
            </button>
          </header>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto bg-[#FAFAF7] px-4 py-4">
            {messages.length === 0 && (
              <>
                <div className="max-w-[85%] rounded-[16px_16px_16px_4px] border border-[#E7E5DE] bg-white px-3.5 py-2.5 text-[14px] leading-relaxed text-[#0B1512]">
                  Hai! 👋 Aku bantu jelasin Kasira buat cafe kamu.
                  <br />
                  Tanya apa aja — fitur, harga, cara mulai. Atau pilih di bawah:
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s.label}
                      onClick={() => send(s.text)}
                      className="rounded-full border border-[#E7E5DE] bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#3F4A45] transition hover:border-[#059669] hover:text-[#059669]"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </>
            )}

            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <div
                  className={
                    m.role === 'user'
                      ? 'max-w-[85%] whitespace-pre-wrap rounded-[16px_16px_4px_16px] bg-[#0B1512] px-3.5 py-2.5 text-[14px] leading-relaxed text-white'
                      : 'max-w-[85%] whitespace-pre-wrap rounded-[16px_16px_16px_4px] border border-[#E7E5DE] bg-white px-3.5 py-2.5 text-[14px] leading-relaxed text-[#0B1512]'
                  }
                >
                  {m.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-[16px_16px_16px_4px] border border-[#E7E5DE] bg-white px-3.5 py-2.5 text-[13.5px] text-[#8A938D]">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  lagi ngetik…
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-[#EAE8E1] bg-white px-3 py-3">
            <div className="flex items-center gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && send(draft)}
                maxLength={500}
                placeholder="Tanya soal Kasira…"
                className="min-w-0 flex-1 rounded-xl border border-[#E7E5DE] bg-[#FAFAF7] px-3.5 py-2.5 text-[14px] text-[#0B1512] outline-none transition placeholder:text-[#A8B0AA] focus:border-[#059669]"
              />
              <button
                onClick={() => send(draft)}
                disabled={loading || !draft.trim()}
                aria-label="Kirim"
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#059669] text-white transition disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 text-center text-[11px] text-[#A8B0AA]">
              Jawaban AI bisa meleset —{' '}
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="font-semibold text-[#059669] underline underline-offset-2">
                tanya orangnya via WhatsApp
              </a>
            </p>
          </div>
        </div>
      )}
    </>
  );
}
