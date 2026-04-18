import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function POST(req: NextRequest) {
  const cookieStore = await cookies();
  const token = cookieStore.get('token')?.value;
  const tenantId = cookieStore.get('tenant_id')?.value;

  if (!token) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }

  const body = await req.json();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
  if (tenantId) headers['X-Tenant-ID'] = tenantId;

  const backendRes = await fetch(`${API_URL}/ai/apply-recipe`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  const text = await backendRes.text();
  return new Response(text, {
    status: backendRes.status,
    headers: { 'Content-Type': 'application/json' },
  });
}
