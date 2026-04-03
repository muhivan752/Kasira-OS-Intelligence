'use server';

export async function getStorefront(slug: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
    const url = `${baseUrl}/connect/${slug}`;
    const res = await fetch(url, {
      cache: 'no-store',
    });
    if (!res.ok) {
      console.warn(`Backend not reachable (status ${res.status}), using mock data for storefront.`);
      // Fallback to mock data for demo purposes if backend is not running
      return getMockStorefront(slug);
    }
    const data = await res.json();
    return data.data;
  } catch (error) {
    console.warn(`Backend not reachable, using mock data for storefront.`);
    // Fallback to mock data for demo purposes if backend is not running
    return getMockStorefront(slug);
  }
}

// Mock data generator for demo purposes
function getMockStorefront(slug: string) {
  return {
    outlet: {
      id: 'mock-outlet-1',
      name: `Warung ${slug.charAt(0).toUpperCase() + slug.slice(1)}`,
      address: 'Jl. Demo No. 123, Jakarta',
      phone: '081234567890',
      is_open: true,
      tier: 'premium',
      opening_hours: '08:00 - 22:00',
      logo_url: null
    },
    categories: [
      { id: 'cat-1', name: 'Makanan Utama' },
      { id: 'cat-2', name: 'Minuman' },
      { id: 'cat-3', name: 'Cemilan' }
    ],
    products: [
      {
        id: 'prod-1',
        name: 'Nasi Goreng Spesial',
        description: 'Nasi goreng dengan telur, ayam, dan kerupuk',
        price: 25000,
        stock: 10,
        category_id: 'cat-1',
        image_url: 'https://picsum.photos/seed/nasigoreng/400/400'
      },
      {
        id: 'prod-2',
        name: 'Mie Goreng Seafood',
        description: 'Mie goreng dengan udang dan cumi',
        price: 30000,
        stock: 5,
        category_id: 'cat-1',
        image_url: 'https://picsum.photos/seed/miegoreng/400/400'
      },
      {
        id: 'prod-3',
        name: 'Es Teh Manis',
        description: 'Teh manis dingin menyegarkan',
        price: 5000,
        stock: 50,
        category_id: 'cat-2',
        image_url: 'https://picsum.photos/seed/esteh/400/400'
      },
      {
        id: 'prod-4',
        name: 'Kopi Susu Gula Aren',
        description: 'Kopi susu dengan gula aren asli',
        price: 18000,
        stock: 20,
        category_id: 'cat-2',
        image_url: 'https://picsum.photos/seed/kopisusu/400/400'
      },
      {
        id: 'prod-5',
        name: 'Kentang Goreng',
        description: 'Kentang goreng renyah dengan saus sambal',
        price: 15000,
        stock: 15,
        category_id: 'cat-3',
        image_url: 'https://picsum.photos/seed/kentang/400/400'
      }
    ]
  };
}

export async function createStorefrontOrder(slug: string, orderData: any) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/${slug}/order`, {
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
  } catch (error) {
    console.warn(`Backend not reachable, using mock data for order creation.`);
    const mockExpiry = new Date(Date.now() + 15 * 60 * 1000).toISOString();
    return {
      success: true,
      data: {
        order_id: 'mock-order-' + Date.now(),
        display_number: 1,
        status: 'pending',
        estimated_minutes: 15,
        payment: {
          method: orderData.payment_method || 'qris',
          status: 'pending',
          qris_url: null,
          qris_expired_at: mockExpiry,
        },
      },
      message: 'Pesanan berhasil dibuat (Mock)',
    };
  }
}

export async function getStorefrontOrder(orderId: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/orders/${orderId}`, {
      cache: 'no-store',
    });
    if (!res.ok) {
      console.warn(`Backend not reachable (status ${res.status}), using mock data for order fetch.`);
      // Fallback to mock data for demo purposes if backend is not running
      return getMockOrder(orderId);
    }
    const data = await res.json();
    return data.data;
  } catch (error) {
    console.warn(`Backend not reachable, using mock data for order fetch.`);
    // Fallback to mock data for demo purposes if backend is not running
    return getMockOrder(orderId);
  }
}

export async function getAvailableTables(slug: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/${slug}/tables`, { cache: 'no-store' });
    if (!res.ok) return getMockTables();
    const data = await res.json();
    return data.data;
  } catch {
    return getMockTables();
  }
}

export async function createBooking(slug: string, bookingData: any) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/${slug}/booking`, {
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
    return {
      success: true,
      data: {
        booking_id: 'mock-booking-' + Date.now(),
        customer_name: bookingData.customer_name,
        reservation_time: bookingData.reservation_time,
        guest_count: bookingData.guest_count,
        table_name: null,
        status: 'pending',
      },
      message: 'Booking berhasil dibuat (Mock)',
    };
  }
}

export async function getBookingStatus(bookingId: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/bookings/${bookingId}`, { cache: 'no-store' });
    if (!res.ok) return getMockBooking(bookingId);
    const data = await res.json();
    return data.data;
  } catch {
    return getMockBooking(bookingId);
  }
}

function getMockTables() {
  return [
    { id: 'tbl-1', name: 'Meja 1', capacity: 2, status: 'available' },
    { id: 'tbl-2', name: 'Meja 2', capacity: 4, status: 'available' },
    { id: 'tbl-3', name: 'Meja 3', capacity: 6, status: 'available' },
    { id: 'tbl-4', name: 'Meja VIP', capacity: 8, status: 'available' },
  ];
}

function getMockBooking(bookingId: string) {
  return {
    booking_id: bookingId,
    customer_name: 'Demo Customer',
    customer_phone: '081234567890',
    reservation_time: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    guest_count: 2,
    table_name: 'Meja 1',
    status: 'pending',
    notes: null,
    outlet: { name: 'Warung Demo', phone: '081234567890' },
  };
}

function getMockOrder(orderId: string) {
  return {
    id: orderId,
    order_number: 'ORD-MOCK-001',
    display_number: 1,
    status: 'pending',
    order_type: 'pickup',
    payment_method: 'qris',
    total_amount: 50000,
    created_at: new Date().toISOString(),
    estimated_minutes: 15,
    delivery_address: null,
    items: [
      {
        id: 'item-1',
        product_name: 'Nasi Goreng Spesial',
        quantity: 2,
        price: 25000,
        subtotal: 50000,
        notes: null,
      }
    ],
    outlet: {
      name: 'Warung Demo',
      phone: '081234567890'
    },
    payment: {
      method: 'qris',
      status: 'pending',
      qris_url: null,
      qris_expired_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
    },
  };
}
