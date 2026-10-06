'use server';

import { cookies } from 'next/headers';
import { validAccountAccess } from '@/lib/account-access';

export type AccountResult<T = any> = { success: true; data: T } | { success: false; message: string };
const base = (process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');

async function call(path: string, method = 'GET', body?: unknown, authenticated = true): Promise<AccountResult> {
  const jar = await cookies();
  const token = jar.get('token')?.value;
  if (authenticated && !token) return { success: false, message: 'Sesi berakhir. Masuk kembali.' };
  try {
    const result = await fetch(`${base}${path}`, { method, cache: 'no-store', signal: AbortSignal.timeout(20000),
      headers: { 'Content-Type': 'application/json', ...(authenticated ? { Authorization: `Bearer ${token}`, 'X-Tenant-ID': jar.get('tenant_id')?.value || '' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}) });
    const value = await result.json();
    if (!result.ok) return { success: false, message: typeof value.detail === 'string' ? value.detail
      : Array.isArray(value.detail) ? value.detail.map((v: { msg: string }) => v.msg).join('. ')
      : value.detail?.message || 'Permintaan gagal. Coba lagi.' };
    return { success: true, data: value.data };
  } catch { return { success: false, message: method === 'GET' ? 'Data belum dapat dimuat. Coba lagi.' : 'Hasil permintaan belum pasti. Coba lagi dengan data yang sama.' }; }
}

async function save(result: AccountResult): Promise<AccountResult> {
  if (!result.success) return result;
  const jar = await cookies();
  for (const [name, value] of Object.entries({ token: result.data.access_token, tenant_id: result.data.tenant_id, outlet_id: result.data.outlet_id })) {
    if (typeof value === 'string' && value) jar.set(name, value, { httpOnly: true, sameSite: 'lax', secure: process.env.NEXT_PUBLIC_SECURE_COOKIES === 'true', path: '/', maxAge: 7 * 86400 });
    else jar.delete(name);
  }
  const { access_token, ...data } = result.data;
  return { success: true, data };
}

export async function loginPassword(body: unknown) { return save(await call('/auth/password/login', 'POST', body, false)); }
export async function registerPassword(body: unknown) { return save(await call('/auth/password/register', 'POST', body, false)); }
export async function consumeAccountCode(body: unknown) { return save(await call('/auth/password/challenge', 'POST', body, false)); }
export async function claimPassword(body: unknown) { return save(await call('/auth/password/claim', 'POST', body)); }
export async function getAccountInfo() { return call('/auth/account'); }
export async function getAccountAccess(): Promise<AccountResult> {
  const result = await call('/auth/access');
  return result.success && !validAccountAccess(result.data)
    ? { success: false, message: 'Pengaturan akses belum dapat dimuat. Masuk kembali.' } : result;
}
export async function getAccountSessions() { return call('/auth/sessions'); }
export async function revokeAccountSessions(body: unknown) {
  const result = await call('/auth/sessions/revoke-all', 'POST', body);
  if (result.success) { const jar = await cookies(); for (const name of ['token', 'tenant_id', 'outlet_id']) jar.delete(name); }
  return result;
}
export async function getAccountSetup() { return call('/hris/access/setup'); }
export async function saveAccessRole(body: unknown) { return call('/hris/access/roles', 'POST', body); }
export async function saveStaffAccount(employeeId: string, body: unknown) { return call(`/hris/employees/${encodeURIComponent(employeeId)}/account`, 'POST', body); }
export async function issueStaffActivation(employeeId: string, body: unknown) { return call(`/hris/employees/${encodeURIComponent(employeeId)}/activation`, 'POST', body); }
