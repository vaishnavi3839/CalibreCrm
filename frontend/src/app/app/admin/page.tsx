"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { TopPerformerSpotlight, type TopPerformer } from "@/components/Brand";
import { LeaderboardCard, MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";

type Pulse = {
  new_leads: number;
  leads_assigned: number;
  calls_completed: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  pending_followups: number;
  registrations: number;
  admissions: number;
  students_present: number;
  students_absent: number;
  upcoming_exams: number;
  upcoming_events: number;
  staff_meetings: number;
  top_performer?: TopPerformer | string | null;
};

function AdminDashboard() {
  const [pulse, setPulse] = useState<Pulse | null>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);

  useEffect(() => {
    api<{ pulse: Pulse; leaderboard: any[] }>("/api/v1/dashboard").then((res) => {
      setPulse(res.data.pulse);
      setLeaderboard(res.data.leaderboard || []);
    });
  }, []);

  return (
    <RequireAuth roles={["super_admin", "admin"]}>
      <AppShell title="Daily Academy Pulse" subtitle="Live operations across CRM, academics and campus">
        {!pulse ? (
          <div className="text-muted">Loading pulse…</div>
        ) : (
          <div className="space-y-5">
            <TopPerformerSpotlight performer={pulse.top_performer} />

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="New Leads" value={pulse.new_leads} accent="text-sky-500" />
              <MetricCard label="Hot Leads" value={pulse.hot_leads} accent="text-hot" />
              <MetricCard label="Pending Follow-ups" value={pulse.pending_followups} />
              <MetricCard label="Admissions" value={pulse.admissions} accent="text-brass-500" />
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Calls Completed" value={pulse.calls_completed} />
              <MetricCard label="Students Present" value={pulse.students_present} />
              <MetricCard label="Students Absent" value={pulse.students_absent} accent="text-hot" />
              <MetricCard label="Upcoming Events" value={pulse.upcoming_events} />
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Warm Leads" value={pulse.warm_leads} accent="text-warm" />
              <MetricCard label="Cold Leads" value={pulse.cold_leads} accent="text-cold" />
              <MetricCard label="Registrations" value={pulse.registrations} />
              <MetricCard label="Upcoming Exams" value={pulse.upcoming_exams} />
            </div>

            <LeaderboardCard rows={leaderboard} />

            <div className="grid gap-3 sm:grid-cols-3">
              <Link href="/app/events" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
                Manage Events
              </Link>
              <Link href="/app/attendance" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
                Mark Attendance
              </Link>
              <Link href="/app/leads" className="glass-panel rounded-2xl p-5 font-medium text-navy-900 transition hover:-translate-y-0.5">
                Lead Management
              </Link>
            </div>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}

export default AdminDashboard;
