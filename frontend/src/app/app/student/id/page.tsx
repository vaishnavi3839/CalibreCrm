"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function StudentIdPage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/students/me/profile").then((res) => setProfile(res.data)).catch(() => null);
  }, []);

  const photo =
    profile?.photo_url ||
    user?.photo_url ||
    null;

  return (
    <RequireAuth roles={["student"]}>
      <AppShell title="Digital ID Card">
        <div className="mx-auto max-w-sm overflow-hidden rounded-3xl bg-navy-900 text-white shadow-xl">
          <div className="bg-[linear-gradient(135deg,rgba(74,159,216,0.35),transparent_55%),linear-gradient(225deg,rgba(196,163,90,0.3),transparent_40%)] p-6">
            <div className="text-xs uppercase tracking-[0.2em] text-sky-300">Calibre Aviation Academy</div>
            <div className="mt-6 flex items-center gap-4">
              {photo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={photo} alt="" className="h-20 w-20 rounded-2xl object-cover" />
              ) : (
                <div className="grid h-20 w-20 place-items-center rounded-2xl bg-white/10 text-2xl font-semibold">
                  {(profile?.name || user?.full_name || "?").slice(0, 1)}
                </div>
              )}
              <div>
                <div className="font-[family-name:var(--font-display)] text-xl">{profile?.name || user?.full_name}</div>
                <div className="mt-1 text-sm text-white/70">{profile?.student_code}</div>
              </div>
            </div>
            <div className="mt-6 space-y-2 text-sm">
              <div className="flex justify-between border-t border-white/10 pt-2">
                <span className="text-white/60">Course</span>
                <span>{profile?.course || "—"}</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-2">
                <span className="text-white/60">Batch</span>
                <span>{profile?.batch || "—"}</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-2">
                <span className="text-white/60">Days present</span>
                <span>{profile?.days_present ?? "—"} / {profile?.days_total ?? "—"}</span>
              </div>
            </div>
            <div className="mt-6 rounded-xl bg-white/10 p-3 text-center text-xs tracking-wider text-brass-400">
              QR · {profile?.student_code || "VERIFY"}
            </div>
          </div>
        </div>
        <p className="mx-auto mt-4 max-w-sm text-center text-sm text-muted">
          <Link href="/app/profile" className="text-sky-500 hover:underline">Update your photo</Link> to show it on this ID card.
        </p>
      </AppShell>
    </RequireAuth>
  );
}
