"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";

export default function ParentAttendance() {
  const [students, setStudents] = useState<any[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api<any>("/api/v1/dashboard").then((res) => {
      const list = res.data.students || [];
      setStudents(list);
      if (list[0]) setSelected(list[0].student_id);
    }).catch(() => null);
  }, []);

  useEffect(() => {
    if (!selected) return;
    api(`/api/v1/students/${selected}/attendance`)
      .then((res) => setData(res.data))
      .catch(() => setData(null));
  }, [selected]);

  const current = students.find((s) => s.student_id === selected);

  return (
    <RequireAuth roles={["parent"]}>
      <AppShell title="Attendance" subtitle="Presence history for your linked student">
        {students.length > 1 && (
          <select
            className="mb-4 w-full rounded-xl border border-cloud-200 px-3 py-2.5 text-sm"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {students.map((s) => (
              <option key={s.student_id} value={s.student_id}>{s.name}</option>
            ))}
          </select>
        )}

        <div className="mb-4 rounded-2xl border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm text-navy-800">
          When faculty mark <strong>{current?.name || "your ward"}</strong> absent, you receive an in-app alert under Notifications.
        </div>

        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard label="Days Present" value={data?.days_present ?? current?.days_present ?? "—"} accent="text-sky-500" />
          <MetricCard label="Days Absent" value={data?.days_absent ?? current?.days_absent ?? "—"} accent="text-hot" />
          <MetricCard label="Sessions" value={data?.days_total ?? current?.days_total ?? "—"} />
          <MetricCard label="Attendance %" value={`${data?.attendance_pct ?? current?.attendance_pct ?? "—"}%`} />
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
