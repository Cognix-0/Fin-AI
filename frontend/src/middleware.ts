import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_ROUTES = ['/dashboard', '/profile', '/expenses', '/settings'];

// Routes that should redirect authenticated users away (login/register)
const AUTH_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('access_token')?.value;
  const isAuthenticated = Boolean(token);

  // Redirect authenticated users away from login/register pages
  if (isAuthenticated && AUTH_ROUTES.some((r) => pathname.startsWith(r))) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Redirect unauthenticated users away from protected pages
  if (!isAuthenticated && PROTECTED_ROUTES.some((r) => pathname.startsWith(r))) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', pathname);   // preserve intended destination
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico
     * - public files
     */
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
};
