"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatLabel, tempClass } from "@/lib/utils";

export default function TeleFollowups() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/followups?today_only=true").then((r) => setItems(r.data.items));
  }, []);
  return (
    <RequireAuth roles={["telecaller"]}>
      <AppShell title="Follow-ups">
        <div className="space-y-3">
          {items.map((f) => (
            <div key={f.id} className="glass-panel rounded-2xl p-4">
              <div className="font-semibold">{f.lead_name}</div>
              <div className="text-sm text-muted">{new Date(f.scheduled_at).toLocaleString()}</div>
              {f.lead_temperature && (
                <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[11px] uppercase ${tempClass(f.lead_temperature)}`}>
                  {f.lead_temperature}
                </span>
              )}
              <div className="mt-1 text-xs">{formatLabel(f.status)}</div>
            </div>
          ))}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
