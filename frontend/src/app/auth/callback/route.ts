// frontend/src/app/auth/callback/route.ts
import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export async function GET(request: Request) {
  const url = new URL(request.url)
  const next = url.searchParams.get('next') ?? '/dashboard'
  const err = url.searchParams.get('error') || url.searchParams.get('error_description')
  const code = url.searchParams.get('code')

  if (err) {
    return NextResponse.redirect(new URL(`/signin?err=${encodeURIComponent(err)}`, url.origin))
  }

  if (!code) {
    return NextResponse.redirect(new URL(`/signin?err=${encodeURIComponent('Missing OAuth code')}`, url.origin))
  }

  const supabase = createRouteHandlerClient({ cookies })
  try {
    await supabase.auth.exchangeCodeForSession(code)
  } catch (e: any) {
    return NextResponse.redirect(
      new URL(`/signin?err=${encodeURIComponent(e?.message ?? 'Auth exchange failed')}`, url.origin)
    )
  }

  return NextResponse.redirect(new URL(next, url.origin))
}
