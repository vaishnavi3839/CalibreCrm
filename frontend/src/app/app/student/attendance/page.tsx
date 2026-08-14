"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";

export default function StudentAttendance() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api<{ id: string }>("/api/v1/students/me/profile")
      .then(async (profile) => {
        const att = await api(`/api/v1/students/${profile.data.id}/attendance`);
        setData(att.data);
      })
      .catch(() => null);
  }, []);
  return (
    <RequireAuth roles={["student"]}>
      <AppShell title="Attendance" subtitle="Your session history and presence">
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard label="Days Present" value={data?.days_present ?? "—"} accent="text-sky-500" />
          <MetricCard label="Days Absent" value={data?.days_absent ?? "—"} accent="text-hot" />
          <MetricCard label="Sessions" value={data?.days_total ?? "—"} />
          <MetricCard label="Attendance %" value={`${data?.attendance_pct ?? "—"}%`} />
        </div>
        <div className="space-y-2">
          {(data?.records || []).map((r: any) => (
            <div key={r.id} className="glass-panel flex justify-between rounded-xl px-4 py-3 text-sm">
              <span>{r.date}</span>
              <span className="capitalize font-medium">{r.status}</span>
            </div>
          ))}
          {!data?.records?.length && <div className="text-sm text-muted">No attendance records yet.</div>}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
