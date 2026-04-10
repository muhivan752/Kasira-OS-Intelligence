import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login', '/register', '/onboarding', '/api'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public paths and storefront ([slug])
  if (
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    pathname === '/' ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon')
  ) {
    return NextResponse.next();
  }

  // Protect /dashboard/*
  const token = request.cookies.get('token')?.value;
  if (!token && pathname.startsWith('/dashboard')) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*'],
};
