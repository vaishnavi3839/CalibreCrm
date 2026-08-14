"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const AUDIENCE_OPTIONS = [
  { value: "all", label: "Everyone" },
  { value: "staff", label: "Staff only" },
  { value: "students", label: "Students only" },
  { value: "parents", label: "Parents only" },
  { value: "students_parents", label: "Students & parents" },
];

function audienceLabel(audience: any) {
  const roles = audience?.roles || ["all"];
  if (roles.includes("all")) return "Everyone";
  if (roles.includes("staff") && roles.length === 1) return "Staff";
  if (roles.includes("student") && roles.includes("parent")) return "Students & parents";
  if (roles.includes("student")) return "Students";
  if (roles.includes("parent")) return "Parents";
  return roles.join(", ");
}

export default function MeetingsPage() {
  const { user } = useAuth();
  const canManage = user && ["super_admin", "admin", "rm"].includes(user.role.name);
  const [items, setItems] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "",
    agenda: "",
    start_at: "",
    duration_minutes: "60",
    zoom_link: "",
    audience_type: "staff",
  });

  async function load() {
    const r = await api<{ items: any[] }>("/api/v1/meetings");
    setItems(r.data.items);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  function startCreate() {
    setEditId(null);
    setForm({ title: "", agenda: "", start_at: "", duration_minutes: "60", zoom_link: "", audience_type: "staff" });
    setOpen(true);
  }

  function startEdit(m: any) {
    const roles = m.audience?.roles || ["all"];
    let audience_type = "all";
    if (roles.includes("staff") && roles.length === 1) audience_type = "staff";
    else if (roles.includes("student") && roles.includes("parent")) audience_type = "students_parents";
    else if (roles.includes("student")) audience_type = "students";
    else if (roles.includes("parent")) audience_type = "parents";
    setEditId(m.id);
    setForm({
      title: m.title,
      agenda: m.agenda || "",
      start_at: m.start_at ? m.start_at.slice(0, 16) : "",
      duration_minutes: String(m.duration_minutes || 60),
      zoom_link: m.zoom_link || "",
      audience_type,
    });
    setOpen(true);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {
        title: form.title,
        agenda: form.agenda || null,
        start_at: new Date(form.start_at).toISOString(),
        duration_minutes: Number(form.duration_minutes) || 60,
        zoom_link: form.zoom_link || null,
        audience_type: form.audience_type,
      };
      if (editId) {
        await api(`/api/v1/meetings/${editId}`, {
          method: "PATCH",
          body: JSON.stringify({
            ...body,
            audience: { audience_type: form.audience_type },
          }),
        });
      } else {
        await api("/api/v1/meetings", { method: "POST", body: JSON.stringify(body) });
      }
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this meeting?")) return;
    await api(`/api/v1/meetings/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <RequireAuth>
      <AppShell title="Meetings" subtitle="Join with the link — shown only to the selected audience">
        {canManage && (
          <div className="mb-4 flex justify-end">
            <button onClick={startCreate} className="rounded-xl px-4 py-2.5 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
              + Schedule Meeting
            </button>
          </div>
        )}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          {items.map((m) => (
            <div key={m.id} className="glass-panel rounded-2xl p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-wider text-brass-500">{audienceLabel(m.audience)}</div>
                  <div className="mt-1 font-semibold text-navy-900">{m.title}</div>
                  <div className="mt-1 text-sm text-muted">
                    {new Date(m.start_at).toLocaleString()} · {m.duration_minutes} min
                  </div>
                  {m.agenda && <p className="mt-3 whitespace-pre-wrap text-sm text-navy-800">{m.agenda}</p>}
                  {m.zoom_link && (
                    <a
                      href={m.zoom_link}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-4 inline-flex rounded-xl px-4 py-2 text-sm font-semibold"
                      style={{ color: "#fff", backgroundColor: "#0a1628" }}
                    >
                      Join meeting
                    </a>
                  )}
                </div>
                {canManage && (
                  <div className="flex gap-2">
                    <button onClick={() => startEdit(m)} className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs">Edit</button>
                    <button onClick={() => remove(m.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700">Delete</button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No upcoming meetings for you.</div>}
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={save} className="glass-panel w-full max-w-lg rounded-3xl p-6">
              <h2 className="text-lg font-semibold">{editId ? "Edit meeting" : "Schedule meeting"}</h2>
              <p className="mt-1 text-sm text-muted">Audience gets an in-app notification with the details.</p>
              <div className="mt-4 grid gap-3">
                <input required placeholder="Title" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                <label className="text-sm font-medium">
                  For
                  <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.audience_type} onChange={(e) => setForm({ ...form, audience_type: e.target.value })}>
                    {AUDIENCE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </label>
                <input required type="datetime-local" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.start_at} onChange={(e) => setForm({ ...form, start_at: e.target.value })} />
                <input type="number" min={15} placeholder="Duration (minutes)" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} />
                <input placeholder="Zoom / Google Meet / join link" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.zoom_link} onChange={(e) => setForm({ ...form, zoom_link: e.target.value })} />
                <textarea rows={3} placeholder="Agenda" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.agenda} onChange={(e) => setForm({ ...form, agenda: e.target.value })} />
              </div>
              <div className="mt-5 flex gap-2">
                <button type="button" onClick={() => setOpen(false)} className="flex-1 rounded-xl border border-cloud-200 py-2.5 text-sm">Cancel</button>
                <button disabled={busy} className="flex-1 rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                  {busy ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
