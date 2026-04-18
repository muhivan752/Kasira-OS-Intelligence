import { cookies } from 'next/headers';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function GET() {
  const cookieStore = await cookies();
  let outletId = cookieStore.get('outlet_id')?.value;

  // Fallback: kalau cookie gak ada (session lama), fetch dari /auth/me
  if (!outletId) {
    const token = cookieStore.get('token')?.value;
    const tenantId = cookieStore.get('tenant_id')?.value;
    if (!token) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
    }
    try {
      const headers: Record<string, string> = { 'Authorization': `Bearer ${token}` };
      if (tenantId) headers['X-Tenant-ID'] = tenantId;
      const res = await fetch(`${API_URL}/auth/me`, { headers });
      if (res.ok) {
        const body = await res.json();
        outletId = body?.data?.outlet_id;
        if (outletId) {
          // Set cookie untuk next request
          cookieStore.set({
            name: 'outlet_id',
            value: outletId,
            httpOnly: true,
            path: '/',
            maxAge: 60 * 60 * 24 * 7,
          });
        }
      }
    } catch {}
  }

  if (!outletId) {
    return new Response(JSON.stringify({ error: 'No outlet' }), { status: 404 });
  }
  return new Response(JSON.stringify({ outlet_id: outletId }), {
    headers: { 'Content-Type': 'application/json' },
  });
}
