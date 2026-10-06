'use server';

import { cookies } from 'next/headers';
import { validAccountAccess } from '@/lib/account-access';
import type { HppIngredient, HppProduct, HppRecipe } from '@/lib/hpp';
import type { InventoryIngredient } from '@/lib/ingredient-inventory';
import type { HppChatMode, HppChatSession, HppChatListItem, HppChatResult } from '@/lib/hpp-chat';
import type { FinanceSummary, FinanceExpense, FinanceAccount, FinanceCategory, FinanceSetup, FinanceResult } from '@/lib/finance';
import type { PurchaseResult, PurchaseSetup, PurchaseData, PurchaseTarget, PurchaseFilters, Purchase, Supplier, PurchaseSummary } from '@/lib/purchasing';

async function businessAccess() {
  const response = await fetchWithAuth('/auth/access', { cache: 'no-store' });
  const body = await response.json();
  if (!response.ok || !validAccountAccess(body.data)) throw new Error(extractError(body, 'Akses akun belum dapat dimuat.'));
  const managed = body.data.enforcement_mode === 'managed';
  const allows = (permission: string) => !managed || body.data.permissions.includes(permission);
  return { managed, allows, includeGlobal: !managed || body.data.scope === 'tenant' };
}

async function hppChatRequest<T>(path: string, options: RequestInit = {}): Promise<HppChatResult<T>> {
  try {
    const response = await fetchWithAuth(`/ai/hpp-setup/${path}`, { ...options, cache: 'no-store' });
    const body = await response.json();
    if (!response.ok) return { success: false, message: response.status >= 500
      ? 'Hasil belum dapat dipastikan. Periksa percakapan terbaru sebelum mencoba lagi.'
      : extractError(body, 'Percakapan belum bisa diproses.') };
    return { success: true, data: body.data as T };
  } catch (error) {
    return { success: false, message: error instanceof Error && ['SESSION_EXPIRED', 'Unauthorized'].includes(error.message)
      ? 'Sesi berakhir. Masuk kembali untuk melanjutkan percakapan.'
      : 'Koneksi terputus. Periksa percakapan terbaru; pesan dan persetujuan mungkin sudah diterima.' };
  }
}

export async function listHppChats(outletId?: string): Promise<HppChatResult<HppChatListItem[]>> {
  const outlet = outletId || (await cookies()).get('outlet_id')?.value;
  if (!outlet) return { success: false, message: 'Pilih outlet dahulu.' };
  return hppChatRequest(`sessions?outlet_id=${encodeURIComponent(outlet)}`);
}

export async function createHppChat(mode: HppChatMode, productId?: string, outletId?: string): Promise<HppChatResult<HppChatSession>> {
  const outlet = outletId || (await cookies()).get('outlet_id')?.value;
  if (!outlet) return { success: false, message: 'Pilih outlet dahulu.' };
  return hppChatRequest('sessions', { method: 'POST', body: JSON.stringify({ outlet_id: outlet, mode, product_id: productId || null }) });
}

export async function getHppChat(id: string, outletId?: string): Promise<HppChatResult<HppChatSession>> {
  const result = await hppChatRequest<HppChatSession>(`sessions/${encodeURIComponent(id)}`);
  const outlet = outletId || (await cookies()).get('outlet_id')?.value;
  if (result.success && result.data.outlet_id !== outlet) return { success: false, message: 'Percakapan ini milik outlet lain. Pilih outlet yang sesuai.' };
  return result;
}

export async function sendHppChat(id: string, payload: { request_id: string; revision: number; mode: HppChatMode; message: string }, outletId?: string): Promise<HppChatResult<HppChatSession>> {
  const outlet = outletId || (await cookies()).get('outlet_id')?.value;
  if (!outlet) return { success: false, message: 'Pilih outlet dahulu.' };
  return hppChatRequest(`sessions/${encodeURIComponent(id)}/messages`, { method: 'POST', body: JSON.stringify({ ...payload, outlet_id: outlet }) });
}

export async function approveHppChat(id: string, revision: number, fingerprint: string, replaceRecipe: boolean, outletId?: string): Promise<HppChatResult<HppChatSession>> {
  const outlet = outletId || (await cookies()).get('outlet_id')?.value;
  if (!outlet) return { success: false, message: 'Pilih outlet dahulu.' };
  return hppChatRequest(`sessions/${encodeURIComponent(id)}/approve`, { method: 'POST', body: JSON.stringify({ outlet_id: outlet, revision, fingerprint, replace_recipe: replaceRecipe }) });
}

// Gunakan internal Docker URL untuk server actions (lebih cepat, bypass Nginx)
const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/** Extract error message from API response — handles string, object, and array detail */
function extractError(data: any, fallback = 'Terjadi kesalahan'): string {
  if (data?.message && typeof data.message === 'string') return data.message;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.detail?.message === 'string') return data.detail.message;
  if (Array.isArray(data?.detail)) return data.detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ');
  return fallback;
}

export async function getAuthToken() {
  const cookieStore = await cookies();
  return cookieStore.get('token')?.value;
}

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  if (!token) throw new Error('Unauthorized');

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const cookieStore = await cookies();
  const tenantId = cookieStore.get('tenant_id')?.value;
  if (tenantId) headers.set('X-Tenant-ID', tenantId);

  // Tambah trailing slash untuk collection endpoints, tapi JANGAN untuk resource endpoints
  // seperti /me, /status, /pin, /version (akan menyebabkan 307 dan Authorization header hilang)
  const normalizedEndpoint = endpoint.replace(/^([^?]+?)(\?|$)/, (_, path, sep) => {
    if (path.endsWith('/')) return `${path}${sep}`;
    // Jangan tambah trailing slash jika path berakhir dengan kata (bukan collection root)
    const lastSegment = path.split('/').pop() || '';
    const isCollectionRoot = lastSegment === '' || /^[a-z_-]+$/.test(lastSegment) && !['me', 'status', 'pin', 'verify', 'send', 'version', 'upload', 'daily', 'setup', 'cashier'].includes(lastSegment);
    return isCollectionRoot ? `${path}/${sep}` : `${path}${sep}`;
  });

  // Gunakan redirect: 'manual' dan follow manual untuk preserve Authorization header
  const res = await fetch(`${API_URL}${normalizedEndpoint}`, { ...options, headers, redirect: 'manual' });

  // Follow 307/308 redirect secara manual agar Authorization header tidak hilang
  if (res.status === 307 || res.status === 308) {
    const location = res.headers.get('location');
    if (location) {
      const redirectUrl = location.startsWith('http') ? location : `${API_URL}${location}`;
      const retryRes = await fetch(redirectUrl, { ...options, headers, redirect: 'manual' });
      if (retryRes.status === 401) throw new Error('Unauthorized');
      return retryRes;
    }
  }

  if (res.status === 401) {
    // Clear auth cookies on 401
    const { cookies: getCookies } = await import('next/headers');
    const cookieStore = await getCookies();
    cookieStore.delete('token');
    cookieStore.delete('tenant_id');
    cookieStore.delete('outlet_id');
    // Throw instead of redirect — callers with try-catch can handle gracefully,
    // page-level loaders will catch and redirect via client-side navigation
    throw new Error('SESSION_EXPIRED');
  }
  return res;
}

