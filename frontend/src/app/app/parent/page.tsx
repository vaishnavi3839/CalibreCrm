"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";

export default function ParentHome() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/dashboard").then((res) => setData(res.data));
  }, []);

  return (
    <RequireAuth roles={["parent"]}>
      <AppShell title="Parent Portal" subtitle="Stay connected with your ward's academy progress">
        <div className="space-y-4">
          {(data?.students || []).map((s: any) => {
            const photo =
              s.photo_url ||
              `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(String(s.name || "student").replace(/\s/g, ""))}`;
            return (
              <div key={s.student_id} className="glass-panel rounded-3xl p-5">
                <div className="flex items-center gap-4">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={photo} alt="" className="h-14 w-14 rounded-full border-2 border-brass-500/40 object-cover" />
                  <div>
                    <div className="text-lg font-semibold text-navy-900">{s.name}</div>
                    <div className="text-sm text-muted">{s.course}</div>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <MetricCard label="Days Present" value={s.days_present ?? "—"} accent="text-sky-500" />
                  <MetricCard label="Attendance %" value={`${s.attendance_pct ?? "—"}%`} />
                  <MetricCard label="Days Absent" value={s.days_absent ?? "—"} accent="text-hot" />
                  <MetricCard label="Progress" value={`${s.course_progress_pct ?? "—"}%`} accent="text-brass-500" />
                </div>
              </div>
            );
          })}

          <div className="grid grid-cols-2 gap-3">
            <Link href="/app/parent/attendance" className="glass-panel rounded-2xl px-4 py-5 text-center text-sm font-medium text-navy-900">
              Attendance history
            </Link>
            <Link href="/app/profile" className="glass-panel rounded-2xl px-4 py-5 text-center text-sm font-medium text-navy-900">
              My photo
            </Link>
            <Link href="/app/notifications" className="glass-panel rounded-2xl px-4 py-5 text-center text-sm font-medium text-navy-900">
              Notifications
            </Link>
            <Link href="/app/parent/announcements" className="glass-panel rounded-2xl px-4 py-5 text-center text-sm font-medium text-navy-900">
              Notices
            </Link>
          </div>
          <p className="text-xs text-muted">
            Absence alerts appear in Notifications when faculty mark your ward absent. Internal CRM and fee details are not shown.
          </p>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
