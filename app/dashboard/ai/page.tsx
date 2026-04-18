'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Bot, Send, Trash2, Loader2, AlertCircle, CheckCircle2, FlaskConical } from 'lucide-react';
import { useProGuard } from '@/app/hooks/use-pro-guard';

interface ProposalIngredient {
  name: string;
  qty: number;
  unit: string;
  buy_price: number;
  buy_qty: number;
}

interface RecipeProposal {
  product_name: string;
  ingredients: ProposalIngredient[];
  hpp_estimate?: number;
  suggested_price_range?: [number, number];
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'system';
  content: string;
  intent?: string;
  model?: string;
  tokens?: number;
  recipeProposal?: RecipeProposal;
  proposalApplied?: boolean;
  proposalError?: string;
}

const SUGGESTIONS = [
  'Setup resep Kopi Susu Gula Aren',
  'Bikin resep Es Matcha Latte',
  'Berapa omzet hari ini?',
  'Stok apa yang perlu diisi?',
];

const RECIPE_PROPOSAL_REGEX = /<RECIPE_PROPOSAL>([\s\S]*?)<\/RECIPE_PROPOSAL>/;

function parseRecipeProposal(content: string): { proposal: RecipeProposal | null; cleaned: string } {
  const match = content.match(RECIPE_PROPOSAL_REGEX);
  if (!match) return { proposal: null, cleaned: content };
  try {
    const proposal = JSON.parse(match[1].trim()) as RecipeProposal;
    const cleaned = content.replace(RECIPE_PROPOSAL_REGEX, '').trim();
    return { proposal, cleaned };
  } catch {
    return { proposal: null, cleaned: content };
  }
}

const rp = (n: number) => `Rp ${Math.round(n).toLocaleString('id-ID')}`;

