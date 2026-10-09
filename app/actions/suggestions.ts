'use server';

import { cookies } from 'next/headers';

// Saran Selaris (backend/services/suggestions.py). Pola sama dengan actions/accounts.ts.
export type SuggestionResult<T = any> = { success: true; data: T } | { success: false; message: string };
const base = (process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');

async function call(path: string, method = 'GET', body?: unknown): Promise<SuggestionResult> {
  const jar = await cookies();
  const token = jar.get('token')?.value;
  if (!token) return { success: false, message: 'Sesi berakhir. Masuk kembali.' };
  try {
    const result = await fetch(`${base}${path}`, { method, cache: 'no-store', signal: AbortSignal.timeout(20000),
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'X-Tenant-ID': jar.get('tenant_id')?.value || '' },
      ...(body ? { body: JSON.stringify(body) } : {}) });
    const value = await result.json();
    if (!result.ok) return { success: false, message: typeof value.detail === 'string' ? value.detail
      : value.detail?.message || 'Permintaan gagal. Coba lagi.' };
    return { success: true, data: value.data };
  } catch {
    return { success: false, message: method === 'GET' ? 'Saran belum dapat dimuat.' : 'Hasil belum pasti. Muat ulang saran sebelum mencoba lagi.' };
  }
}

export async function getSuggestions(outletId: string) { return call(`/suggestions?outlet_id=${encodeURIComponent(outletId)}`); }
export async function applySuggestion(id: string, params?: { new_price?: number; qty?: number }) {
  return call(`/suggestions/${encodeURIComponent(id)}/apply`, 'POST', params || {});
}
export async function skipSuggestion(id: string, reason: string) { return call(`/suggestions/${encodeURIComponent(id)}/skip`, 'POST', { reason }); }
export async function undoSuggestion(id: string) { return call(`/suggestions/${encodeURIComponent(id)}/undo`, 'POST'); }
export async function refreshSuggestions(outletId: string) { return call('/suggestions/refresh', 'POST', { outlet_id: outletId }); }