export async function getCurrentUser() {
  try {
    const res = await fetchWithAuth('/users/me');
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function getOutlets() {
  try {
    const res = await fetchWithAuth('/outlets');
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function setOutletLocation(outletId: string, latitude: number, longitude: number) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/location`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude, longitude }),
    });
    const data = await res.json();
    if (!res.ok) return { success: false, message: data?.detail || 'Gagal menyimpan titik lokasi' };
    return { success: true };
  } catch { return { success: false, message: 'Terjadi kesalahan jaringan' }; }
}

export async function getSefrekuensiStatus(outletId: string) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/sefrekuensi-status`);
    const data = await res.json();
    return data.data as { enabled: boolean; connected: boolean; push: boolean; phone_masked: string | null; play_url: string } | null;
  } catch { return null; }
}

export async function getProducts(brandId: string) {
  try {
    const res = await fetchWithAuth(`/products?brand_id=${brandId}`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function getBestSellers(limit: number = 5) {
  try {
    const res = await fetchWithAuth(`/products/best-sellers?limit=${limit}`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function getCategories(brandId: string) {
  try {
    const res = await fetchWithAuth(`/categories?brand_id=${brandId}`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function createCategory(brandId: string, name: string) {
  try {
    const res = await fetchWithAuth('/categories/', {
      method: 'POST',
      body: JSON.stringify({ brand_id: brandId, name }),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat kategori' }; }
}

export async function updateCategory(categoryId: string, payload: { name?: string; is_active?: boolean }) {
  try {
    const res = await fetchWithAuth(`/categories/${categoryId}/`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update kategori' }; }
}

export async function deleteCategory(categoryId: string) {
  try {
    const res = await fetchWithAuth(`/categories/${categoryId}/`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

export async function createProduct(productData: any) {
  try {
    const res = await fetchWithAuth('/products/', {
      method: 'POST',
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat produk' }; }
}

export async function updateProduct(productId: string, productData: any) {
  try {
    const res = await fetchWithAuth(`/products/${productId}/`, {
      method: 'PUT',
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update produk' }; }
}

export async function deleteProduct(productId: string) {
  try {
    const res = await fetchWithAuth(`/products/${productId}/`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

/**
 * Simpan seluruh daftar varian satu produk sekaligus (Hot/Ice, size, level gula).
 *
 * Sengaja "kirim daftar final", bukan tambah/hapus per baris: form produk cuma
 * punya satu tombol Simpan, jadi kalau tiap baris jadi request sendiri, gagal
 * di tengah ninggalin daftar setengah jadi tanpa pemiliknya sadar.
 */
export async function setProductVariants(
  productId: string,
  variants: { name: string; price_adjustment: number; is_active: boolean; sort_order: number }[],
) {
  try {
    const res = await fetchWithAuth(`/products/${productId}/variants`, {
      method: 'PUT',
      body: JSON.stringify({ variants }),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal menyimpan varian' }; }
}

export async function toggleProductActive(productId: string, isActive: boolean, rowVersion: number) {
  try {
    const res = await fetchWithAuth(`/products/${productId}/`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive, row_version: rowVersion }),
    });
    return res.ok;
  } catch { return false; }
}

// Upload gambar produk — dipanggil via /api/upload proxy route (server action tidak bisa handle FormData dari browser)
export async function proxyUploadImage(formData: FormData) {
  const token = await getAuthToken();
  const cookieStore = await cookies();
  const tenantId = cookieStore.get('tenant_id')?.value;

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (tenantId) headers['X-Tenant-ID'] = tenantId;

  const res = await fetch(`${API_URL}/media/upload/`, {
    method: 'POST',
    headers,
    body: formData,
  });
  const data = await res.json();
  return { success: res.ok, url: data.url, message: data.detail };
}

export async function getCashiers(outletId: string) {
  try {
    const res = await fetchWithAuth(`/users?outlet_id=${outletId}&role=cashier`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function createCashier(cashierData: any) {
  try {
    const res = await fetchWithAuth('/users/cashier/', {
      method: 'POST',
      body: JSON.stringify(cashierData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail || 'Gagal membuat kasir' };
  } catch { return { success: false, message: 'Gagal membuat kasir' }; }
}

export async function toggleCashierActive(userId: string, isActive: boolean) {
  try {
    const res = await fetchWithAuth(`/users/${userId}/status/`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.ok;
  } catch { return false; }
}

export async function resetCashierPin(userId: string, newPin: string) {
  try {
    const res = await fetchWithAuth(`/users/${userId}/pin/`, {
      method: 'PUT',
      body: JSON.stringify({ pin: newPin }),
    });
    return res.ok;
  } catch { return false; }
}

export async function getOrders(outletId: string, startDate?: string, endDate?: string) {
  try {
    let url = `/orders?outlet_id=${outletId}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    const res = await fetchWithAuth(url);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function updateOutlet(outletId: string, outletData: any) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/`, {
      method: 'PUT',
      body: JSON.stringify(outletData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message };
  } catch { return { success: false, message: 'Gagal update outlet' }; }
}

export async function setupPayment(outletId: string, paymentData: any) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup/`, {
      method: 'POST',
      body: JSON.stringify(paymentData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal setup pembayaran' }; }
}

export async function setupPaymentOwnKey(outletId: string, xenditApiKey: string, xenditCallbackToken?: string) {
  try {
    const body: Record<string, string> = { xendit_api_key: xenditApiKey };
    if (xenditCallbackToken && xenditCallbackToken.trim()) {
      body.xendit_callback_token = xenditCallbackToken.trim();
    }
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup/own-key/`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal menyimpan API key' }; }
}

export async function removePaymentOwnKey(outletId: string) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup/own-key/`, { method: 'DELETE' });
    const data = await res.json();
    return { success: res.ok, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal menghapus API key' }; }
}

export async function getPaymentStatus(outletId: string) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-status`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function getDailyReport(outletId: string, reportDate: string) {
  try {
    const res = await fetchWithAuth(`/reports/daily?outlet_id=${outletId}&report_date=${reportDate}`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function getReportSummary(outletId: string, startDate: string, endDate: string) {
  try {
    const res = await fetchWithAuth(`/reports/summary?outlet_id=${outletId}&start_date=${startDate}&end_date=${endDate}`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

/**
 * Margin report (Starter feature) — list produk + computed margin (base_price - buy_price).
 * Returns { data, error }. Error includes recipe-mode reject (400 STOCK_MODE_NOT_SUPPORTED).
 */
export async function getMarginReport(outletId: string): Promise<{ data: any | null; error: string | null; isRecipeMode: boolean }> {
  try {
    const res = await fetchWithAuth(`/reports/margin?outlet_id=${outletId}`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = body?.detail;
      if (res.status === 400 && typeof detail === 'object' && detail?.code === 'STOCK_MODE_NOT_SUPPORTED') {
        return { data: null, error: detail.message || 'Outlet pakai mode Resep, pakai Laporan HPP.', isRecipeMode: true };
      }
      const msg = typeof detail === 'string' ? detail : (detail?.message || `Error ${res.status}`);
      return { data: null, error: msg, isRecipeMode: false };
    }
    const json = await res.json();
    return { data: json.data, error: null, isRecipeMode: false };
  } catch (e: any) {
    return { data: null, error: e?.message || 'Gagal memuat laporan', isRecipeMode: false };
  }
}

export async function getWeeklyRevenue(outletId: string) {
  const days: { date: Date; dateStr: string }[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push({ date: d, dateStr: d.toISOString().split('T')[0] });
  }

  const results = await Promise.all(
    days.map(async ({ date, dateStr }) => {
      try {
        const res = await fetchWithAuth(`/reports/daily?outlet_id=${outletId}&report_date=${dateStr}`);
        const json = await res.json();
        return { name: date.toLocaleDateString('id-ID', { weekday: 'short' }), revenue: json.data?.revenue_today || 0 };
      } catch {
        return { name: date.toLocaleDateString('id-ID', { weekday: 'short' }), revenue: 0 };
      }
    })
  );

  return results;
}

// ===================== Reservations =====================

export async function getReservations(outletId: string, reservationDate?: string, status?: string) {
  try {
    let url = `/reservations?outlet_id=${outletId}`;
    if (reservationDate) url += `&reservation_date=${reservationDate}`;
    if (status) url += `&status=${status}`;
    const res = await fetchWithAuth(url);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function createReservation(outletId: string, payload: {
  reservation_date: string;
  start_time: string;
  guest_count: number;
  customer_name: string;
  customer_phone: string;
  table_id?: string;
  notes?: string;
  source?: string;
}) {
  try {
    const res = await fetchWithAuth(`/reservations/?outlet_id=${outletId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat reservasi' }; }
}

export async function confirmReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/confirm/`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal konfirmasi reservasi' }; }
}

export async function seatReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/seat/`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal mengubah status reservasi' }; }
}

export async function completeReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/complete/`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal menyelesaikan reservasi' }; }
}

export async function cancelReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/cancel/`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membatalkan reservasi' }; }
}

export async function noShowReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/no-show/`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal mengubah status reservasi' }; }
}

export async function getReservationSettings(outletId: string) {
  try {
    const res = await fetchWithAuth(`/reservations/settings/${outletId}`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function updateReservationSettings(outletId: string, payload: any) {
  try {
    const res = await fetchWithAuth(`/reservations/settings/${outletId}/`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update pengaturan reservasi' }; }
}

// ===================== Tables =====================

export async function getTables(outletId: string) {
  try {
    const res = await fetchWithAuth(`/tables?outlet_id=${outletId}`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function createTable(outletId: string, payload: {
  name: string;
  capacity: number;
  floor_section?: string;
  is_active?: boolean;
}) {
  try {
    const res = await fetchWithAuth(`/tables/?outlet_id=${outletId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    const msg = typeof data.detail === 'string' ? data.detail : (data.message || 'Gagal membuat meja');
    return { success: res.ok, data: data.data, message: msg };
  } catch { return { success: false, message: 'Gagal membuat meja' }; }
}

export async function updateTable(id: string, payload: any) {
  try {
    const res = await fetchWithAuth(`/tables/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update meja' }; }
}

export async function deleteTable(id: string) {
  try {
    const res = await fetchWithAuth(`/tables/${id}/`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

// ===================== Ingredients (Pro) =====================

export async function getIngredients(brandId: string, outletId?: string) {
  try {
    let url = `/ingredients?brand_id=${brandId}`;
    if (outletId) url += `&outlet_id=${outletId}`;
    const res = await fetchWithAuth(url);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function createIngredient(payload: any) {
  const res = await fetchWithAuth('/ingredients/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal menambahkan bahan baku');
  return data.data;
}

export async function updateIngredient(id: string, payload: any) {
  const res = await fetchWithAuth(`/ingredients/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal mengupdate bahan baku');
  return data.data;
}

export async function deleteIngredient(id: string) {
  try {
    const res = await fetchWithAuth(`/ingredients/${id}/`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

export async function restockIngredient(id: string, payload: { outlet_id: string; quantity: number; notes?: string }) {
  const res = await fetchWithAuth(`/ingredients/${id}/restock/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal restock');
  return data.data;
}

// ===================== Recipes (Pro) =====================

export async function getRecipes(params: { product_id?: string; brand_id?: string }) {
  try {
    const qs = new URLSearchParams();
    if (params.product_id) qs.set('product_id', params.product_id);
    if (params.brand_id) qs.set('brand_id', params.brand_id);
    const res = await fetchWithAuth(`/recipes?${qs.toString()}`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

export async function createRecipe(payload: any) {
  const res = await fetchWithAuth('/recipes/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal membuat resep');
  return data.data;
}

export async function updateRecipe(id: string, payload: any) {
  const res = await fetchWithAuth(`/recipes/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal mengupdate resep');
  return data.data;
}

export async function deleteRecipe(id: string) {
  try {
    const res = await fetchWithAuth(`/recipes/${id}/`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

export async function getHPPReport(brandId: string) {
  try {
    const res = await fetchWithAuth(`/recipes/hpp?brand_id=${brandId}`);
    const data = await res.json();
    return data.data;
  } catch { return []; }
}

// ===================== Stock Mode =====================

async function readHppData(endpoint: string) {
  const res = await fetchWithAuth(endpoint, { cache: 'no-store' });
  if (!res.ok) throw new Error(res.status === 403 ? 'HPP tersedia untuk paket Pro.' : 'Data HPP belum bisa dimuat. Coba lagi.');
  const data = await res.json();
  if (!Array.isArray(data.data)) throw new Error('Data HPP belum bisa dimuat. Coba lagi.');
  return data.data;
}

async function readAllHppData(endpoint: string) {
  const items: any[] = [];
  for (let skip = 0; ; skip += 100) {
    const page = await readHppData(`${endpoint}&skip=${skip}&limit=100`);
    items.push(...page);
    if (page.length < 100) return items;
  }
}

function hppError(error: unknown) {
  const message = error instanceof Error ? error.message : '';
  if (['SESSION_EXPIRED', 'Unauthorized'].includes(message)) return 'Sesi login sudah berakhir. Login kembali untuk melanjutkan.';
  if (message === 'HPP tersedia untuk paket Pro.' || message === 'Data HPP belum bisa dimuat. Coba lagi.') return message;
  return 'Belum berhasil. Periksa koneksi lalu coba lagi.';
}

export async function loadHppProducts(outletId?: string) {
  try {
    const outlets = await readHppData('/outlets');
    const chosen = outletId || (await cookies()).get('outlet_id')?.value;
    const outlet = outlets.find((o: any) => o.id === chosen) || outlets[0];
    if (!outlet) return { success: false as const, message: 'Buat outlet terlebih dahulu di Pengaturan.' };
    const brand = encodeURIComponent(outlet.brand_id);
    const [products, recipes] = await Promise.all([
      readAllHppData(`/products?brand_id=${brand}&outlet_id=${encodeURIComponent(outlet.id)}`), readHppData(`/recipes?brand_id=${brand}`),
    ]);
    const access = await businessAccess();
    return { success: true as const, brandId: outlet.brand_id as string, stockMode: outlet.stock_mode as string,
      outlets: outlets.map((o: any) => ({ id: o.id as string, name: o.name as string })), outletId: outlet.id as string,
      managed: access.managed, canManage: access.allows('hpp.manage') && access.allows('hpp.approve') && access.allows('supplier.price.view'),
      canChat: ['ai.chat', 'hpp.view', 'hpp.manage', 'supplier.price.view'].every(access.allows),
      products: products as HppProduct[], recipes: recipes as HppRecipe[] };
  } catch (error) { return { success: false as const, message: hppError(error) }; }
}

export async function loadHppRecipe(brandId: string, productId: string) {
  try {
    const outlets = await readHppData('/outlets');
    const chosen = (await cookies()).get('outlet_id')?.value;
    const outlet = outlets.find((o: any) => o.id === chosen && o.brand_id === brandId) || outlets.find((o: any) => o.brand_id === brandId);
    if (!outlet) throw new Error('Data HPP belum bisa dimuat. Coba lagi.');
    const [ingredients, recipes] = await Promise.all([
      readAllHppData(`/ingredients?brand_id=${encodeURIComponent(brandId)}&outlet_id=${encodeURIComponent(outlet.id)}`),
      readHppData(`/recipes?product_id=${encodeURIComponent(productId)}`),
    ]);
    return { success: true as const, ingredients: ingredients as HppIngredient[], recipe: (recipes[0] || null) as HppRecipe | null };
  } catch (error) { return { success: false as const, message: hppError(error) }; }
}

export async function saveHppIngredient(payload: {
  brand_id: string; name: string; base_unit: string; unit_type: string; buy_price: number; buy_qty: number;
}, existing?: { id: string; row_version: number }) {
  try {
    if (!payload.name.trim() || !Number.isFinite(payload.buy_price) || payload.buy_price < 0 || !Number.isFinite(payload.buy_qty) || payload.buy_qty <= 0) {
      return { success: false as const, message: 'Isi nama bahan, harga beli, dan jumlah pembelian yang valid.' };
    }
    const res = await fetchWithAuth(existing ? `/ingredients/${existing.id}/` : '/ingredients/', {
      method: existing ? 'PUT' : 'POST', body: JSON.stringify(existing
        ? { name: payload.name.trim(), buy_price: payload.buy_price, buy_qty: payload.buy_qty, row_version: existing.row_version }
        : { ...payload, name: payload.name.trim(), tracking_mode: 'simple', ingredient_type: 'recipe' }),
    });
    const data = await res.json();
    if (!res.ok) return { success: false as const, message: res.status < 500 ? extractError(data, 'Bahan belum tersimpan.') : 'Bahan belum tersimpan. Coba lagi beberapa saat.' };
    return { success: true as const, ingredient: data.data as HppIngredient };
  } catch (error) { return { success: false as const, message: hppError(error) }; }
}

export async function saveHppRecipe(productId: string, ingredients: {
  ingredient_id: string; quantity: number; quantity_unit: string; is_optional: boolean; notes?: string | null;
}[], recipeId?: string, notes?: string | null) {
  try {
    if (!ingredients.length || !ingredients.some(i => !i.is_optional) || ingredients.some(i => !Number.isFinite(i.quantity) || i.quantity <= 0)) {
      return { success: false as const, message: 'Isi takaran lebih dari nol untuk setiap bahan, dengan minimal satu bahan utama.' };
    }
    const res = await fetchWithAuth(recipeId ? `/recipes/${recipeId}/` : '/recipes/', {
      method: recipeId ? 'PUT' : 'POST', body: JSON.stringify({ product_id: productId, ingredients, notes }),
    });
    const data = await res.json();
    if (!res.ok) return { success: false as const, message: res.status < 500 ? extractError(data, 'Resep belum tersimpan.') : 'Resep belum tersimpan. Coba lagi beberapa saat.' };
    return { success: true as const, recipe: data.data as HppRecipe };
  } catch (error) { return { success: false as const, message: hppError(error) }; }
}

export async function loadIngredientInventory() {
  try {
    const outlets = await readHppData('/outlets');
    const outlet = outlets[0];
    if (!outlet) return { success: false as const, message: 'Buat outlet terlebih dahulu di Pengaturan.' };
    const ingredients = await readAllHppData(`/ingredients?brand_id=${encodeURIComponent(outlet.brand_id)}&outlet_id=${encodeURIComponent(outlet.id)}`);
    return { success: true as const, ingredients: ingredients as InventoryIngredient[],
      outletId: outlet.id as string, brandId: outlet.brand_id as string, stockMode: outlet.stock_mode as string };
  } catch (error) {
    const message = hppError(error);
    return { success: false as const, message: message === 'Data HPP belum bisa dimuat. Coba lagi.'
      ? 'Daftar bahan belum bisa dimuat. Coba lagi.' : message === 'HPP tersedia untuk paket Pro.'
        ? 'Bahan Baku tersedia untuk paket Pro.' : message };
  }
}

async function writeInventory(endpoint: string, options: RequestInit) {
  try {
    const res = await fetchWithAuth(endpoint, options);
    const data = await res.json();
    if (!res.ok) return { success: false as const, uncertain: res.status >= 500,
      message: res.status < 500 ? extractError(data, 'Perubahan belum tersimpan.')
        : 'Hasil penyimpanan belum dapat dipastikan. Muat ulang data sebelum mencoba lagi.' };
    return { success: true as const, data: data.data as InventoryIngredient };
  } catch (error) {
    const expired = error instanceof Error && ['Unauthorized', 'SESSION_EXPIRED'].includes(error.message);
    return { success: false as const, uncertain: !expired, message: expired ? hppError(error)
      : 'Hasil penyimpanan belum dapat dipastikan. Muat ulang data sebelum mencoba lagi.' };
  }
}

export async function saveInventoryIngredient(payload: {
  brand_id: string; name: string; base_unit: string; unit_type: string; buy_price: number; buy_qty: number;
  ingredient_type: 'recipe' | 'overhead'; overhead_cost_per_day?: number;
}, existing?: { id: string; row_version: number }) {
  const validPrice = payload.ingredient_type === 'overhead'
    ? Number.isFinite(payload.overhead_cost_per_day) && payload.overhead_cost_per_day! >= 0
    : Number.isFinite(payload.buy_price) && payload.buy_price >= 0 && Number.isFinite(payload.buy_qty) && payload.buy_qty > 0 && Number.isFinite(payload.buy_price / payload.buy_qty);
  if (!payload.name.trim() || !validPrice) return { success: false as const, uncertain: false,
    message: 'Isi nama dan harga yang valid. Jumlah pembelian harus lebih dari nol.' };
  const values = existing ? { name: payload.name.trim(), row_version: existing.row_version,
    ...(payload.ingredient_type === 'overhead' ? { overhead_cost_per_day: payload.overhead_cost_per_day }
      : { buy_price: payload.buy_price, buy_qty: payload.buy_qty }) }
    : { ...payload, name: payload.name.trim(), tracking_mode: 'simple' };
  return writeInventory(existing ? `/ingredients/${existing.id}/` : '/ingredients/', {
    method: existing ? 'PUT' : 'POST', body: JSON.stringify(values),
  });
}

export async function addInventoryStock(ingredientId: string, outletId: string, quantity: number, notes?: string) {
  if (!Number.isFinite(quantity) || quantity <= 0) return { success: false as const, uncertain: false, message: 'Jumlah tambahan stok harus lebih dari nol.' };
  return writeInventory(`/ingredients/${ingredientId}/restock/`, {
    method: 'POST', body: JSON.stringify({ outlet_id: outletId, quantity, notes: notes?.trim() || undefined }),
  });
}

export async function removeInventoryIngredient(id: string) {
  return writeInventory(`/ingredients/${id}/`, { method: 'DELETE' });
}

export async function updateStockMode(outletId: string, stockMode: string) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/stock-mode/`, {
      method: 'PUT',
      body: JSON.stringify({ stock_mode: stockMode }),
    });
    const data = await res.json();
    // Expected API rejections must cross the Server Action boundary as data.
    // Production Next.js deliberately redacts thrown error messages.
    if (!res.ok) {
      return {
        success: false as const,
        needsRecipeSetup: res.status === 400 && stockMode === 'recipe',
        message: res.status < 500
          ? extractError(data, 'Gagal mengubah mode stok')
          : 'Mode stok belum tersimpan. Coba lagi beberapa saat.',
      };
    }
    return { success: true as const, data: data.data };
  } catch (error) {
    const expired = error instanceof Error && ['SESSION_EXPIRED', 'Unauthorized'].includes(error.message);
    return {
      success: false as const,
      needsRecipeSetup: false,
      message: expired
        ? 'Sesi login sudah berakhir. Login kembali sebelum mengubah mode stok.'
        : 'Mode stok belum tersimpan. Periksa koneksi lalu coba lagi.',
    };
  }
}

// ── Sesi kas (shift otomatis, gelombang 2) ──
export async function getCurrentShift(outletId: string) {
  const res = await fetchWithAuth(`/shifts/current?outlet_id=${outletId}`);
  const data = await res.json();
  return res.ok ? data.data : null;
}

export async function getUncountedShifts(outletId: string) {
  const res = await fetchWithAuth(`/shifts/uncounted?outlet_id=${outletId}`);
  const data = await res.json();
  return res.ok ? (data.data as any[]) : [];
}

export async function countShift(shiftId: string, endingCash: number, notes?: string) {
  const res = await fetchWithAuth(`/shifts/${shiftId}/close`, {
    method: 'POST',
    body: JSON.stringify({ ending_cash: endingCash, notes }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal mencatat hitungan kas');
  return data;
}

export async function getTaxConfig(outletId: string) {
  const res = await fetchWithAuth(`/outlets/${outletId}/tax-config`);
  const data = await res.json();
  return data.data;
}

export async function updateTaxConfig(outletId: string, config: any) {
  const res = await fetchWithAuth(`/outlets/${outletId}/tax-config/`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal menyimpan pengaturan pajak');
  return data.data;
}

// ── Billing ──────────────────────────────────────────────

export async function getBillingInfo() {
  const res = await fetchWithAuth('/billing/current');
  const data = await res.json();
  return data.data;
}

export async function getBillingInvoices() {
  const res = await fetchWithAuth('/billing/invoices');
  const data = await res.json();
  return data.data || [];
}

export async function retryInvoicePayment(invoiceId: string) {
  const res = await fetchWithAuth(`/billing/invoices/${invoiceId}/retry`, {
    method: 'POST',
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal membuat invoice');
  return data.data;
}

// ── Referral ──────────────────────────────────────────────────
export async function getReferralCode() {
  const res = await fetchWithAuth('/referrals/my-code');
  const data = await res.json();
  if (!res.ok) return null;
  return data.data;
}

export async function getReferralStats() {
  const res = await fetchWithAuth('/referrals/stats');
  const data = await res.json();
  if (!res.ok) return null;
  return data.data;
}

// ── CRM pelanggan ────────────────────────────────────────────────────────────
// Pakai server action, bukan route handler di /api/*, karena nginx melempar
// SEMUA /api/ ke FastAPI — route Next di bawah /api/ harus didaftarkan manual
// di nginx dan gampang kelupaan. Server action juga lebih cepat: nembak
// backend lewat jaringan internal Docker, bypass nginx.

export async function getCrmCustomers(
  params: { search?: string; sort?: string; segment?: string; rfm?: string } = {}
) {
  try {
    const qs = new URLSearchParams({ sort: params.sort || 'last_visit', limit: '200' });
    if (params.search?.trim()) qs.set('search', params.search.trim());
    if (params.segment) qs.set('segment', params.segment);
    if (params.rfm) qs.set('rfm', params.rfm);
    const res = await fetchWithAuth(`/customers/crm?${qs}`);
    const data = await res.json();
    return data.data ?? null;
  } catch { return null; }
}

export async function getCrmCustomerDetail(customerId: string) {
  try {
    const res = await fetchWithAuth(`/customers/${customerId}/detail`);
    const data = await res.json();
    return data.data ?? null;
  } catch { return null; }
}

export async function refreshCrmStats() {
  try {
    const res = await fetchWithAuth('/customers/refresh-stats', { method: 'POST' });
    const data = await res.json();
    return data.success === true;
  } catch { return false; }
}

// ── Purchasing (nota belanja + supplier) ─────────────────────────────

export async function getSuppliers(includeInactive = false) {
  try {
    const res = await fetchWithAuth(`/suppliers${includeInactive ? '?include_inactive=true' : ''}`);
    const data = await res.json();
    return data.data || [];
  } catch { return []; }
}

export async function createSupplier(payload: Record<string, unknown>) { return purchaseWrite<Supplier>('/suppliers', 'POST', payload); }

export async function updateSupplier(id: string, payload: Record<string, unknown>) {
  return purchaseWrite<Supplier>(`/suppliers/${encodeURIComponent(id)}`, 'PUT', payload);
}

export async function deleteSupplier(id: string) {
  return purchaseWrite<{ ok: boolean }>(`/suppliers/${encodeURIComponent(id)}`, 'DELETE');
}

export async function getPurchaseSummary(outletId: string) {
  try {
    const res = await fetchWithAuth(`/purchases/summary?outlet_id=${outletId}`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
}

export async function getPurchases(outletId: string, opts?: { unpaidOnly?: boolean; supplierId?: string }) {
  try {
    let url = `/purchases?outlet_id=${outletId}`;
    if (opts?.unpaidOnly) url += '&unpaid_only=true';
    if (opts?.supplierId) url += `&supplier_id=${opts.supplierId}`;
    const res = await fetchWithAuth(url);
    const data = await res.json();
    return data.data || [];
  } catch { return []; }
}

export async function createPurchase(payload: Record<string, unknown>) {
  return purchaseWrite<Purchase>('/purchases', 'POST', payload);
}

export async function payPurchase(id: string, payload: Record<string, unknown>) {
  return purchaseWrite<Purchase>(`/purchases/${encodeURIComponent(id)}/pay`, 'POST', payload);
}

async function purchaseRead<T>(path: string): Promise<T> {
  const res = await fetchWithAuth(path, { cache: 'no-store' });
  const body = await res.json();
  if (!res.ok || body.success === false || body.data == null) throw new Error(res.status >= 500
    ? 'Data pembelian belum bisa dimuat. Coba lagi.' : extractError(body, 'Data pembelian belum bisa dimuat.'));
  return body.data as T;
}

function purchaseError(error: unknown) {
  if (error instanceof Error && ['SESSION_EXPIRED', 'Unauthorized'].includes(error.message)) return 'Sesi berakhir. Masuk kembali untuk membuka pembelian.';
  return error instanceof Error && !/fetch failed|ECONN|ENOTFOUND|Unexpected token/i.test(error.message)
    ? error.message : 'Data pembelian belum bisa dimuat. Periksa koneksi lalu coba lagi.';
}

async function purchaseWrite<T>(path: string, method: string, payload?: Record<string, unknown>): Promise<PurchaseResult<T>> {
  try {
    const res = await fetchWithAuth(path, { method, body: payload ? JSON.stringify(payload) : undefined });
    const body = await res.json();
    if (!res.ok || body.success === false || body.data == null) return { success: false, uncertain: res.status >= 500,
      message: res.status >= 500 ? 'Hasil penyimpanan belum pasti. Coba periksa permintaan yang sama sebelum membuat catatan baru.' : extractError(body, 'Pembelian belum bisa disimpan.') };
    return { success: true, data: body.data as T, message: body.message };
  } catch (error) {
    const expired = error instanceof Error && ['SESSION_EXPIRED', 'Unauthorized'].includes(error.message);
    return { success: false, uncertain: !expired, message: expired ? purchaseError(error) : 'Koneksi terputus. Hasil penyimpanan belum pasti; periksa permintaan yang sama.' };
  }
}

export async function getPurchasingSetup(): Promise<PurchaseResult<PurchaseSetup>> {
  try {
    const [outlets, user] = await Promise.all([purchaseRead<PurchaseSetup['outlets']>('/outlets'), purchaseRead<{ subscription_tier: string }>('/users/me')]);
    const access = await businessAccess();
    return { success: true, data: { outlets, managed: access.managed,
      canManage: access.allows('purchasing.manage'), canRecord: access.allows('purchasing.manage') && access.allows('supplier.price.view'),
      canReceive: access.allows('stock.receive'), canCreateIngredient: access.allows('hpp.manage') && access.allows('hpp.approve'),
      canScan: access.allows('ai.chat') && access.allows('purchasing.manage') && access.allows('supplier.price.view'),
      selectedOutletId: (await cookies()).get('outlet_id')?.value,
      isPro: ['pro', 'business', 'enterprise'].includes(user.subscription_tier) } };
  } catch (error) { return { success: false, message: purchaseError(error) }; }
}

export async function getPurchasingData(outletId: string, reportMonth: string, filters: PurchaseFilters): Promise<PurchaseResult<PurchaseData>> {
  try {
    const query = new URLSearchParams({ outlet_id: outletId, limit: '51', skip: String(filters.skip || 0) });
    if (filters.month) query.set('month', filters.month);
    if (filters.unpaidOnly) query.set('unpaid_only', 'true');
    if (filters.search) query.set('search', filters.search);
    const [summary, rows, suppliers] = await Promise.all([
      purchaseRead<PurchaseSummary>(`/purchases/summary?outlet_id=${encodeURIComponent(outletId)}&month=${encodeURIComponent(reportMonth)}`),
      purchaseRead<Purchase[]>(`/purchases?${query}`),
      purchaseRead<Supplier[]>(`/suppliers?include_inactive=true&outlet_id=${encodeURIComponent(outletId)}`),
    ]);
    return { success: true, data: { summary, purchases: rows.slice(0, 50), hasNext: rows.length > 50, suppliers } };
  } catch (error) { return { success: false, message: purchaseError(error) }; }
}

export async function getPurchaseDetail(id: string): Promise<PurchaseResult<Purchase>> {
  try { return { success: true, data: await purchaseRead<Purchase>(`/purchases/${encodeURIComponent(id)}`) }; }
  catch (error) { return { success: false, message: purchaseError(error) }; }
}

export async function getPurchaseTargets(outletId: string, brandId: string, isPro: boolean): Promise<PurchaseResult<PurchaseTarget[]>> {
  try {
    const [products, ingredients] = await Promise.all([
      purchaseReadAll<{id: string; name: string; stock_enabled: boolean}>(`/products?brand_id=${encodeURIComponent(brandId)}&outlet_id=${encodeURIComponent(outletId)}`),
      isPro ? purchaseReadAll<{id: string; name: string; base_unit: string; ingredient_type?: string}>(`/ingredients?brand_id=${encodeURIComponent(brandId)}&outlet_id=${encodeURIComponent(outletId)}`) : Promise.resolve([]),
    ]);
    return { success: true, data: [
      ...ingredients.filter(i => i.ingredient_type !== 'overhead').map(i => ({key:`i:${i.id}`,id:i.id,name:i.name,kind:'ingredient' as const,unit:i.base_unit})),
      ...products.map(p => ({key:`p:${p.id}`,id:p.id,name:p.name,kind:'product' as const,unit:'pcs',stockEnabled:p.stock_enabled})),
    ] };
  } catch (error) { return { success: false, message: purchaseError(error) }; }
}

async function purchaseReadAll<T extends { id: string }>(path: string): Promise<T[]> {
  const rows: T[] = [], seen = new Set<string>();
  for (let skip = 0; ; skip += 200) {
    const batch = await purchaseRead<T[]>(`${path}&skip=${skip}&limit=200`);
    if (!Array.isArray(batch) || batch.some(row => seen.has(row.id))) throw new Error('Daftar barang berubah saat dimuat. Coba muat barang lagi.');
    batch.forEach(row => seen.add(row.id)); rows.push(...batch);
    if (batch.length < 200) return rows;
  }
}

/** Foto nota → baris terisi (Claude Vision). Endpoint lama /invoice-ocr/scan dipakai ulang. */
export async function scanInvoice(formData: FormData, outletId?: string) {
  try {
  const token = await getAuthToken();
  const cookieStore = await cookies();
  const tenantId = cookieStore.get('tenant_id')?.value;
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (tenantId) headers['X-Tenant-ID'] = tenantId;
  const res = await fetch(`${API_URL}/invoice-ocr/scan${outletId ? `?outlet_id=${encodeURIComponent(outletId)}` : ''}`, { method: 'POST', headers, body: formData });
  const data = await res.json();
  if (!res.ok || data.success === false) {
    return { success: false, message: res.status >= 500 ? 'Foto nota belum bisa dibaca. Isi manual atau coba lagi.' : extractError(data, 'Nota tidak terbaca'), data: null };
  }
  return { success: true, message: data.message, data: data.data };
  } catch { return { success: false, message: 'Koneksi terputus saat membaca foto. Catatan belum disimpan.', data: null }; }
}

// ── Keuangan (laba rugi, arus kas, pengeluaran) ───────────────────────

async function financeData<T>(path: string): Promise<T> {
  try {
    const res = await fetchWithAuth(path, { cache: 'no-store' });
    const data = await res.json();
    if (!res.ok || data.success === false || data.data == null) throw new Error(res.status < 500
      ? extractError(data, 'Data keuangan belum bisa dimuat.') : 'Data keuangan belum bisa dimuat. Coba lagi.');
    return data.data as T;
  } catch (error) {
    if (error instanceof Error && ['SESSION_EXPIRED', 'Unauthorized'].includes(error.message)) {
      throw new Error('Sesi berakhir. Masuk kembali untuk membuka keuangan.');
    }
    throw error;
  }
}

export async function getFinanceSetup(): Promise<FinanceResult<FinanceSetup>> {
  try {
  const access = await businessAccess();
  const [outlets, categories, accounts, suppliers] = await Promise.all([
    financeData<{ id: string; name: string }[]>('/outlets'),
    financeData<FinanceCategory[]>('/finance/categories'),
    financeData<FinanceAccount[]>('/finance/accounts'),
    financeData<{ id: string; name: string; is_active: boolean }[]>('/suppliers'),
  ]);
  const selectedOutletId = (await cookies()).get('outlet_id')?.value;
  return { success: true, data: { outlets, categories, accounts, suppliers: suppliers.filter(s => s.is_active), selectedOutletId,
    canManage: access.allows('finance.manage'), managed: access.managed, includeGlobal: access.includeGlobal } };
  } catch (error) { return { success: false, message: financeError(error) }; }
}

function financeError(error: unknown): string {
  return error instanceof Error && !/fetch failed|ECONN|ENOTFOUND|Unexpected token/i.test(error.message)
    ? error.message : 'Data keuangan belum bisa dimuat. Periksa koneksi lalu coba lagi.';
}

export async function getFinanceReport(outletId: string, month: string): Promise<FinanceResult<{ summary: FinanceSummary; expenses: FinanceExpense[] }>> {
  try {
    const [summary, expenses] = await Promise.all([getFinanceSummary(outletId, month), getExpenses(outletId, month)]);
    return { success: true, data: { summary, expenses } };
  } catch (error) { return { success: false, message: financeError(error) }; }
}

export async function getFinanceSummary(outletId: string, month: string) {
  return financeData<FinanceSummary>(`/finance/summary?outlet_id=${encodeURIComponent(outletId)}&month=${encodeURIComponent(month)}`);
}

export async function getFinanceCategories() {
  try { const res = await fetchWithAuth('/finance/categories'); return (await res.json()).data || []; } catch { return []; }
}

export async function getCashAccounts() {
  try { const res = await fetchWithAuth('/finance/accounts'); return (await res.json()).data || []; } catch { return []; }
}

export async function getExpenses(outletId: string, month: string) {
  return financeData<FinanceExpense[]>(`/finance/expenses?outlet_id=${encodeURIComponent(outletId)}&month=${encodeURIComponent(month)}`);
}

export async function createExpense(payload: Record<string, unknown>) {
  return financeWrite<FinanceExpense>('/finance/expenses', 'POST', payload);
}

export async function updateExpense(id: string, payload: Record<string, unknown>) {
  return financeWrite<FinanceExpense>(`/finance/expenses/${encodeURIComponent(id)}`, 'PUT', payload);
}

async function financeWrite<T>(path: string, method: string, payload?: Record<string, unknown>): Promise<FinanceResult<T>> {
  try {
    const res = await fetchWithAuth(path, { method, body: payload ? JSON.stringify(payload) : undefined });
    const data = await res.json();
    if (!res.ok || data.success === false) return { success: false, uncertain: res.status >= 500,
      message: res.status >= 500 ? 'Penyimpanan belum bisa dipastikan. Periksa hasil sebelum membuat catatan baru.' : extractError(data, 'Pengeluaran belum bisa disimpan.') };
    return { success: true, data: data.data as T, message: data.message };
  } catch (error) {
    const expired = error instanceof Error && ['SESSION_EXPIRED', 'Unauthorized'].includes(error.message);
    return { success: false, uncertain: !expired, message: expired ? 'Sesi berakhir. Masuk kembali untuk melanjutkan.' : 'Koneksi terputus. Hasil penyimpanan belum bisa dipastikan.' };
  }
}

export async function deleteExpense(id: string) {
  return financeWrite<{ ok: boolean }>(`/finance/expenses/${encodeURIComponent(id)}`, 'DELETE');
}

export async function copyRecurringExpenses(outletId: string, month: string) {
  return financeWrite<FinanceExpense[]>(`/finance/expenses/copy-recurring?outlet_id=${encodeURIComponent(outletId)}&month=${encodeURIComponent(month)}`, 'POST');
}

// ── WhatsApp toko (token Fonnte per outlet — promo dikirim dari nomor toko) ──
export async function setupOutletWhatsApp(outletId: string, fonnteToken: string) {
  const res = await fetchWithAuth(`/outlets/${outletId}/whatsapp-setup`, {
    method: 'POST',
    body: JSON.stringify({ fonnte_token: fonnteToken }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(extractError(data, 'Gagal menyimpan token Fonnte'));
  return { connected: !!data.data?.wa_connected, message: data.message as string };
}

// ── Kurir toko (delivery gelombang 2) ────────────────────────────────────
// Kurirnya orang toko, bukan armada agregator: toko daftarin sendiri siapa
// yang biasa nganter, kasir tinggal pilih, pelanggan lihat namanya.

export async function getCouriers(outletId?: string, includeInactive = false) {
  try {
    const qs = new URLSearchParams();
    if (outletId) qs.set('outlet_id', outletId);
    if (includeInactive) qs.set('include_inactive', 'true');
    const res = await fetchWithAuth(`/couriers/?${qs.toString()}`);
    const data = await res.json();
    return (data.data || []) as any[];
  } catch { return []; }
}

export async function createCourier(body: { name: string; phone?: string | null; vehicle?: string; outlet_id?: string | null }) {
  try {
    const res = await fetchWithAuth('/couriers/', { method: 'POST', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) return { success: false, message: extractError(data, 'Gagal menambah kurir') };
    return { success: true, data: data.data };
  } catch { return { success: false, message: 'Terjadi kesalahan jaringan' }; }
}

export async function updateCourier(id: string, body: any) {
  try {
    const res = await fetchWithAuth(`/couriers/${id}`, { method: 'PUT', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) return { success: false, message: extractError(data, 'Gagal menyimpan kurir') };
    return { success: true, data: data.data };
  } catch { return { success: false, message: 'Terjadi kesalahan jaringan' }; }
}

export async function deleteCourier(id: string) {
  try {
    const res = await fetchWithAuth(`/couriers/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) return { success: false, message: extractError(data, 'Gagal menghapus kurir') };
    return { success: true };
  } catch { return { success: false, message: 'Terjadi kesalahan jaringan' }; }
}
