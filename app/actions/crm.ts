'use server';

/**
 * CRM gelombang 3 + promo WhatsApp. Dipisah dari api.ts biar file itu nggak
 * makin gendut. Pola sama: cookie token + X-Tenant-ID lewat fetchWithAuth.
 */
import { cookies } from 'next/headers';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function extractError(data: any, fallback: string): string {
  if (data?.message && typeof data.message === 'string') return data.message;
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ');
  return fallback;
}

async function call(endpoint: string, options: RequestInit = {}) {
  const cookieStore = await cookies();
  const token = cookieStore.get('token')?.value;
  if (!token) throw new Error('Unauthorized');
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const tenantId = cookieStore.get('tenant_id')?.value;
  if (tenantId) headers.set('X-Tenant-ID', tenantId);
  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers, cache: 'no-store' });
  if (res.status === 401) throw new Error('SESSION_EXPIRED');
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(extractError(data, 'Terjadi kesalahan'));
  return data;
}

// ── Segmen ──
export async function getSegmentSummary() {
  try { return (await call('/crm/segments/summary')).data || []; } catch { return []; }
}
export async function refreshSegments() {
  const d = await call('/crm/segments/refresh', { method: 'POST' });
  return { data: d.data, message: d.message as string };
}

// ── Tag ──
export async function getTags() {
  try { return (await call('/crm/tags')).data || []; } catch { return []; }
}
export async function createTag(name: string, color = 'violet') {
  return (await call('/crm/tags', { method: 'POST', body: JSON.stringify({ name, color }) })).data;
}
export async function deleteTag(id: string) {
  await call(`/crm/tags/${id}`, { method: 'DELETE' }); return true;
}
export async function setCustomerTags(customerId: string, tagIds: string[]) {
  return (await call(`/crm/customers/${customerId}/tags`, { method: 'PUT', body: JSON.stringify({ tag_ids: tagIds }) })).data;
}

// ── Profil / timeline ──
export async function getCustomerTimeline(customerId: string) {
  try { return (await call(`/crm/customers/${customerId}/timeline`)).data; } catch { return null; }
}
export async function addCustomerNote(customerId: string, body: string, kind = 'note') {
  return (await call(`/crm/customers/${customerId}/notes`, { method: 'POST', body: JSON.stringify({ body, kind }) })).data;
}
export async function updateCustomerProfile(customerId: string, payload: { birthday?: string | null; wa_marketing_consent?: boolean }) {
  return (await call(`/crm/customers/${customerId}/profile`, { method: 'PUT', body: JSON.stringify(payload) })).data;
}

// ── Voucher ──
export async function getVouchers() {
  try { return (await call('/crm/vouchers')).data || []; } catch { return []; }
}
export async function createVoucher(payload: Record<string, unknown>) {
  const d = await call('/crm/vouchers', { method: 'POST', body: JSON.stringify(payload) });
  return { data: d.data, message: d.message as string };
}
export async function updateVoucher(id: string, payload: Record<string, unknown>) {
  return (await call(`/crm/vouchers/${id}`, { method: 'PUT', body: JSON.stringify(payload) })).data;
}
export async function deleteVoucher(id: string) {
  await call(`/crm/vouchers/${id}`, { method: 'DELETE' }); return true;
}

// ── Promo WA (campaign) ──
export async function getCampaigns(outletId: string) {
  try { return (await call(`/campaigns/?outlet_id=${outletId}`)).data || []; } catch { return []; }
}
export async function previewCampaign(payload: { outlet_id: string; name: string; template: string; target: string }) {
  return (await call('/campaigns/preview', { method: 'POST', body: JSON.stringify(payload) })).data;
}
export async function createCampaign(payload: { outlet_id: string; name: string; template: string; target: string }) {
  return (await call('/campaigns/', { method: 'POST', body: JSON.stringify(payload) })).data;
}
export async function sendCampaign(id: string) {
  const d = await call(`/campaigns/${id}/send`, { method: 'POST' });
  return { data: d.data, message: d.message as string };
}
export async function getCampaign(id: string) {
  try { return (await call(`/campaigns/${id}`)).data; } catch { return null; }
}
export async function deleteCampaign(id: string) {
  await call(`/campaigns/${id}`, { method: 'DELETE' }); return true;
}
