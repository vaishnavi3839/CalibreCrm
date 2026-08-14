"use client";

import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";

export default function ParentProgress() {
  return (
    <RequireAuth roles={["parent"]}>
      <AppShell title="Academic & Training Progress">
        <div className="glass-panel rounded-2xl p-5 text-sm text-muted">
          Course completion, module status and training hours for your ward. Fee information is intentionally hidden.
        </div>
      </AppShell>
    </RequireAuth>
  );
}
