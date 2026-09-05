import { NextRequest, NextResponse } from 'next/server';

// Server-side jalan di container, pakai URL internal Docker.
const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

/**
 * Proxy halaman tugas kurir (delivery gelombang 2b). Publik: kuncinya token
 * `k` di query yang diteruskan apa adanya ke backend. POST multipart (foto
 * serah terima) diteruskan mentah supaya boundary Content-Type tetap utuh,
 * sama seperti /api/proof.
 */
function check(slug: string, orderId: string) {
  return /^[a-z0-9-]{1,80}$/i.test(slug) && /^[0-9a-f-]{36}$/i.test(orderId);
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ slug: string; orderId: string }> }) {
  const { slug, orderId } = await params;
  if (!check(slug, orderId)) return NextResponse.json({ detail: 'Link tidak valid' }, { status: 400 });
  const k = req.nextUrl.searchParams.get('k') || '';
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}/antar/${orderId}?k=${encodeURIComponent(k)}`, { cache: 'no-store' });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Gagal menghubungi server' }, { status: 502 });
  }
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ slug: string; orderId: string }> }) {
  const { slug, orderId } = await params;
  if (!check(slug, orderId)) return NextResponse.json({ detail: 'Link tidak valid' }, { status: 400 });
  const k = req.nextUrl.searchParams.get('k') || '';
  const action = req.nextUrl.searchParams.get('action') === 'failed' ? 'failed' : 'delivered';
  const contentType = req.headers.get('content-type') || '';
  const body = await req.arrayBuffer();
  try {
    const res = await fetch(`${BACKEND_URL}/connect/${slug}/antar/${orderId}/${action}?k=${encodeURIComponent(k)}`, {
      method: 'POST',
      headers: { 'Content-Type': contentType },
      body,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Gagal menghubungi server' }, { status: 502 });
  }
}
