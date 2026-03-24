'use server';

import { cookies } from 'next/headers';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function getAuthToken() {
  const cookieStore = await cookies();
  const token = cookieStore.get('token')?.value;
  return token;
}

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Unauthorized');
  }

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    throw new Error('Unauthorized');
  }

  return res;
}

export async function getCurrentUser() {
  try {
    const res = await fetchWithAuth('/users/me');
    const data = await res.json();
    return data.data;
  } catch (error) {
    return null;
  }
}

export async function getOutlets() {
  try {
    const res = await fetchWithAuth('/outlets');
    const data = await res.json();
    return data.data;
  } catch (error) {
    return [];
  }
}

export async function getProducts(outletId: string) {
  try {
    const res = await fetchWithAuth(`/products?outlet_id=${outletId}`);
    const data = await res.json();
    return data.data;
  } catch (error) {
    return [];
  }
}

export async function getCategories(outletId: string) {
  try {
    const res = await fetchWithAuth(`/categories?outlet_id=${outletId}`);
    const data = await res.json();
    return data.data;
  } catch (error) {
    return [];
  }
}

export async function createProduct(productData: any) {
  try {
    const res = await fetchWithAuth('/products', {
      method: 'POST',
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message };
  } catch (error) {
    return { success: false, message: 'Gagal membuat produk' };
  }
}

export async function updateProduct(productId: string, productData: any) {
  try {
    const res = await fetchWithAuth(`/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify(productData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message };
  } catch (error) {
    return { success: false, message: 'Gagal update produk' };
  }
}

export async function toggleProductActive(productId: string, isActive: boolean) {
  try {
    const res = await fetchWithAuth(`/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}
export async function getCashiers(outletId: string) {
  try {
    const res = await fetchWithAuth(`/users?outlet_id=${outletId}&role=cashier`);
    const data = await res.json();
    return data.data;
  } catch (error) {
    return [];
  }
}

export async function createCashier(cashierData: any) {
  try {
    const res = await fetchWithAuth('/users/cashier', {
      method: 'POST',
      body: JSON.stringify(cashierData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message };
  } catch (error) {
    return { success: false, message: 'Gagal membuat kasir' };
  }
}

export async function toggleCashierActive(userId: string, isActive: boolean) {
  try {
    const res = await fetchWithAuth(`/users/${userId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function resetCashierPin(userId: string, newPin: string) {
  try {
    const res = await fetchWithAuth(`/users/${userId}/pin`, {
      method: 'PUT',
      body: JSON.stringify({ pin: newPin }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}
export async function getOrders(outletId: string, startDate?: string, endDate?: string) {
  try {
    let url = `/orders?outlet_id=${outletId}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    
    const res = await fetchWithAuth(url);
    const data = await res.json();
    return data.data;
  } catch (error) {
    return [];
  }
}
export async function updateOutlet(outletId: string, outletData: any) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}`, {
      method: 'PUT',
      body: JSON.stringify(outletData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message };
  } catch (error) {
    return { success: false, message: 'Gagal update outlet' };
  }
}
export async function setupPayment(outletId: string, paymentData: any) {
  try {
    const res = await fetchWithAuth(`/outlets/${outletId}/payment-setup`, {
      method: 'POST',
      body: JSON.stringify(paymentData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch (error) {
    return { success: false, message: 'Gagal setup pembayaran' };
  }
}
export async function getDailyReport(outletId: string, date: string) {
  try {
    const res = await fetchWithAuth(`/reports/daily?outlet_id=${outletId}&date=${date}`);
    const data = await res.json();
    return data.data;
  } catch (error) {
    return null;
  }
}

export async function getWeeklyRevenue(outletId: string) {
  // Mocking 7 days data for now, since the backend might not have this specific endpoint yet
  // We can fetch daily report for the last 7 days
  const data = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];
    try {
      const res = await fetchWithAuth(`/reports/daily?outlet_id=${outletId}&date=${dateStr}`);
      const json = await res.json();
      data.push({
        name: d.toLocaleDateString('id-ID', { weekday: 'short' }),
        revenue: json.data?.total_revenue || 0
      });
    } catch (e) {
      data.push({
        name: d.toLocaleDateString('id-ID', { weekday: 'short' }),
        revenue: 0
      });
    }
  }
  return data;
}
