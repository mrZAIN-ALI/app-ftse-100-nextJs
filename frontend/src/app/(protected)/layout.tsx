import { ReactNode } from "react";
import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase/server";
import AppShell from "@/components/AppShell";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function ProtectedLayout({ children }: { children: ReactNode }) {
  const supabase = createServerSupabase();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) redirect("/signin");

  const { data: { user } } = await supabase.auth.getUser();

  const simpleUser = user
    ? {
        email: user.email ?? null,
        name:
          (user.user_metadata as any)?.full_name ||
          (user.user_metadata as any)?.name ||
          null,
        imageUrl:
          (user.user_metadata as any)?.avatar_url ||
          (user.user_metadata as any)?.picture ||
          null,
      }
    : null;

  return <AppShell user={simpleUser}>{children}</AppShell>;
}
