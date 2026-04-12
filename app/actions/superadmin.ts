'use server';

import { cookies } from 'next/headers';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function saFetch(endpoint: string, options: RequestInit = {}) {
  const cookieStore = await cookies();
  const token = cookieStore.get('token')?.value;
  if (!token) throw new Error('Unauthorized');

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  headers.set('Content-Type', 'application/json');

  // Superadmin routes still need X-Tenant-ID for auth but it can be any valid value
  const tenantId = cookieStore.get('tenant_id')?.value;
  if (tenantId) headers.set('X-Tenant-ID', tenantId);

  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers, cache: 'no-store' });
  if (res.status === 401 || res.status === 403) {
    throw new Error(res.status === 401 ? 'Unauthorized' : 'Forbidden');
  }
  return res;
}

export async function getSuperadminStats() {
  try {
    const res = await saFetch('/superadmin/stats');
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function getSuperadminTenants(params?: { tier?: string; search?: string }) {
  try {
    const qs = new URLSearchParams();
    if (params?.tier) qs.set('tier', params.tier);
    if (params?.search) qs.set('search', params.search);
    const q = qs.toString();
    const res = await saFetch(`/superadmin/tenants${q ? `?${q}` : ''}`);
    const data = await res.json();
    return { tenants: data.data, meta: data.meta };
  } catch { return { tenants: [], meta: null }; }
}

export async function getSuperadminTenantDetail(tenantId: string) {
  try {
    const res = await saFetch(`/superadmin/tenants/${tenantId}`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function updateTenantTier(tenantId: string, tier: string) {
  try {
    const res = await saFetch(`/superadmin/tenants/${tenantId}/tier`, {
      method: 'PUT',
      body: JSON.stringify({ tier }),
    });
    const data = await res.json();
    return { success: res.ok, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update tier' }; }
}

export async function checkSuperadminAccess(): Promise<boolean> {
  try {
    const res = await saFetch('/superadmin/stats');
    return res.ok;
  } catch { return false; }
}

export async function getSuperadminAuditLogs(params?: { tenant_id?: string; entity?: string; limit?: number; skip?: number }) {
  try {
    const qs = new URLSearchParams();
    if (params?.tenant_id) qs.set('tenant_id', params.tenant_id);
    if (params?.entity) qs.set('entity', params.entity);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.skip) qs.set('skip', String(params.skip));
    const q = qs.toString();
    const res = await saFetch(`/superadmin/audit-logs${q ? `?${q}` : ''}`);
    const data = await res.json();
    return { logs: data.data || [], meta: data.meta };
  } catch { return { logs: [], meta: null }; }
}

// ── Billing ──────────────────────────────────────────────

export async function getTenantInvoices(tenantId: string) {
  try {
    const res = await saFetch(`/superadmin/billing/${tenantId}/invoices`);
    const data = await res.json();
    return data.data || [];
  } catch { return []; }
}

export async function generateTenantInvoice(tenantId: string) {
  try {
    const res = await saFetch(`/superadmin/billing/${tenantId}/generate`, { method: 'POST' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, data: null, message: 'Gagal generate invoice' }; }
}

export async function activateTenantBilling(tenantId: string) {
  try {
    const res = await saFetch(`/superadmin/billing/${tenantId}/activate`, { method: 'POST' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, data: null, message: 'Gagal activate tenant' }; }
}

export async function skipTenantBilling(tenantId: string) {
  // Skip billing = activate without generating invoice, just set active + next_billing_date
  return activateTenantBilling(tenantId);
}

export async function updateTenantStatus(tenantId: string, isActive: boolean, subscriptionStatus?: string) {
  try {
    const res = await saFetch(`/superadmin/tenants/${tenantId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive, subscription_status: subscriptionStatus }),
    });
    const data = await res.json();
    return { success: res.ok, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update status' }; }
}
