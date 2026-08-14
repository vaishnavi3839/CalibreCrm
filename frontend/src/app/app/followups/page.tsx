"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatLabel, tempClass } from "@/lib/utils";

export default function FollowupsPage() {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    api<{ items: any[] }>("/api/v1/followups?today_only=true").then((r) => setItems(r.data.items));
  }, []);

  return (
    <RequireAuth roles={["super_admin", "admin", "rm", "telecaller"]}>
      <AppShell title="Today's Follow-ups">
        <div className="space-y-3">
          {items.map((f) => (
            <div key={f.id} className="glass-panel rounded-2xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-navy-900">{f.lead_name}</div>
                  <div className="text-sm text-muted">
                    {f.staff_name} · {new Date(f.scheduled_at).toLocaleString()}
                  </div>
                </div>
                <div className="text-right">
                  {f.lead_temperature && (
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${tempClass(f.lead_temperature)}`}>
                      {f.lead_temperature}
                    </span>
                  )}
                  <div className="mt-1 text-xs text-muted">{formatLabel(f.status)}</div>
                </div>
              </div>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No follow-ups scheduled for today.</div>}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
