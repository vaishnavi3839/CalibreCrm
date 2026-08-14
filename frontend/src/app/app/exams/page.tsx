"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function ExamsPage() {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    api<{ items: any[] }>("/api/v1/exams").then((r) => setItems(r.data.items)).catch(() => null);
  }, []);

  return (
    <RequireAuth roles={["super_admin", "admin", "instructor", "rm"]}>
      <AppShell title="Exams" subtitle="Upcoming and recent examinations">
        <div className="space-y-3">
          {items.map((exam) => (
            <div key={exam.id} className="glass-panel rounded-2xl p-5">
              <div className="font-semibold text-navy-900">{exam.title}</div>
              <div className="mt-1 text-sm text-muted">
                {exam.exam_date} · {exam.venue || "Venue TBA"} · Max {exam.max_marks}
              </div>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No exams scheduled.</div>}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
