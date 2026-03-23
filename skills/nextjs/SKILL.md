# NEXT.JS SKILL

## App Router Default
// Server Component (default, lebih efisien)
export default async function MenuPage({ params }) {
  const menu = await getMenu(params.token); // server fetch
  return <MenuGrid menu={menu} />;
}
// Client Component hanya kalau butuh interaktif
"use client";
export function CartButton({ product }) { ... }

## Auth
// Owner dashboard: JWT dari Kasira backend
// Self-order: token dari URL params (no auth)
// middleware.ts
export function middleware(request) {
  const token = request.cookies.get('kasira_token');
  if (!token && !pathname.startsWith('/meja'))
    return redirect('/login');
}

## Realtime
// AI Chat: SSE
const response = await fetch('/api/v1/ai/chat/stream', {method:'POST'});
const reader = response.body.getReader();

// Order status: WebSocket
const ws = new WebSocket('wss://api.kasira.id/ws/table/'+tableId);
ws.onmessage = (e) => setOrderStatus(JSON.parse(e.data));

## Mobile-First (Self-Order)
- font-size minimum 16px (prevent iOS zoom)
- touch target minimum 44x44px
- Test di 375px width
