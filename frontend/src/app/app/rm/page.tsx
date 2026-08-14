"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { TopPerformerSpotlight } from "@/components/Brand";
import { LeaderboardCard, MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";

export default function RMDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/dashboard").then((res) => setData(res.data));
  }, []);

  const pulse = data?.pulse;

  return (
    <RequireAuth roles={["rm"]}>
      <AppShell title="RM Command Center" subtitle="Lead flow, staff productivity and conversions">
        <div className="space-y-5">
          <TopPerformerSpotlight performer={pulse?.top_performer || data?.leaderboard?.[0]} />

          {pulse && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="New Leads" value={pulse.new_leads} accent="text-sky-500" />
              <MetricCard label="Hot Leads" value={pulse.hot_leads} accent="text-hot" />
              <MetricCard label="Pending Follow-ups" value={pulse.pending_followups} />
              <MetricCard label="Admissions" value={pulse.admissions} accent="text-brass-500" />
            </div>
          )}

          <LeaderboardCard rows={data?.leaderboard || []} />
        </div>
      </AppShell>
    </RequireAuth>
  );
}
