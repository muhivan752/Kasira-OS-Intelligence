export async function getStorefront(slug: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/${slug}`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.data;
  } catch (error) {
    console.error('Failed to fetch storefront:', error);
    return null;
  }
}

export async function createStorefrontOrder(slug: string, orderData: any) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/${slug}/order`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderData),
    });
    const data = await res.json();
    return { success: res.ok, data: data.data, message: data.message || data.detail };
  } catch (error) {
    console.error('Failed to create order:', error);
    return { success: false, message: 'Gagal membuat pesanan' };
  }
}

export async function getStorefrontOrder(orderId: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const res = await fetch(`${baseUrl}/connect/order/${orderId}`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.data;
  } catch (error) {
    console.error('Failed to fetch order:', error);
    return null;
  }
}
