"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { dashboardPathForRole, useAuth, UserRole } from "@/lib/auth-context";

export function RequireAuth({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: UserRole[];
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (roles && !roles.includes(user.role.name)) {
      router.replace(dashboardPathForRole(user.role.name));
    }
  }, [user, loading, roles, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen grid place-items-center text-navy-800">
        <div className="animate-pulse-soft text-sm tracking-wide">Loading Calibre…</div>
      </div>
    );
  }
  if (roles && !roles.includes(user.role.name)) return null;
  return <>{children}</>;
}
