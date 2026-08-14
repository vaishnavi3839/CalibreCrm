"use client";

import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";

export default function StudentCourse() {
  return (
    <RequireAuth roles={["student"]}>
      <AppShell title="My Course">
        <div className="space-y-3">
          {[
            ["Air Regulations", "Completed"],
            ["Navigation", "In Progress"],
            ["Meteorology", "Upcoming"],
            ["Technical General", "Upcoming"],
          ].map(([name, status]) => (
            <div key={name} className="glass-panel flex items-center justify-between rounded-2xl px-4 py-4">
              <span className="font-medium text-navy-900">{name}</span>
              <span className="text-sm text-muted">{status}</span>
            </div>
          ))}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
