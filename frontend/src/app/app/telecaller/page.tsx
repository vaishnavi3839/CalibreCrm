"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Phone, Users } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { TopPerformerSpotlight } from "@/components/Brand";
import { LeaderboardCard, MetricCard } from "@/components/DashboardCards";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function TelecallerHome() {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/dashboard").then((res) => setData(res.data));
  }, []);

  const stats = data?.stats;

  return (
    <RequireAuth roles={["telecaller"]}>
      <AppShell title={data?.greeting || `Hello, ${user?.full_name.split(" ")[0]}`} subtitle="Your leads, targets and follow-ups">
        <div className="space-y-4">
          <TopPerformerSpotlight performer={data?.top_performer} compact />

          {data?.is_top_performer && (
            <div className="rounded-2xl bg-brass-500/15 px-4 py-3 text-sm font-medium text-navy-900 animate-rise">
              That&apos;s you — keep the momentum going.
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="My Leads" value={stats?.my_leads ?? "—"} />
            <MetricCard label="Hot Leads" value={stats?.hot_leads ?? "—"} accent="text-hot" />
            <MetricCard label="Follow-ups" value={stats?.todays_followups ?? "—"} />
            <MetricCard label="Calls Today" value={stats?.calls_today ?? "—"} accent="text-sky-500" />
          </div>

          <Link
            href="/app/telecaller/leads"
            className="flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-4 text-base font-semibold shadow-md"
            style={{ color: "#ffffff", backgroundColor: "#0a1628" }}
          >
            <Users className="h-5 w-5" style={{ color: "#ffffff" }} />
            Open My Leads
          </Link>

          <Link
            href="/app/telecaller/followups"
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-sky-500/40 bg-sky-500/10 px-4 py-3.5 text-base font-semibold text-sky-500"
          >
            <Phone className="h-5 w-5" />
            Today&apos;s Follow-ups
          </Link>

          <LeaderboardCard rows={data?.top_performers || []} title="Today's Leaderboard" />
        </div>
      </AppShell>
    </RequireAuth>
  );
}
