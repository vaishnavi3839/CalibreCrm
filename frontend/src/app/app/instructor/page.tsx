"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { TopPerformerSpotlight } from "@/components/Brand";
import { MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";

export default function InstructorHome() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/dashboard").then((res) => setData(res.data));
  }, []);

  return (
    <RequireAuth roles={["instructor"]}>
      <AppShell title="Instructor Desk" subtitle="Students, attendance, exams and training">
        <div className="space-y-5">
          <TopPerformerSpotlight performer={data?.top_performer} compact />

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Assigned Students" value={data?.stats?.assigned_students ?? "—"} accent="text-sky-500" />
            <MetricCard label="Upcoming Exams" value={data?.stats?.upcoming_exams ?? "—"} />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Link href="/app/attendance" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
              Mark Attendance
              <div className="mt-1 text-xs font-normal text-muted">Parents are notified when a student is absent</div>
            </Link>
            <Link href="/app/students" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
              Students
            </Link>
            <Link href="/app/exams" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
              Enter Exam Marks
            </Link>
            <Link href="/app/tasks" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
              Academic Tasks
            </Link>
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
