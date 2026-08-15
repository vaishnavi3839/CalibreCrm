"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const emptyForm = {
  full_name: "",
  email: "",
  phone: "",
  student_code: "",
  course_id: "",
  batch_id: "",
  batch_mode: "existing" as "existing" | "new",
  new_batch_name: "",
  branch_id: "",
  password: "Password123!",
};

export default function StudentsPage() {
  const { user } = useAuth();
  const canManage = user && ["super_admin", "admin"].includes(user.role.name);
  const [items, setItems] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [createdCreds, setCreatedCreds] = useState<{ email: string; password: string } | null>(null);

  async function load() {
    const res = await api<{ items: any[] }>("/api/v1/students");
    setItems(res.data.items);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    api<{ items: any[] }>("/api/v1/courses").then((r) => setCourses(r.data.items)).catch(() => null);
    api<{ items: any[] }>("/api/v1/batches").then((r) => setBatches(r.data.items)).catch(() => null);
    api<{ items: any[] }>("/api/v1/branches").then((r) => setBranches(r.data.items)).catch(() => null);
  }, []);

  function openCreate() {
    setEditingId(null);
    setForm(emptyForm);
    setOpen(true);
  }

  function openEdit(s: any) {
    setEditingId(s.id);
    setForm({
      full_name: s.name || "",
      email: s.email || "",
      phone: s.phone || "",
      student_code: s.student_code || "",
      course_id: s.course_id || "",
      batch_id: s.batch_id || "",
      batch_mode: "existing",
      new_batch_name: "",
      branch_id: s.branch_id || "",
      password: "",
    });
    setOpen(true);
  }

  async function resolveBatchId(): Promise<string | null> {
    if (form.batch_mode === "new") {
      const name = form.new_batch_name.trim();
      if (!name) throw new Error("Enter a new batch name");
      if (!form.course_id) throw new Error("Select a course before creating a batch");
      const res = await api<{ id: string }>("/api/v1/batches", {
        method: "POST",
        body: JSON.stringify({ name, course_id: form.course_id }),
      });
      const list = await api<{ items: any[] }>("/api/v1/batches");
      setBatches(list.data.items);
      return res.data.id;
    }
    return form.batch_id || null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setCreatedCreds(null);
    try {
      const batchId = await resolveBatchId();
      if (editingId) {
        const body: Record<string, unknown> = {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          student_code: form.student_code || null,
          course_id: form.course_id || null,
          batch_id: batchId,
          branch_id: form.branch_id || null,
          clear_course: !form.course_id,
          clear_batch: !batchId,
        };
        if (form.password.trim()) body.password = form.password;
        await api(`/api/v1/students/${editingId}`, { method: "PUT", body: JSON.stringify(body) });
        setMessage("Student updated");
      } else {
        const res = await api<any>("/api/v1/students", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name,
            email: form.email,
            phone: form.phone || null,
            student_code: form.student_code || null,
            course_id: form.course_id || null,
            batch_id: batchId,
            branch_id: form.branch_id || null,
            password: form.password || null,
          }),
        });
        setCreatedCreds({ email: form.email, password: form.password || "Password123!" });
        setMessage(res.message || "Student created");
      }
      setOpen(false);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(s: any) {
    if (!confirm(`Delete student ${s.name}? They will lose login access.`)) return;
    try {
      await api(`/api/v1/students/${s.id}`, { method: "DELETE" });
      setMessage(`${s.name} deleted`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "rm", "instructor", "accountant"]}>
      <AppShell title="Students" subtitle="Add, edit, and manage student portal logins">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">{items.length} active students</p>
          {canManage && (
            <button
              onClick={openCreate}
              className="rounded-xl px-4 py-2.5 text-sm font-semibold"
              style={{ color: "#fff", backgroundColor: "#0a1628" }}
            >
              + Add Student
            </button>
          )}
        </div>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {createdCreds && (
          <div className="mb-3 rounded-xl border border-brass-500/30 bg-brass-500/10 px-4 py-3 text-sm text-navy-900">
            Student login: <strong>{createdCreds.email}</strong> / password <strong>{createdCreds.password}</strong>
          </div>
        )}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="glass-panel overflow-hidden rounded-2xl">
          <table className="min-w-full text-sm">
            <thead className="bg-cloud-50 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3 text-left">Student</th>
                <th className="px-4 py-3 text-left">Email / Login</th>
                <th className="px-4 py-3 text-left">Course</th>
                <th className="px-4 py-3 text-left">Branch</th>
                <th className="px-4 py-3 text-left">Attendance</th>
                <th className="px-4 py-3 text-left">Progress</th>
                {canManage && <th className="px-4 py-3"></th>}
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id} className="border-t border-cloud-100">
                  <td className="px-4 py-3">
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-muted">{s.student_code}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div>{s.email || "—"}</div>
                    <div className="text-xs text-muted">{s.phone || ""}</div>
                  </td>
                  <td className="px-4 py-3">{s.course || "—"}</td>
                  <td className="px-4 py-3">{s.branch_name || "—"}</td>
                  <td className="px-4 py-3">{s.attendance_pct}%</td>
                  <td className="px-4 py-3">{s.course_progress_pct}%</td>
                  {canManage && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => openEdit(s)}
                          className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs font-medium text-navy-900"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => onDelete(s)}
                          className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {open && canManage && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={onSubmit} className="glass-panel max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">
                {editingId ? "Edit Student" : "Add Student"}
              </h2>
              <p className="mt-1 text-sm text-muted">
                {editingId
                  ? "Update details, branch, course, or reset password."
                  : "Creates a portal login with email and password."}
              </p>
              <div className="mt-4 grid gap-3">
                <input required placeholder="Full name" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                <input required type="email" placeholder="Login email" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                <input placeholder="Phone" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                <input placeholder="Student code" className="rounded-xl border border-cloud-200 px-3 py-2" value={form.student_code} onChange={(e) => setForm({ ...form, student_code: e.target.value })} />
                <select className="rounded-xl border border-cloud-200 px-3 py-2" value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })}>
                  <option value="">Course (optional)</option>
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <div className="rounded-xl border border-cloud-200 p-3">
                  <div className="mb-2 flex gap-3 text-sm">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={form.batch_mode === "existing"}
                        onChange={() => setForm({ ...form, batch_mode: "existing" })}
                      />
                      Existing batch
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={form.batch_mode === "new"}
                        onChange={() => setForm({ ...form, batch_mode: "new" })}
                      />
                      New batch
                    </label>
                  </div>
                  {form.batch_mode === "existing" ? (
                    <select className="w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.batch_id} onChange={(e) => setForm({ ...form, batch_id: e.target.value })}>
                      <option value="">Batch (optional)</option>
                      {batches.map((b) => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      required={form.batch_mode === "new"}
                      placeholder="New batch name (e.g. CPL Batch B)"
                      className="w-full rounded-xl border border-cloud-200 px-3 py-2"
                      value={form.new_batch_name}
                      onChange={(e) => setForm({ ...form, new_batch_name: e.target.value })}
                    />
                  )}
                </div>
                <select required className="rounded-xl border border-cloud-200 px-3 py-2" value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>
                  <option value="">Punch branch *</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
                <input
                  placeholder={editingId ? "New password (optional)" : "Temporary password"}
                  className="rounded-xl border border-cloud-200 px-3 py-2"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </div>
              <div className="mt-5 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    setEditingId(null);
                  }}
                  className="flex-1 rounded-xl border border-cloud-200 py-2.5 text-sm"
                >
                  Cancel
                </button>
                <button
                  disabled={busy}
                  className="flex-1 rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60"
                  style={{ color: "#fff", backgroundColor: "#0a1628" }}
                >
                  {busy ? "Saving…" : editingId ? "Save changes" : "Create student"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
