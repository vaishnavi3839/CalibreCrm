"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function TelePerformance() {
  const [perf, setPerf] = useState<any>(null);
  const [board, setBoard] = useState<any[]>([]);
  useEffect(() => {
    api("/api/v1/staff/performance").then((r) => setPerf(r.data));
    api<{ items: any[] }>("/api/v1/staff/leaderboard?period=daily").then((r) => setBoard(r.data.items));
  }, []);
  return (
    <RequireAuth roles={["telecaller"]}>
      <AppShell title="My Performance">
        <div className="grid grid-cols-2 gap-3">
          <div className="glass-panel rounded-2xl p-4">
            <div className="text-xs text-muted">Calls</div>
            <div className="text-2xl font-semibold">{perf?.today?.calls ?? 0}</div>
          </div>
          <div className="glass-panel rounded-2xl p-4">
            <div className="text-xs text-muted">Score</div>
            <div className="text-2xl font-semibold text-brass-500">{perf?.today?.score ?? 0}</div>
          </div>
        </div>
        <div className="mt-4 space-y-3">
          {(perf?.targets || []).map((t: any) => (
            <div key={t.metric} className="glass-panel rounded-2xl p-4">
              <div className="flex justify-between text-sm">
                <span className="capitalize">{t.metric}</span>
                <span>
                  {t.current} / {t.target}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-cloud-100">
                <div
                  className="h-full bg-sky-500"
                  style={{ width: `${Math.min(100, (t.current / Math.max(t.target, 1)) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-5 glass-panel rounded-2xl p-4">
          <h3 className="font-semibold">Leaderboard</h3>
          <div className="mt-3 space-y-2">
            {board.map((b) => (
              <div key={b.staff_id} className="flex justify-between text-sm">
                <span>
                  #{b.rank} {b.name}
                </span>
                <span>{b.score}</span>
              </div>
            ))}
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
