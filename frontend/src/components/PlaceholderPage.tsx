"use client";

import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";

function Placeholder({ title, roles }: { title: string; roles?: any[] }) {
  return (
    <RequireAuth roles={roles}>
      <AppShell title={title}>
        <div className="glass-panel rounded-2xl p-6 text-sm text-muted">
          This module is wired to the API and ready for deeper UI iteration in the next phase.
        </div>
      </AppShell>
    </RequireAuth>
  );
}

export default function Page() {
  return <Placeholder title="Module" />;
}
