'use server';

import { cookies } from 'next/headers';
import type { CustomerResult, CustomerList, CustomerDetail, CustomerFilters, CustomerSave, CustomerNote } from '@/lib/customers';

async function call<T>(path: string, method = 'GET', payload?: unknown): Promise<CustomerResult<T>> {
  const write = method !== 'GET';
  try {
    const jar = await cookies();
    const token = jar.get('token')?.value;
    if (!token) return { success: false, message: 'Sesi berakhir. Masuk kembali untuk membuka pelanggan.' };
    const base = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const response = await fetch(`${base}/customers/workspace${path}`, { method, cache: 'no-store',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'X-Tenant-ID': jar.get('tenant_id')?.value || '' },
      body: payload ? JSON.stringify(payload) : undefined });
    const body = await response.json();
    if (!response.ok || body.success !== true || body.data == null) {
      const detail = body.detail;
      const message = response.status === 401 ? 'Sesi berakhir. Masuk kembali untuk membuka pelanggan.' : response.status >= 500
        ? (write ? 'Hasil penyimpanan belum pasti. Periksa permintaan yang sama.' : 'Data pelanggan belum bisa dimuat. Coba lagi.')
        : typeof detail === 'string' ? detail : typeof detail?.message === 'string' ? detail.message
        : Array.isArray(detail) ? detail.map((v: { msg: string }) => v.msg).join('. ')
        : body.message || 'Data pelanggan belum bisa diproses.';
      return { success: false, message, uncertain: write && response.status >= 500 };
    }
    return { success: true, data: body.data as T, message: body.message };
  } catch {
    return { success: false, uncertain: write, message: write ? 'Koneksi terputus. Hasil penyimpanan belum pasti; periksa permintaan yang sama.'
      : 'Data pelanggan belum bisa dimuat. Periksa koneksi lalu coba lagi.' };
  }
}

export async function getCustomerWorkspace(filters: CustomerFilters, exporting = false) {
  return call<CustomerList>(`?${new URLSearchParams({ ...filters, skip: String(filters.skip), limit: '50', ...(exporting ? { export: 'true' } : {}) })}`);
}
export async function getCustomerWorkspaceDetail(id: string, skip = 0) {
  return call<CustomerDetail>(`/${encodeURIComponent(id)}?skip=${skip}`);
}
export async function saveCustomerWorkspace(payload: CustomerSave, id?: string) {
  return call<{ id: string; row_version: number }>(id ? `/${encodeURIComponent(id)}` : '', id ? 'PUT' : 'POST', payload);
}
export async function addCustomerWorkspaceNote(id: string, payload: CustomerNote) {
  return call<{ id: string }>(`/${encodeURIComponent(id)}/notes`, 'POST', payload);
}
