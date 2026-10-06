'use server';

import { cookies } from 'next/headers';
import type { HrisResult, HrFilters, HrSetup, HrWorkspace, HrPending } from '@/lib/hris';

async function call<T>(path: string, method = 'GET', payload?: unknown): Promise<HrisResult<T>> {
  const write = method !== 'GET';
  try {
    const jar = await cookies(); const token = jar.get('token')?.value;
    if (!token) return { success: false, message: 'Sesi berakhir. Masuk kembali untuk membuka tim dan absensi.' };
    const base = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const response = await fetch(`${base}/hris${path}`, { method, cache: 'no-store', signal: AbortSignal.timeout(15000), headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'X-Tenant-ID': jar.get('tenant_id')?.value || '' }, body: payload ? JSON.stringify(payload) : undefined });
    const body = await response.json();
    if (!response.ok || body.success !== true || body.data == null) {
      const message = response.status === 401 ? 'Sesi berakhir. Masuk kembali.' : response.status >= 500
        ? write ? 'Hasil penyimpanan belum pasti. Periksa permintaan yang sama.' : 'Data tim belum bisa dimuat. Coba lagi.'
        : typeof body.detail === 'string' ? body.detail : Array.isArray(body.detail) ? body.detail.map((v: { msg: string }) => v.msg).join('. ')
        : typeof body.detail?.message === 'string' ? body.detail.message : body.message || 'Data belum bisa diproses.';
      return { success: false, message, uncertain: write && response.status >= 500 };
    }
    return { success: true, data: body.data as T, message: body.message };
  } catch { return { success: false, uncertain: write, message: write ? 'Koneksi terputus. Hasil penyimpanan belum pasti; periksa permintaan yang sama.' : 'Data tim belum bisa dimuat. Periksa koneksi lalu coba lagi.' }; }
}
export async function getHrSetup() { return call<HrSetup>('/setup'); }
export async function checkHrRequest(request: HrPending) {
  if (!/^[0-9a-f-]{36}$/.test(request.payload.client_request_id)) return { success: false as const, message: 'Permintaan belum valid' };
  const setup = await getHrSetup();
  if (!setup.success) return setup;
  if (request.workspace_key !== setup.data.workspace_key) return { success: false as const, message: 'Akun atau bisnis sudah berubah. Masuk kembali dengan akun yang menyimpan.' };
  return call<{ state: 'saved' | 'unknown'; result?: { id: string; row_version: number } }>(`/requests/${request.payload.client_request_id}`);
}
export async function getHrWorkspace(filters: HrFilters) { return call<HrWorkspace>(`/workspace?${new URLSearchParams({ ...filters, skip: String(filters.skip), limit: '50' })}`); }
export async function getHrEmployeeChoices(search = '', skip = 0) { return call<{ items: { id: string; name: string; code: string }[]; total: number }>(`/employee-choices?${new URLSearchParams({ search, skip: String(skip), limit: '50' })}`); }
export async function writeHr(request: HrPending) {
  if (!/^\/(employees|schedules|attendance)(\/[0-9a-f-]{36}(\/void)?)?$/.test(request.path) && request.path !== '/punch') return { success: false as const, message: 'Permintaan belum valid' };
  const setup = await getHrSetup();
  if (!setup.success) return { ...setup, uncertain: true };
  if (request.workspace_key !== setup.data.workspace_key) return { success: false as const, uncertain: true, message: 'Akun atau bisnis sudah berubah. Muat ulang sebelum menyimpan.' };
  return call<{ id: string; row_version: number }>(request.path, request.method, request.payload);
}
