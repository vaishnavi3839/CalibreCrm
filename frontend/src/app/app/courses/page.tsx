"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function CoursesPage() {
  const [items, setItems] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    code: "",
    name: "",
    description: "",
    duration_months: "",
    has_flight_training: false,
  });

  async function load() {
    const r = await api<{ items: any[] }>("/api/v1/courses?include_inactive=false");
    setItems(r.data.items);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/courses", {
        method: "POST",
        body: JSON.stringify({
          code: form.code,
          name: form.name,
          description: form.description || null,
          duration_months: form.duration_months ? Number(form.duration_months) : null,
          has_flight_training: form.has_flight_training,
        }),
      });
      setOpen(false);
      setForm({ code: "", name: "", description: "", duration_months: "", has_flight_training: false });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create course");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this course? It will be deactivated.")) return;
    await api(`/api/v1/courses/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <RequireAuth roles={["super_admin", "admin"]}>
      <AppShell title="Courses" subtitle="Add or remove academy courses">
        <div className="mb-4 flex justify-end">
          <button onClick={() => setOpen(true)} className="rounded-xl px-4 py-2.5 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
            + Add Course
          </button>
        </div>
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          {items.map((c) => (
            <div key={c.id} className="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4">
              <div>
                <div className="font-semibold text-navy-900">{c.name}</div>
                <div className="text-sm text-muted">
                  {c.code}
                  {c.duration_months ? ` · ${c.duration_months} months` : ""}
                  {c.has_flight_training ? " · Flight training" : ""}
                </div>
                {c.description && <p className="mt-1 text-sm text-muted">{c.description}</p>}
              </div>
              <button onClick={() => remove(c.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700">
                Delete
              </button>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No courses yet.</div>}
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={save} className="glass-panel w-full max-w-lg rounded-3xl p-6">
              <h2 className="text-lg font-semibold">Add course</h2>
              <div className="mt-4 grid gap-3">
                <input required placeholder="Code (e.g. CPL)" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
                <input required placeholder="Name" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                <input type="number" min={1} placeholder="Duration (months)" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.duration_months} onChange={(e) => setForm({ ...form, duration_months: e.target.value })} />
                <textarea rows={3} placeholder="Description" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.has_flight_training} onChange={(e) => setForm({ ...form, has_flight_training: e.target.checked })} />
                  Includes flight training
                </label>
              </div>
              <div className="mt-5 flex gap-2">
                <button type="button" onClick={() => setOpen(false)} className="flex-1 rounded-xl border border-cloud-200 py-2.5 text-sm">Cancel</button>
                <button disabled={busy} className="flex-1 rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                  {busy ? "Saving…" : "Create"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
