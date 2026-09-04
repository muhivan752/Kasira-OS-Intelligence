import { NextRequest, NextResponse } from 'next/server';

// Server-side jalan di container, pakai URL internal Docker.
const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

/**
 * Unggah bukti bayar dari halaman publik (lacak pesanan, lacak reservasi).
 * Publik: tidak ada token, kuncinya id pembayaran (UUID acak). Body multipart
 * diteruskan mentah supaya boundary Content-Type tetap utuh, sama seperti
 * /api/upload untuk dashboard.
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ paymentId: string }> }) {
  const { paymentId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(paymentId)) {
    return NextResponse.json({ detail: 'Id pembayaran tidak valid' }, { status: 400 });
  }
  const contentType = req.headers.get('content-type') || '';
  const body = await req.arrayBuffer();
  try {
    const res = await fetch(`${BACKEND_URL}/connect/payments/${paymentId}/proof`, {
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
