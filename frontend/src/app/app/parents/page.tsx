"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

const emptyForm = {
  full_name: "",
  email: "",
  phone: "",
  relationship_type: "father",
  student_id: "",
  password: "Password123!",
};

export default function ParentsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [createdCreds, setCreatedCreds] = useState<{ email: string; password: string } | null>(null);

  async function load() {
    const res = await api<{ items: any[] }>("/api/v1/parents");
    setItems(res.data.items);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    api<{ items: any[] }>("/api/v1/students").then((r) => setStudents(r.data.items)).catch(() => null);
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setCreatedCreds(null);
    try {
      const res = await api<any>("/api/v1/parents", {
        method: "POST",
        body: JSON.stringify({
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          relationship_type: form.relationship_type,
          student_id: form.student_id || null,
          password: form.password || null,
        }),
      });
      setMessage(res.message || "Parent created");
      setCreatedCreds({ email: res.data.email, password: res.data.temporary_password });
      setForm(emptyForm);
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create parent");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(p: any) {
    if (!confirm(`Delete parent ${p.name}? They will lose login access.`)) return;
    try {
      await api(`/api/v1/parents/${p.id}`, { method: "DELETE" });
      setMessage(`${p.name} deleted`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <RequireAuth roles={["super_admin", "admin"]}>
      <AppShell title="Parents" subtitle="Portal logins for linked parents">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">{items.length} active parents</p>
          <button onClick={() => setOpen(true)} className="rounded-xl px-4 py-2.5 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
            + Add Parent
          </button>
        </div>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {createdCreds && (
          <div className="mb-3 rounded-xl border border-brass-500/30 bg-brass-500/10 px-4 py-3 text-sm text-navy-900">
            Parent login: <strong>{createdCreds.email}</strong> / password <strong>{createdCreds.password}</strong>
          </div>
        )}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="glass-panel overflow-hidden rounded-2xl">
          <table className="min-w-full text-sm">
            <thead className="bg-cloud-50 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3 text-left">Parent</th>
                <th className="px-4 py-3 text-left">Email / Login</th>
                <th className="px-4 py-3 text-left">Linked student(s)</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id} className="border-t border-cloud-100">
                  <td className="px-4 py-3">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted capitalize">{p.relationship_type}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div>{p.email}</div>
                    <div className="text-xs text-muted">{p.phone || ""}</div>
                  </td>
                  <td className="px-4 py-3">
                    {(p.students || []).map((s: any) => s.name).join(", ") || "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => onDelete(p)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={onCreate} className="glass-panel max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">Add Parent</h2>
              <p className="mt-1 text-sm text-muted">Creates a parent portal login. Link them to a student to see attendance alerts.</p>
              <div className="mt-4 grid gap-3">
                <input required placeholder="Full name" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                <input required type="email" placeholder="Login email" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                <input placeholder="Phone" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                <select className="rounded-xl border border-cloud-200 px-3 py-2" value={form.relationship_type} onChange={(e) => setForm({ ...form, relationship_type: e.target.value })}>
                  <option value="father">Father</option>
                  <option value="mother">Mother</option>
                  <option value="guardian">Guardian</option>
                  <option value="parent">Parent</option>
                </select>
                <select className="rounded-xl border border-cloud-200 px-3 py-2" value={form.student_id} onChange={(e) => setForm({ ...form, student_id: e.target.value })}>
                  <option value="">Link to student (optional)</option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} · {s.student_code}</option>
                  ))}
                </select>
                <input placeholder="Temporary password" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div className="mt-5 flex gap-2">
                <button type="button" onClick={() => setOpen(false)} className="flex-1 rounded-xl border border-cloud-200 py-2.5 text-sm">Cancel</button>
                <button disabled={busy} className="flex-1 rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                  {busy ? "Creating…" : "Create parent"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
