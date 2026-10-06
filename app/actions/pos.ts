'use server';

import { cookies } from 'next/headers';

type Result = { success: true; data: any } | { success: false; message: string; uncertain: boolean };
const base = (process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');

async function call(path: string, body?: unknown): Promise<Result> {
  const jar = await cookies();
  try {
    const response = await fetch(`${base}${path}`, { method: body ? 'POST' : 'GET', cache: 'no-store', signal: AbortSignal.timeout(20000),
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jar.get('token')?.value || ''}`, 'X-Tenant-ID': jar.get('tenant_id')?.value || '' },
      ...(body ? { body: JSON.stringify(body) } : {}) });
    const value = await response.json();
    if (!response.ok) return { success: false, uncertain: !!body && response.status >= 500,
      message: typeof value.detail === 'string' ? value.detail : value.detail?.message || 'Permintaan ditolak. Periksa data dan izin akun.' };
    return { success: true, data: value.data };
  } catch { return { success: false, uncertain: !!body, message: body ? 'Hasil pencatatan belum pasti. Muat ulang stok dan periksa sebelum mencatat lagi.' : 'Stok belum dapat dimuat. Periksa koneksi lalu coba lagi.' }; }
}

export async function getOperationalStock(outletId: string): Promise<Result> {
  const outlet = await call(`/outlets/${encodeURIComponent(outletId)}`);
  if (!outlet.success) return outlet;
  const query = new URLSearchParams({ outlet_id: outletId, brand_id: outlet.data.brand_id, limit: '1000' });
  const products = await call(`/products/?${query}`);
  if (!products.success) return products;
  let ingredients: any[] = [];
  if (outlet.data.stock_mode === 'recipe') {
    const result = await call(`/ingredients/?${query}`);
    if (!result.success) return result;
    ingredients = result.data;
  }
  return { success: true, data: { outlet: outlet.data, products: products.data, ingredients } };
}

export async function recordOperationalStock(kind: 'product' | 'ingredient', id: string, outletId: string, action: 'receive' | 'count', quantity: number): Promise<Result> {
  if (!['product', 'ingredient'].includes(kind) || !['receive', 'count'].includes(action) || !Number.isFinite(quantity) || kind === 'product' && !Number.isInteger(quantity) || quantity < 0 || (action === 'receive' && quantity === 0) || (kind === 'ingredient' && action === 'count'))
    return { success: false, uncertain: false, message: 'Jumlah atau tindakan stok tidak valid.' };
  return call(`/${kind === 'product' ? 'products' : 'ingredients'}/${encodeURIComponent(id)}/${action === 'count' ? 'stock-count' : 'restock'}`,
    { outlet_id: outletId, ...(action === 'count' ? { counted_qty: quantity } : { quantity }) });
}
