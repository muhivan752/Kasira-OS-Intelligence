import { NextRequest, NextResponse } from 'next/server';

// Gunakan URL internal Docker — server-side code berjalan di container, bukan browser
const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function POST(req: NextRequest) {
  const token = req.cookies.get('token')?.value;
  const tenantId = req.cookies.get('tenant_id')?.value;

  if (!token) {
    return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
  }

  // Pipe raw body langsung — jangan parse FormData, agar Content-Type boundary tetap utuh
  const contentType = req.headers.get('content-type') || '';
  const body = await req.arrayBuffer();

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Content-Type': contentType,
  };
  if (tenantId) headers['X-Tenant-ID'] = tenantId;

  try {
    const res = await fetch(`${BACKEND_URL}/media/upload`, {
      method: 'POST',
      headers,
      body,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ detail: 'Gagal menghubungi server' }, { status: 502 });
  }
}