export default function AIChatPage() {
  const allowed = useProGuard('AI Asisten');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [outletId, setOutletId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadOutlet = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch('/api/ai/outlet', { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        if (data.outlet_id) {
          setOutletId(data.outlet_id);
          return data.outlet_id;
        }
      }
    } catch {}
    return null;
  }, []);

  useEffect(() => {
    loadOutlet();
  }, [loadOutlet]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    // Lazy-fetch outletId kalau belum ada (initial load race / session lama)
    let effectiveOutletId = outletId;
    if (!effectiveOutletId) {
      effectiveOutletId = await loadOutlet();
      if (!effectiveOutletId) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'error',
          content: 'Outlet belum teridentifikasi. Coba logout & login ulang.',
        }]);
        return;
      }
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setError('');

    const assistantId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '' }]);

    try {
      const res = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text.trim(), outlet_id: effectiveOutletId }),
      });

      if (res.status === 403) {
        setMessages(prev => prev.filter(m => m.id !== assistantId));
        setMessages(prev => [...prev, {
          id: assistantId,
          role: 'error',
          content: 'Fitur AI Chatbot hanya tersedia untuk paket Pro. Upgrade untuk mengakses.',
        }]);
        setLoading(false);
        return;
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No reader');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr);

            if (event.type === 'chunk') {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.content }
                    : m
                )
              );
            } else if (event.type === 'done') {
              setMessages(prev =>
                prev.map(m => {
                  if (m.id !== assistantId) return m;
                  const { proposal, cleaned } = parseRecipeProposal(m.content);
                  return {
                    ...m,
                    content: proposal ? cleaned : m.content,
                    intent: event.intent,
                    model: event.model,
                    tokens: event.tokens_used,
                    recipeProposal: proposal || undefined,
                  };
                })
              );
            } else if (event.type === 'error') {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, role: 'error', content: event.message }
                    : m
                )
              );
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err: any) {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, role: 'error', content: 'Gagal terhubung ke AI. Periksa koneksi internet Anda.' }
            : m
        )
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [loading, outletId, loadOutlet]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const clearChat = () => {
    setMessages([]);
    setError('');
  };

  const applyProposal = useCallback(async (messageId: string, proposal: RecipeProposal) => {
    let effectiveOutletId = outletId;
    if (!effectiveOutletId) {
      effectiveOutletId = await loadOutlet();
      if (!effectiveOutletId) return;
    }

    setMessages(prev =>
      prev.map(m => (m.id === messageId ? { ...m, proposalError: undefined } : m))
    );

    try {
      const res = await fetch('/api/ai/apply-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          outlet_id: effectiveOutletId,
          product_name: proposal.product_name,
          ingredients: proposal.ingredients.map(i => ({
            name: i.name,
            qty: i.qty,
            unit: i.unit,
            buy_price: i.buy_price,
            buy_qty: i.buy_qty,
          })),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail || data.error || 'Gagal membuat resep.';
        setMessages(prev =>
          prev.map(m => (m.id === messageId ? { ...m, proposalError: detail } : m))
        );
        return;
      }

      const d = data.data || {};
      const lines = [
        `✅ Resep **${d.product_name}** berhasil dibuat.`,
        '',
        `HPP: **${rp(d.hpp)}**` +
          (d.product_base_price ? ` · Harga jual: ${rp(d.product_base_price)}` : '') +
          (typeof d.margin_pct === 'number' ? ` · Margin: **${d.margin_pct}%**` : ''),
      ];
      if (d.created_ingredients?.length) {
        lines.push('', `Bahan baru dibuat: ${d.created_ingredients.map((i: any) => i.name).join(', ')}`);
      }
      if (d.reused_ingredients?.length) {
        lines.push(`Bahan yang udah ada (dipakai ulang): ${d.reused_ingredients.map((i: any) => i.name).join(', ')}`);
      }

      setMessages(prev => [
        ...prev.map(m => (m.id === messageId ? { ...m, proposalApplied: true } : m)),
        {
          id: (Date.now() + 10).toString(),
          role: 'system',
          content: lines.join('\n'),
        },
      ]);
    } catch {
      setMessages(prev =>
        prev.map(m => (m.id === messageId ? { ...m, proposalError: 'Gagal terhubung ke server.' } : m))
      );
    }
  }, [outletId, loadOutlet]);

  if (!allowed) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] lg:h-[calc(100vh-6rem)] max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
            <Bot className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">AI Asisten</h1>
            <p className="text-xs text-gray-500">Tanya laporan & insight bisnis kamu</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Hapus Chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-xl bg-white border border-gray-200 p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-purple-50 rounded-2xl flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-purple-400" />
            </div>
            <h2 className="text-lg font-semibold text-gray-700 mb-1">Halo! Ada yang bisa dibantu?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-sm">
              Saya bisa bantu analisa penjualan, cek stok, dan kasih insight bisnis kamu.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="px-3 py-2 text-sm bg-gray-50 hover:bg-purple-50 text-gray-600 hover:text-purple-700 rounded-lg border border-gray-200 hover:border-purple-200 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-purple-600 text-white'
                  : msg.role === 'error'
                  ? 'bg-red-50 text-red-700 border border-red-200'
                  : msg.role === 'system'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {msg.role === 'error' && (
                <div className="flex items-center gap-1.5 mb-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span className="text-xs font-medium">Error</span>
                </div>
              )}
              {msg.role === 'system' && (
                <div className="flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span className="text-xs font-medium">Berhasil</span>
                </div>
              )}
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>

              {msg.recipeProposal && (
                <div className="mt-3 rounded-xl border border-purple-200 bg-white p-3 space-y-3">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-purple-600" />
                    <p className="text-sm font-semibold text-gray-900">
                      {msg.recipeProposal.product_name}
                    </p>
                  </div>
                  <div className="space-y-1 text-xs text-gray-700">
                    {msg.recipeProposal.ingredients.map((ing, idx) => {
                      const costPerPorsi = (ing.buy_price / ing.buy_qty) * ing.qty;
                      return (
                        <div key={idx} className="flex justify-between items-baseline gap-2">
                          <span><span className="font-medium">{ing.name}</span> <span className="text-gray-500">{ing.qty}{ing.unit}</span></span>
                          <span className="text-gray-500 whitespace-nowrap">≈ {rp(costPerPorsi)}</span>
                        </div>
                      );
                    })}
                  </div>
                  {msg.recipeProposal.hpp_estimate && (
                    <div className="flex justify-between text-xs pt-2 border-t border-gray-100">
                      <span className="text-gray-500">HPP total</span>
                      <span className="font-semibold text-gray-900">{rp(msg.recipeProposal.hpp_estimate)}</span>
                    </div>
                  )}
                  {msg.proposalError && (
                    <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-2 py-1.5">
                      {msg.proposalError}
                    </p>
                  )}
                  {msg.proposalApplied ? (
                    <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 rounded-lg px-2 py-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Resep sudah dibuat</span>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        onClick={() => applyProposal(msg.id, msg.recipeProposal!)}
                        className="flex-1 px-3 py-2 text-xs font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        Buat Otomatis
                      </button>
                      <button
                        onClick={() => sendMessage(`Ubah resep ${msg.recipeProposal!.product_name} — `)}
                        className="px-3 py-2 text-xs font-medium text-purple-700 bg-white border border-purple-200 rounded-lg hover:bg-purple-50 transition-colors"
                      >
                        Ubah Dulu
                      </button>
                    </div>
                  )}
                </div>
              )}

              {msg.role === 'assistant' && msg.content && !loading && msg.tokens !== undefined && (
                <p className="text-[10px] text-gray-400 mt-2">
                  {msg.model?.includes('haiku') ? 'Haiku' : 'Sonnet'} &middot; {msg.tokens} tokens
                </p>
              )}
              {msg.role === 'assistant' && msg.content === '' && loading && (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                  <span className="text-sm text-gray-400">Mengetik...</span>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ketik pertanyaan..."
          disabled={loading}
          className="flex-1 px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:hover:bg-purple-600 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
