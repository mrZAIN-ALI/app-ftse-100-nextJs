// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req, res })

  const {
    data: { session },
  } = await supabase.auth.getSession()

  const { pathname, search } = req.nextUrl
  const isRoot = pathname === '/'
  const isAuthRoute = pathname === '/signin' || pathname.startsWith('/auth/')

  if (!session && !isAuthRoute) {
    const url = req.nextUrl.clone()
    url.pathname = '/signin'
    if (pathname && pathname !== '/') {
      url.searchParams.set('redirectedFrom', pathname + (search || ''))
    }
    return NextResponse.redirect(url)
  }

  if (session && (isRoot || isAuthRoute)) {
    const url = req.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return res
}

export const config = {
  matcher: [
    '/',
    '/signin',
    '/dashboard',
    '/history',
    '/settings',
    '/auth/:path*',
    '/(protected)/(.*)',
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
