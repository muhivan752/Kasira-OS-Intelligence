'use server';

import { cookies } from 'next/headers';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

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

  // Selalu gunakan trailing slash — hindari 307 redirect yang menghilangkan Authorization header
  const normalizedEndpoint = endpoint.replace(/^([^?]+?)(\?|$)/, (_, path, sep) =>
    path.endsWith('/') ? `${path}${sep}` : `${path}/${sep}`
  );

  const res = await fetch(`${API_URL}${normalizedEndpoint}`, { ...options, headers });
  if (res.status === 401) throw new Error('Unauthorized');
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

export async function getProducts(brandId: string) {
  try {
    const res = await fetchWithAuth(`/products?brand_id=${brandId}`);
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
    const res = await fetchWithAuth('/categories', {
      method: 'POST',
      body: JSON.stringify({ brand_id: brandId, name }),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat kategori' }; }
}

export async function updateCategory(categoryId: string, payload: { name?: string; is_active?: boolean }) {
  try {
    const res = await fetchWithAuth(`/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update kategori' }; }
}

export async function deleteCategory(categoryId: string) {
  try {
    const res = await fetchWithAuth(`/categories/${categoryId}`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

export async function createProduct(productData: any) {
  try {
    const res = await fetchWithAuth('/products', {
      method: 'POST',
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat produk' }; }
}

export async function updateProduct(productId: string, productData: any) {
  try {
    const res = await fetchWithAuth(`/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update produk' }; }
}

export async function deleteProduct(productId: string) {
  try {
    const res = await fetchWithAuth(`/products/${productId}`, { method: 'DELETE' });
    return res.ok;
  } catch { return false; }
}

export async function toggleProductActive(productId: string, isActive: boolean, rowVersion: number) {
  try {
    const res = await fetchWithAuth(`/products/${productId}`, {
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
    const res = await fetchWithAuth('/users/cashier', {
      method: 'POST',
      body: JSON.stringify(cashierData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail || 'Gagal membuat kasir' };
  } catch { return { success: false, message: 'Gagal membuat kasir' }; }
}

export async function toggleCashierActive(userId: string, isActive: boolean) {
  try {
    const res = await fetchWithAuth(`/users/${userId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.ok;
  } catch { return false; }
}

export async function resetCashierPin(userId: string, newPin: string) {
  try {
    const res = await fetchWithAuth(`/users/${userId}/pin`, {
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
    const res = await fetchWithAuth(`/outlets/${outletId}`, {
      method: 'PUT',
      body: JSON.stringify(outletData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message };
  } catch { return { success: false, message: 'Gagal update outlet' }; }
}

export async function setupPayment(outletId: string, paymentData: any) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup`, {
      method: 'POST',
      body: JSON.stringify(paymentData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal setup pembayaran' }; }
}

export async function setupPaymentOwnKey(outletId: string, xenditApiKey: string) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup/own-key`, {
      method: 'POST',
      body: JSON.stringify({ xendit_api_key: xenditApiKey }),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal menyimpan API key' }; }
}

export async function removePaymentOwnKey(outletId: string) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup/own-key`, { method: 'DELETE' });
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

export async function getWeeklyRevenue(outletId: string) {
  const data = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];
    try {
      const res = await fetchWithAuth(`/reports/daily?outlet_id=${outletId}&report_date=${dateStr}`);
      const json = await res.json();
      data.push({ name: d.toLocaleDateString('id-ID', { weekday: 'short' }), revenue: json.data?.total_revenue || 0 });
    } catch {
      data.push({ name: d.toLocaleDateString('id-ID', { weekday: 'short' }), revenue: 0 });
    }
  }
  return data;
}
