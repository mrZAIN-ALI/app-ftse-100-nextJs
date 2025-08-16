// Server-side Supabase for Server Components / RSC
import { cookies } from "next/headers";
import { createServerComponentClient } from "@supabase/auth-helpers-nextjs";

export function createServerSupabase() {
  return createServerComponentClient({ cookies });
}
