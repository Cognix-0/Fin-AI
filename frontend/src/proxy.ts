import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_ROUTES = [
  '/dashboard', '/profile', '/expenses', '/approvals', '/budgets', '/reports', '/settings',
];

// Routes that should redirect authenticated users away (login/register)
const AUTH_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password'];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  // The access cookie is short-lived; a refresh cookie means the client can
  // silently renew the session (lib/api/client.ts), so treat either as signed in.
  const hasAccess = Boolean(request.cookies.get('access_token')?.value);
  const isAuthenticated = hasAccess || Boolean(request.cookies.get('refresh_token')?.value);

  // Redirect signed-in users away from login/register pages. Only a live access
  // cookie counts here: a leftover (possibly stale) refresh cookie must never
  // lock the user out of /login, or a dead session becomes a redirect trap.
  if (hasAccess && AUTH_ROUTES.some((r) => pathname.startsWith(r))) {
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
