"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

type StudentRow = {
  id: string;
  name: string;
  student_code: string;
  status: "present" | "absent" | "late" | "excused";
};

export default function MarkAttendancePage() {
  const [batches, setBatches] = useState<any[]>([]);
  const [batchId, setBatchId] = useState("");
  const [sessionDate, setSessionDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: any[] }>("/api/v1/batches")
      .then((r) => {
        setBatches(r.data.items);
        if (r.data.items[0]) setBatchId(r.data.items[0].id);
      })
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!batchId) return;
    api<{ items: any[] }>(`/api/v1/students?batch_id=${batchId}`)
      .then((r) =>
        setStudents(
          r.data.items.map((s) => ({
            id: s.id,
            name: s.name || s.student_code,
            student_code: s.student_code,
            status: "present" as const,
          }))
        )
      )
      .catch(() => setStudents([]));
  }, [batchId]);

  function setAll(status: StudentRow["status"]) {
    setStudents((prev) => prev.map((s) => ({ ...s, status })));
  }

  async function submit() {
    if (!batchId || !students.length) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api("/api/v1/attendance", {
        method: "POST",
        body: JSON.stringify({
          batch_id: batchId,
          session_date: sessionDate,
          records: students.map((s) => ({ student_id: s.id, status: s.status })),
        }),
      });
      const absentCount = students.filter((s) => s.status === "absent").length;
      setMessage(
        `Attendance saved for ${students.length} students.` +
          (absentCount
            ? ` Parents of ${absentCount} absent student(s) were notified in-app.`
            : "")
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save attendance");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "instructor"]}>
      <AppShell title="Mark Attendance" subtitle="Record today’s session — absent students notify linked parents">
        <div className="mb-4 grid gap-3 sm:grid-cols-3">
          <label className="text-sm font-medium">
            Batch
            <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2.5" value={batchId} onChange={(e) => setBatchId(e.target.value)}>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium">
            Date
            <input type="date" className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2.5" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)} />
          </label>
          <div className="flex items-end gap-2">
            <button type="button" onClick={() => setAll("present")} className="rounded-xl border border-cloud-200 px-3 py-2.5 text-sm">All present</button>
            <button type="button" onClick={() => setAll("absent")} className="rounded-xl border border-cloud-200 px-3 py-2.5 text-sm">All absent</button>
          </div>
        </div>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="mb-4 rounded-2xl border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm text-navy-800">
          When a student is marked <strong>absent</strong>, linked parents get an in-app notification
          (Notifications). Attendance % and days present update on student and parent profiles automatically.
        </div>

        <div className="glass-panel overflow-hidden rounded-2xl">
          <div className="divide-y divide-cloud-100">
            {students.map((s) => (
              <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                <div>
                  <div className="font-medium text-navy-900">{s.name}</div>
                  <div className="text-xs text-muted">{s.student_code}</div>
                </div>
                <select
                  className="rounded-xl border border-cloud-200 px-3 py-2 text-sm"
                  value={s.status}
                  onChange={(e) =>
                    setStudents((prev) =>
                      prev.map((row) => (row.id === s.id ? { ...row, status: e.target.value as StudentRow["status"] } : row))
                    )
                  }
                >
                  <option value="present">Present</option>
                  <option value="absent">Absent</option>
                  <option value="late">Late</option>
                  <option value="excused">Excused</option>
                </select>
              </div>
            ))}
            {!students.length && <div className="px-4 py-8 text-sm text-muted">No students in this batch.</div>}
          </div>
        </div>

        <button
          disabled={busy || !students.length}
          onClick={submit}
          className="mt-4 w-full rounded-2xl px-4 py-3.5 text-sm font-semibold disabled:opacity-60 sm:w-auto"
          style={{ color: "#fff", backgroundColor: "#0a1628" }}
        >
          {busy ? "Saving…" : "Save attendance"}
        </button>
      </AppShell>
    </RequireAuth>
  );
}
