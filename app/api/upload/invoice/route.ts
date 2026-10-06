import { NextRequest, NextResponse } from 'next/server';

const backendUrl = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000/api/v1';

export async function POST(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  if (!token) return NextResponse.json({ success: false, message: 'Masuk kembali untuk membaca nota.' }, { status: 401 });
  const outlet = request.nextUrl.searchParams.get('outlet_id');
  if (!outlet || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(outlet)) {
    return NextResponse.json({ success: false, message: 'Pilih outlet untuk membaca nota.' }, { status: 400 });
  }
  if (Number(request.headers.get('content-length') || 0) > 9 * 1024 * 1024) return NextResponse.json({ success: false, message: 'Foto maksimal 8 MB.' }, { status: 413 });
  try {
    const form = await request.formData(), file = form.get('file');
    if (!(file instanceof File) || !['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
      return NextResponse.json({ success: false, message: 'Pilih foto JPG, PNG, atau WebP maksimal 8 MB.' }, { status: 400 });
    }
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    const tenant = request.cookies.get('tenant_id')?.value;
    if (tenant) headers['X-Tenant-ID'] = tenant;
    const body = new FormData(); body.append('file', file);
    const response = await fetch(`${backendUrl}/invoice-ocr/scan?outlet_id=${encodeURIComponent(outlet)}`, { method: 'POST', headers, body });
    const result = await response.json();
    if (!response.ok) return NextResponse.json({ success: false, message: response.status >= 500
      ? 'Foto nota belum bisa dibaca. Isi manual atau coba lagi.' : typeof result.detail === 'string' ? result.detail : 'Foto belum bisa dibaca.' }, { status: response.status });
    return NextResponse.json(result);
  } catch { return NextResponse.json({ success: false, message: 'Koneksi terputus saat membaca foto. Catatan belum disimpan.' }, { status: 502 }); }
}
