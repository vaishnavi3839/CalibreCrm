"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { TopPerformerSpotlight } from "@/components/Brand";
import { api } from "@/lib/api";

export default function FinanceHome() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/v1/dashboard").then((res) => setData(res.data)).catch(() => null);
  }, []);

  return (
    <RequireAuth roles={["accountant", "super_admin", "admin", "rm"]}>
      <AppShell title="Finance" subtitle="Internal payment records — not visible to students or parents">
        <div className="space-y-4">
          <TopPerformerSpotlight performer={data?.top_performer} compact />
          <div className="glass-panel rounded-2xl p-6 text-sm text-muted">
            Payment module is permission-gated. Students and parents never receive fee endpoints or UI.
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
