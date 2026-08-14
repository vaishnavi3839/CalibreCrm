"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function StudentHome() {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/dashboard").then((res) => setData(res.data));
  }, []);

  const photo =
    data?.photo_url ||
    user?.photo_url ||
    `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent((user?.full_name || "student").replace(/\s/g, ""))}`;

  return (
    <RequireAuth roles={["student"]}>
      <AppShell title={data?.greeting || "Student Portal"} subtitle="Your academy journey">
        <div className="space-y-4">
          <div className="glass-panel rounded-3xl p-5">
            <div className="flex items-center gap-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo} alt="" className="h-16 w-16 rounded-full border-2 border-brass-500/40 object-cover" />
              <div>
                <div className="text-sm text-muted">Course</div>
                <div className="text-xl font-semibold text-navy-900">{data?.course || "—"}</div>
                <div className="mt-1 text-sm text-muted">Batch · {data?.batch || "—"}</div>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <MetricCard label="Days Present" value={data?.days_present ?? "—"} accent="text-sky-500" />
              <MetricCard label="Attendance %" value={`${data?.attendance_pct ?? "—"}%`} />
              <MetricCard label="Days Absent" value={data?.days_absent ?? "—"} accent="text-hot" />
              <MetricCard label="Course Progress" value={`${data?.course_progress_pct ?? "—"}%`} accent="text-brass-500" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              ["/app/student/attendance", "Attendance"],
              ["/app/student/course", "My Course"],
              ["/app/student/documents", "Documents"],
              ["/app/student/id", "Digital ID"],
              ["/app/profile", "My Photo"],
              ["/app/notifications", "Notifications"],
            ].map(([href, label]) => (
              <Link key={href} href={href} className="glass-panel rounded-2xl px-4 py-5 text-center text-sm font-medium text-navy-900 transition hover:-translate-y-0.5">
                {label}
              </Link>
            ))}
          </div>
          <p className="text-xs text-muted">Fee and payment information is not shown in the student portal.</p>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
