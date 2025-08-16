import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(request: Request) {
  const url = new URL(request.url);
  const next = url.searchParams.get("next") ?? "/dashboard";
  const err = url.searchParams.get("error") || url.searchParams.get("error_description");
  const code = url.searchParams.get("code");

  if (err) {
    return NextResponse.redirect(new URL(`/signin?err=${encodeURIComponent(err)}`, url.origin));
  }

  if (!code) {
    // If you still see this, Google is not redirecting via Supabase with PKCE.
    return NextResponse.redirect(new URL(`/signin?err=${encodeURIComponent("Missing OAuth code")}`, url.origin));
  }

  const supabase = createRouteHandlerClient({ cookies });
  try {
    await supabase.auth.exchangeCodeForSession(code); // attaches Set-Cookie to response internally
  } catch (e: any) {
    return NextResponse.redirect(
      new URL(`/signin?err=${encodeURIComponent(e?.message ?? "Auth exchange failed")}`, url.origin)
    );
  }

  // Success → go where user intended
  return NextResponse.redirect(new URL(next, url.origin));
}
