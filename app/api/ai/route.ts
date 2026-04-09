import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

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

  const backendRes = await fetch(`${API_URL}/api/v1/ai/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  // Pass through status for error responses
  if (!backendRes.ok) {
    const errBody = await backendRes.text();
    return new Response(errBody, {
      status: backendRes.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Stream SSE through
  return new Response(backendRes.body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
