"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function AnalyticsPage() {
  const [funnel, setFunnel] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    api<{ funnel: any[] }>("/api/v1/reports/conversion-funnel").then((r) => setFunnel(r.data.funnel));
    api<{ items: any[] }>("/api/v1/reports/lead-sources").then((r) => setSources(r.data.items));
  }, []);

  const max = Math.max(...funnel.map((f) => f.count), 1);

  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title="Analytics" subtitle="Conversion funnel and marketing channel quality">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="glass-panel rounded-2xl p-5">
            <h2 className="font-semibold text-navy-900">Conversion Funnel</h2>
            <div className="mt-4 space-y-3">
              {funnel.map((stage) => (
                <div key={stage.stage}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="capitalize text-navy-800">{stage.stage.replaceAll("_", " ")}</span>
                    <span className="text-muted">
                      {stage.count} · {stage.conversion_pct}%
                    </span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-cloud-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-sky-500 to-brass-500"
                      style={{ width: `${(stage.count / max) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-5">
            <h2 className="font-semibold text-navy-900">Lead Source Performance</h2>
            <div className="mt-4 space-y-3">
              {sources
                .filter((s) => s.leads > 0)
                .map((s) => (
                  <div key={s.source} className="flex items-center justify-between rounded-xl bg-cloud-50 px-3 py-3 text-sm">
                    <div>
                      <div className="font-medium capitalize text-navy-900">{s.source.replaceAll("_", " ")}</div>
                      <div className="text-xs text-muted">
                        {s.leads} leads · {s.admissions} admissions
                      </div>
                    </div>
                    <div className="font-semibold text-sky-500">{s.conversion_pct}%</div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
