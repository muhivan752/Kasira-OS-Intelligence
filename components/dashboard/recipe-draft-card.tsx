'use client';

import Link from 'next/link';
import { useState } from 'react';
import { approveHppChat } from '@/app/actions/api';

// Kartu draf resep dari alat susun_resep Selaris AI (backend/services/selaris_agent.py).
// Modal dan biaya per bahan dihitung mesin HPP; penyimpanan lewat approve HPP yang sama
// dengan menu Atur bahan (izin, sidik draf, dan kunci baris tetap di backend).
export type RecipeDraft = {
  session_id: string; revision: number; fingerprint?: string | null; ready: boolean; replaces_recipe: boolean;
  product: string; new_product: boolean; total_cost: number | null; base_price: number | null; margin: number | null;
  lines: { bahan: string; takaran: string | null; satuan: string; biaya: number | null; perkiraan: boolean }[];
  missing: string[];
};

const rp = (n: number | null | undefined) => 'Rp ' + Math.round(Number(n) || 0).toLocaleString('id-ID');

export function RecipeDraftCard({ draft, outletId }: { draft: RecipeDraft; outletId?: string | null }) {
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [error, setError] = useState('');
  const [replace, setReplace] = useState(false);
  const edit = `/dashboard/hpp/chat?conversation=${encodeURIComponent(draft.session_id)}`;

  async function save() {
    if (!draft.fingerprint || state !== 'idle') return;
    setState('saving'); setError('');
    const res = await approveHppChat(draft.session_id, draft.revision, draft.fingerprint, replace, outletId || undefined);
    if (res.success) { setState('saved'); return; }
    setState('idle'); setError(res.message);
  }

  return <section className="saran-card mt-3" aria-label={`Draf resep ${draft.product}`}>
    <span className="saran-tag saran-brand">{draft.new_product ? 'Draf resep, produk baru' : 'Draf resep'}</span>
    <p className="saran-prop">{draft.product}</p>
    {draft.lines.length > 0 && <ul className="saran-rows">{draft.lines.map((l, i) => <li key={i}>
      <span>{l.bahan}<em className={l.perkiraan ? 'saran-est' : 'saran-fact'}>{l.perkiraan ? 'perkiraan' : 'harga toko'}</em></span>
      <span className="saran-num">{l.takaran ?? '?'} {l.satuan}{l.biaya != null ? ` · ${rp(l.biaya)}` : ''}</span>
    </li>)}</ul>}
    {draft.total_cost != null && <div className="saran-chips">
      <span className="saran-chip">Modal per porsi {rp(draft.total_cost)}</span>
      {draft.margin != null && <span className={`saran-chip ${draft.margin >= 30 ? 'saran-chip-good' : 'saran-chip-bad'}`}>Margin {draft.margin.toLocaleString('id-ID')}% dari harga {rp(draft.base_price)}</span>}
    </div>}
    {!draft.ready && draft.missing.length > 0 && <p className="saran-note">Belum lengkap: {draft.missing.join(' ')}</p>}
    <p className="saran-note">Takaran berlabel perkiraan adalah usulan umum. Modal dihitung dari harga bahan toko.</p>
    {draft.replaces_recipe && state !== 'saved' && <label className="saran-note flex items-center gap-2">
      <input type="checkbox" checked={replace} onChange={e => setReplace(e.target.checked)} /> Ganti resep lama produk ini
    </label>}
    {error && <p className="saran-error" role="alert">{error}</p>}
    {state === 'saved'
      ? <p className="saran-notice" role="status">Resep {draft.product} tersimpan. Modal dan stoknya sekarang terhitung.</p>
      : <div className="saran-acts">
          {draft.ready && <button type="button" className="saran-btn saran-primary" disabled={state === 'saving' || (draft.replaces_recipe && !replace)} onClick={save}>
            {state === 'saving' ? 'Menyimpan…' : 'Simpan resep'}</button>}
          <Link className="saran-btn inline-flex items-center" href={edit}>{draft.ready ? 'Ubah' : 'Lengkapi'}</Link>
        </div>}
  </section>;
}
