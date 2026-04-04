'use server';

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function getStorefront(slug: string) {
  if (!slug) return null;
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.data;
  } catch {
    return null;
  }
}

export async function createStorefrontOrder(slug: string, orderData: any) {
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData),
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      const errMsg = errBody.detail || `Gagal membuat pesanan (${res.status})`;
      return { success: false, data: null, message: errMsg };
    }
    const data = await res.json();
    // data.data = { order_id, display_number, status, estimated_minutes, payment: { method, status, qris_url, qris_expired_at } }
    return { success: true, data: data.data, message: data.message };
  } catch {
    return { success: false, data: null, message: 'Gagal menghubungi server' };
  }
}

export async function getStorefrontOrder(orderId: string) {
  if (!orderId) return null;
  try {
    const res = await fetch(`${BACKEND_URL}/connect/orders/${orderId}`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.data;
  } catch {
    return null;
  }
}

export async function getAvailableTables(slug: string) {
  if (!slug) return [];
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}/tables`, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return data.data;
  } catch {
    return [];
  }
}

export async function createBooking(slug: string, bookingData: any) {
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}/booking`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bookingData),
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      return { success: false, data: null, message: errBody.detail || `Gagal membuat booking (${res.status})` };
    }
    const data = await res.json();
    return { success: true, data: data.data, message: data.message };
  } catch {
    return { success: false, data: null, message: 'Gagal menghubungi server' };
  }
}

export async function getBookingStatus(bookingId: string) {
  if (!bookingId) return null;
  try {
    const res = await fetch(`${BACKEND_URL}/connect/bookings/${bookingId}`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.data;
  } catch {
    return null;
  }
}

