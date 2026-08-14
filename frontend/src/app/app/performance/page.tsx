"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function PerformancePage() {
  const [board, setBoard] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/staff/leaderboard?period=daily").then((r) => setBoard(r.data.items));
  }, []);
  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title="Staff Performance">
        <div className="space-y-3">
          {board.map((b) => (
            <div key={b.staff_id} className="glass-panel flex items-center justify-between rounded-2xl px-4 py-4">
              <div>
                <div className="font-semibold text-navy-900">
                  #{b.rank} {b.name}
                </div>
                <div className="text-xs text-muted">{(b.badges || []).join(" · ")}</div>
              </div>
              <div className="text-brass-500 font-semibold">{b.score} pts</div>
            </div>
          ))}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
