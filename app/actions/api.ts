'use server';

import { cookies } from 'next/headers';

// Gunakan internal Docker URL untuk server actions (lebih cepat, bypass Nginx)
const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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
    // Clear auth cookies on 401 and redirect
    const { cookies: getCookies } = await import('next/headers');
    const cookieStore = await getCookies();
    cookieStore.delete('token');
    cookieStore.delete('tenant_id');
    cookieStore.delete('outlet_id');
    const { redirect } = await import('next/navigation');
    redirect('/login');
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

export async function getReportSummary(outletId: string, startDate: string, endDate: string) {
  try {
    const res = await fetchWithAuth(`/reports/summary?outlet_id=${outletId}&start_date=${startDate}&end_date=${endDate}`);
    const data = await res.json();
    return data.data;
  } catch { return null; }
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
    const res = await fetchWithAuth(`/reservations?outlet_id=${outletId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat reservasi' }; }
}

export async function confirmReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/confirm`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal konfirmasi reservasi' }; }
}

export async function seatReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/seat`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal mengubah status reservasi' }; }
}

export async function completeReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/complete`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal menyelesaikan reservasi' }; }
}

export async function cancelReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/cancel`, { method: 'PUT' });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membatalkan reservasi' }; }
}

export async function noShowReservation(id: string) {
  try {
    const res = await fetchWithAuth(`/reservations/${id}/no-show`, { method: 'PUT' });
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
    const res = await fetchWithAuth(`/reservations/settings/${outletId}`, {
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
    const res = await fetchWithAuth(`/tables?outlet_id=${outletId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal membuat meja' }; }
}

export async function updateTable(id: string, payload: any) {
  try {
    const res = await fetchWithAuth(`/tables/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch { return { success: false, message: 'Gagal update meja' }; }
}

export async function deleteTable(id: string) {
  try {
    const res = await fetchWithAuth(`/tables/${id}`, { method: 'DELETE' });
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
  const res = await fetchWithAuth(`/ingredients/${id}/restock`, {
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
  const res = await fetchWithAuth('/recipes', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal membuat resep');
  return data.data;
}

export async function updateRecipe(id: string, payload: any) {
  const res = await fetchWithAuth(`/recipes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal mengupdate resep');
  return data.data;
}

export async function deleteRecipe(id: string) {
  try {
    const res = await fetchWithAuth(`/recipes/${id}`, { method: 'DELETE' });
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

export async function updateStockMode(outletId: string, stockMode: string) {
  const res = await fetchWithAuth(`/outlets/${outletId}/stock-mode`, {
    method: 'PUT',
    body: JSON.stringify({ stock_mode: stockMode }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal mengubah mode stok');
  return data.data;
}
