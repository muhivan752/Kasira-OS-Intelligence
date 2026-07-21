import { NextRequest, NextResponse } from 'next/server';

// Proxy ke backend lewat jaringan internal Docker — sama seperti app/api/ai/route.ts.
// Browser nggak pernah nembak backend langsung, jadi nggak ada urusan CORS dan
// NEXT_PUBLIC_API_URL nggak perlu benar buat fitur ini jalan.
const API_URL =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://backend:8000/api/v1';

const FALLBACK = 'Waduh, lagi ada gangguan. Boleh lanjut tanya via WhatsApp ya 🙏';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const res = await fetch(`${API_URL}/landing/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Teruskan IP asli pengunjung — backend pakai buat counter pemakaian.
        'X-Forwarded-For':
          req.headers.get('cf-connecting-ip') ||
          req.headers.get('x-forwarded-for') ||
          '',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30000),
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      // Tampilkan pesan backend kalau ada (mis. kena batas), selain itu fallback.
      const detail =
        typeof data?.detail === 'string' ? data.detail : FALLBACK;
      return NextResponse.json({ reply: detail }, { status: 200 });
    }

    return NextResponse.json({ reply: data?.data?.reply ?? FALLBACK });
  } catch {
    // Chat landing nggak boleh nampilin error mentah ke calon pelanggan —
    // selalu balikin kalimat yang tetap ngarah ke WhatsApp.
    return NextResponse.json({ reply: FALLBACK }, { status: 200 });
  }
}
