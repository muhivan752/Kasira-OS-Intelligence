import { cookies } from 'next/headers';
import { getAccountAccess } from '@/app/actions/accounts';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function GET() {
  const cookieStore = await cookies();
  let outletId = cookieStore.get('outlet_id')?.value;
  const access = await getAccountAccess();
  if (!access.success) return Response.json({ error: access.message }, { status: 401 });
  if (access.data.enforcement_mode === 'managed') {
    if (!access.data.permissions.includes('ai.chat')) return Response.json({ error: 'Akses AI belum diberikan.' }, { status: 403 });
    const permitted = access.data.outlets;
    outletId = permitted.find((outlet: { id: string }) => outlet.id === outletId)?.id || permitted[0]?.id;
    if (!outletId) return Response.json({ error: 'Belum ada outlet aktif dalam akses akun.' }, { status: 404 });
    return Response.json({ outlet_id: outletId, outlets: permitted,
      can_draft: ['ai.chat', 'hpp.view', 'hpp.manage', 'supplier.price.view'].every(permission => access.data.permissions.includes(permission)) });
  }

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
