"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const TYPES = ["general", "exam", "holiday", "event", "academic", "emergency", "training", "meeting"];

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const canManage = user && ["super_admin", "admin", "rm"].includes(user.role.name);
  const [items, setItems] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", description: "", type: "general", location: "", audience_type: "all" });

  async function load() {
    const r = await api<{ items: any[] }>("/api/v1/announcements");
    setItems(r.data.items);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  function startCreate() {
    setEditId(null);
    setForm({ title: "", description: "", type: "general", location: "", audience_type: "all" });
    setOpen(true);
  }

  function startEdit(a: any) {
    setEditId(a.id);
    setForm({ title: a.title, description: a.description, type: a.type || "general", location: a.location || "", audience_type: "all" });
    setOpen(true);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {
        title: form.title,
        description: form.description,
        type: form.type,
        location: form.location || null,
        audience_type: form.audience_type,
      };
      if (editId) {
        await api(`/api/v1/announcements/${editId}`, { method: "PATCH", body: JSON.stringify(body) });
      } else {
        await api("/api/v1/announcements", { method: "POST", body: JSON.stringify(body) });
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
    if (!confirm("Delete this notice?")) return;
    await api(`/api/v1/announcements/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <RequireAuth>
      <AppShell title="Notices" subtitle="Announcements notify the selected audience">
        {canManage && (
          <div className="mb-4 flex justify-end">
            <button onClick={startCreate} className="rounded-xl px-4 py-2.5 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
              + Add Notice
            </button>
          </div>
        )}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          {items.map((a) => (
            <div key={a.id} className="glass-panel rounded-2xl p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-xs uppercase tracking-wider text-sky-500">{a.type}</div>
                  <div className="mt-1 font-semibold text-navy-900">{a.title}</div>
                  <p className="mt-2 text-sm text-muted">{a.description}</p>
                  {a.location && <p className="mt-1 text-xs text-muted">{a.location}</p>}
                </div>
                {canManage && (
                  <div className="flex gap-2">
                    <button onClick={() => startEdit(a)} className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs">Edit</button>
                    <button onClick={() => remove(a.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700">Delete</button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No notices yet.</div>}
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={save} className="glass-panel w-full max-w-lg rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">{editId ? "Edit notice" : "Add notice"}</h2>
              <p className="mt-1 text-sm text-muted">Audience receives an in-app notification.</p>
              <div className="mt-4 grid gap-3">
                <input required placeholder="Title" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                <select className="rounded-xl border border-cloud-200 px-3 py-2" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <label className="text-sm font-medium">
                  Show to
                  <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.audience_type} onChange={(e) => setForm({ ...form, audience_type: e.target.value })}>
                    <option value="all">Everyone</option>
                    <option value="staff">Staff only</option>
                    <option value="students">Students only</option>
                    <option value="parents">Parents only</option>
                    <option value="students_parents">Students & parents</option>
                  </select>
                </label>
                <textarea required rows={4} placeholder="Description" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                <input placeholder="Location (optional)" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
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
