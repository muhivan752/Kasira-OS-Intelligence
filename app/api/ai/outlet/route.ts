import { cookies } from 'next/headers';

export async function GET() {
  const cookieStore = await cookies();
  const outletId = cookieStore.get('outlet_id')?.value;
  if (!outletId) {
    return new Response(JSON.stringify({ error: 'No outlet' }), { status: 404 });
  }
  return new Response(JSON.stringify({ outlet_id: outletId }), {
    headers: { 'Content-Type': 'application/json' },
  });
}
