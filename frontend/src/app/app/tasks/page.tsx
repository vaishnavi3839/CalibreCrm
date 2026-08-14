"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function TasksPage() {
  const { user } = useAuth();
  const canManage = user && ["super_admin", "admin", "rm"].includes(user.role.name);
  const canCreate = Boolean(user && ["super_admin", "admin", "rm", "telecaller", "instructor"].includes(user.role.name));
  const [items, setItems] = useState<any[]>([]);
  const [staff, setStaff] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "",
    description: "",
    priority: "medium",
    status: "pending",
    assigned_to_id: "",
    due_at: "",
  });

  async function load() {
    const r = await api<{ items: any[] }>("/api/v1/tasks");
    setItems(r.data.items);
  }

  useEffect(() => {
    load().catch(() => null);
    if (canManage) {
      api<{ items: any[] }>("/api/v1/staff").then((r) => setStaff(r.data.items)).catch(() => null);
    }
  }, [canManage]);

  function startCreate() {
    setEditId(null);
    setForm({
      title: "",
      description: "",
      priority: "medium",
      status: "pending",
      assigned_to_id: canManage ? staff[0]?.user_id || "" : user?.id || "",
      due_at: "",
    });
    setOpen(true);
  }

  function startEdit(t: any) {
    setEditId(t.id);
    setForm({
      title: t.title,
      description: t.description || "",
      priority: t.priority,
      status: t.status,
      assigned_to_id: t.assigned_to_id,
      due_at: t.due_at ? t.due_at.slice(0, 16) : "",
    });
    setOpen(true);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload: any = {
        title: form.title,
        description: form.description || null,
        priority: form.priority,
        status: form.status,
        due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
      };
      if (editId) {
        if (canManage && form.assigned_to_id) payload.assigned_to_id = form.assigned_to_id;
        await api(`/api/v1/tasks/${editId}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        if (canManage) {
          payload.assigned_to_id = form.assigned_to_id;
        }
        // telecaller/instructor: omit assignee → API assigns to self
        await api("/api/v1/tasks", { method: "POST", body: JSON.stringify(payload) });
      }
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: string) {
    await api(`/api/v1/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    await load();
  }

  async function remove(id: string) {
    if (!confirm("Delete this task?")) return;
    await api(`/api/v1/tasks/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "rm", "telecaller", "instructor"]}>
      <AppShell
        title="Tasks"
        subtitle={canManage ? "Assign tasks to staff — they get notified" : "Tasks assigned to you, plus your own to-dos"}
      >
        {canCreate && (
          <div className="mb-4 flex justify-end">
            <button onClick={startCreate} className="rounded-xl px-4 py-2.5 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
              + Add Task
            </button>
          </div>
        )}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          {items.map((t) => (
            <div key={t.id} className="glass-panel rounded-2xl p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-navy-900">{t.title}</div>
                  {t.description && <p className="mt-1 text-sm text-muted">{t.description}</p>}
                  <div className="mt-1 text-sm text-muted">
                    {t.priority} · {t.status}
                    {t.due_at ? ` · due ${new Date(t.due_at).toLocaleString()}` : ""}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {t.status !== "completed" && (
                    <button onClick={() => setStatus(t.id, "completed")} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs text-emerald-800">
                      Complete
                    </button>
                  )}
                  {t.status === "pending" && (
                    <button onClick={() => setStatus(t.id, "in_progress")} className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs">
                      Start
                    </button>
                  )}
                  <button onClick={() => startEdit(t)} className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs">Edit</button>
                  <button onClick={() => remove(t.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700">Delete</button>
                </div>
              </div>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No tasks yet.</div>}
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={save} className="glass-panel max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold">{editId ? "Edit task" : "Add task"}</h2>
              {!canManage && !editId && (
                <p className="mt-1 text-sm text-muted">This task will be added to your own list.</p>
              )}
              <div className="mt-4 grid gap-3">
                <input required className="rounded-xl border border-cloud-200 px-3 py-2" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                <textarea className="rounded-xl border border-cloud-200 px-3 py-2" rows={3} placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                <select className="rounded-xl border border-cloud-200 px-3 py-2" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
                {editId && (
                  <select className="rounded-xl border border-cloud-200 px-3 py-2" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                    <option value="pending">Pending</option>
                    <option value="in_progress">In progress</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                )}
                {canManage && (
                  <select required={!editId} className="rounded-xl border border-cloud-200 px-3 py-2" value={form.assigned_to_id} onChange={(e) => setForm({ ...form, assigned_to_id: e.target.value })}>
                    <option value="">Assign to…</option>
                    {staff.map((s) => (
                      <option key={s.user_id} value={s.user_id}>{s.name} ({s.role})</option>
                    ))}
                  </select>
                )}
                <input type="datetime-local" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.due_at} onChange={(e) => setForm({ ...form, due_at: e.target.value })} />
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
