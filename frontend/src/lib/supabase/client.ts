// Client-side Supabase for React/Client Components
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";

export function createClientSupabase() {
  // Helpers read NEXT_PUBLIC_SUPABASE_* automatically and wire auth to cookies/local storage
  return createClientComponentClient();
}
