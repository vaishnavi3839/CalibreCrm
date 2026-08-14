"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { dashboardPathForRole, useAuth } from "@/lib/auth-context";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else router.replace(dashboardPathForRole(user.role.name));
  }, [user, loading, router]);

  return (
    <div className="min-h-screen grid place-items-center">
      <div className="text-navy-800">Redirecting…</div>
    </div>
  );
}
