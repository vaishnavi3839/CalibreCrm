"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { FieldRow } from "@/components/FieldRow";
import { api } from "@/lib/api";

const STAFF_ROLES = [
  { value: "telecaller", label: "Telecaller / Counsellor" },
  { value: "instructor", label: "Instructor" },
  { value: "rm", label: "RM" },
  { value: "admin", label: "Admin" },
  { value: "accountant", label: "Accountant" },
];

type StaffRow = {
  id: string;
  employee_code: string;
  name: string;
  email: string;
  phone?: string;
  role?: string;
  role_display?: string;
  department?: string;
  designation?: string;
  photo_url?: string;
  is_available_for_leads?: boolean;
  monthly_salary?: number;
  branch_id?: string;
  branch_name?: string;
};

const emptyForm = {
  full_name: "",
  email: "",
  phone: "",
  role: "telecaller",
  employee_code: "",
  department: "CRM",
  designation: "",
  password: "Password123!",
  available_for_leads: true,
  finance_access: false,
  monthly_salary: 25000,
  branch_id: "",
};

export default function StaffPage() {
  const [items, setItems] = useState<StaffRow[]>([]);
  const [branches, setBranches] = useState<{ id: string; name: string; code: string }[]>([]);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [createdCreds, setCreatedCreds] = useState<{ email: string; password: string } | null>(null);

  async function load() {
    const res = await api<{ items: StaffRow[] }>("/api/v1/staff");
    setItems(res.data.items);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    api<{ items: { id: string; name: string; code: string }[] }>("/api/v1/branches")
      .then((r) => setBranches(r.data.items))
      .catch(() => null);
  }, []);

  function openCreate() {
    setEditingId(null);
    setForm(emptyForm);
    setOpen(true);
  }

  function openEdit(s: StaffRow) {
    setEditingId(s.id);
    setForm({
      full_name: s.name || "",
      email: s.email || "",
      phone: s.phone || "",
      role: s.role || "telecaller",
      employee_code: s.employee_code || "",
      department: s.department || "",
      designation: s.designation || "",
      password: "",
      available_for_leads: !!s.is_available_for_leads,
      finance_access: false,
      monthly_salary: s.monthly_salary || 0,
      branch_id: s.branch_id || "",
    });
    setOpen(true);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setCreatedCreds(null);
    try {
      if (editingId) {
        const body: Record<string, unknown> = {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          role: form.role,
          employee_code: form.employee_code,
          department: form.department || null,
          designation: form.designation || null,
          available_for_leads: form.available_for_leads,
          finance_access: form.finance_access,
          monthly_salary: Number(form.monthly_salary) || 0,
          branch_id: form.branch_id || null,
        };
        if (form.password.trim()) body.password = form.password;
        await api(`/api/v1/staff/${editingId}`, { method: "PUT", body: JSON.stringify(body) });
        setMessage("Staff updated");
      } else {
        const res = await api<any>("/api/v1/staff", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name,
            email: form.email,
            phone: form.phone || null,
            role: form.role,
            employee_code: form.employee_code,
            department: form.department || null,
            designation: form.designation || null,
            password: form.password || null,
            available_for_leads: form.available_for_leads,
            finance_access: form.finance_access,
            monthly_salary: Number(form.monthly_salary) || 0,
            branch_id: form.branch_id || null,
          }),
        });
        setMessage(res.message || "Staff created");
        setCreatedCreds({ email: res.data.email, password: res.data.temporary_password });
      }
      setForm(emptyForm);
      setEditingId(null);
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title="Staff Directory" subtitle="Add, edit, and manage academy staff">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">{items.length} active staff profiles</p>
          <button
            onClick={openCreate}
            className="rounded-xl bg-navy-900 px-4 py-2.5 text-sm font-semibold text-white"
          >
            + Add Staff
          </button>
        </div>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {createdCreds && (
          <div className="mb-3 rounded-xl border border-brass-500/30 bg-brass-500/10 px-4 py-3 text-sm text-navy-900">
            Login created: <strong>{createdCreds.email}</strong> / temporary password{" "}
            <strong>{createdCreds.password}</strong> (they should change it on first login)
          </div>
        )}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="space-y-3 md:hidden">
          {items.map((s) => (
            <div key={s.id} className="glass-panel rounded-2xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.photo_url} alt="" className="h-11 w-11 shrink-0 rounded-full object-cover" />
                  <div className="min-w-0">
                    <div className="font-semibold text-navy-900">{s.name}</div>
                    <div className="text-xs text-muted">{s.employee_code}</div>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" onClick={() => openEdit(s)} className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs font-medium">
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!confirm(`Delete staff ${s.name}? They will lose login access.`)) return;
                      try {
                        await api(`/api/v1/staff/${s.id}`, { method: "DELETE" });
                        setMessage(`${s.name} deleted`);
                        await load();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Delete failed");
                      }
                    }}
                    className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <dl className="mt-3 space-y-2 border-t border-cloud-100 pt-3">
                <FieldRow label="Role" value={s.role_display || s.role} />
                <FieldRow label="Designation" value={s.designation || "—"} />
                <FieldRow label="Department" value={s.department || "—"} />
                <FieldRow label="Salary" value={`₹${(s.monthly_salary || 0).toLocaleString()}`} />
                <FieldRow label="Branch" value={s.branch_name || "—"} />
                <FieldRow label="Email" value={s.email} />
                <FieldRow label="Phone" value={s.phone || "—"} />
              </dl>
            </div>
          ))}
        </div>

        <div className="glass-panel hidden overflow-hidden rounded-2xl md:block">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-cloud-50 text-xs uppercase tracking-wider text-muted">
                <tr>
                  <th className="px-4 py-3">Staff</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Department</th>
                  <th className="px-4 py-3">Salary</th>
                  <th className="px-4 py-3">Branch</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((s) => (
                  <tr key={s.id} className="border-t border-cloud-100">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={s.photo_url} alt={s.name} className="h-10 w-10 rounded-full object-cover" />
                        <div>
                          <div className="font-medium text-navy-900">{s.name}</div>
                          <div className="text-xs text-muted">{s.designation || "—"}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">{s.employee_code}</td>
                    <td className="px-4 py-3 capitalize">{s.role_display || s.role}</td>
                    <td className="px-4 py-3">{s.department || "—"}</td>
                    <td className="px-4 py-3">₹{(s.monthly_salary || 0).toLocaleString()}</td>
                    <td className="px-4 py-3">{s.branch_name || "—"}</td>
                    <td className="px-4 py-3">
                      <div>{s.email}</div>
                      <div className="text-xs text-muted">{s.phone || ""}</div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(s)}
                          className="rounded-lg border border-cloud-200 px-3 py-1.5 text-xs font-medium text-navy-900"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            if (!confirm(`Delete staff ${s.name}? They will lose login access.`)) return;
                            try {
                              await api(`/api/v1/staff/${s.id}`, { method: "DELETE" });
                              setMessage(`${s.name} deleted`);
                              await load();
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Delete failed");
                            }
                          }}
                          className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={onSubmit} className="glass-panel max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">
                {editingId ? "Edit Staff" : "Add New Staff"}
              </h2>
              <p className="mt-1 text-sm text-muted">
                {editingId
                  ? "Update profile, salary, branch, or reset password."
                  : "Enter any staff code and a valid email — they sign in with that email and the temporary password shown after save."}
              </p>

              <div className="mt-4 grid gap-3">
                <label className="text-sm font-medium">
                  Full name
                  <input required className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Login email
                  <input required type="email" className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Phone
                  <input className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Staff / employee code
                  <input required className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.employee_code} onChange={(e) => setForm({ ...form, employee_code: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Role
                  <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value, available_for_leads: e.target.value === "telecaller" })}>
                    {STAFF_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-sm font-medium">
                    Department
                    <input className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
                  </label>
                  <label className="text-sm font-medium">
                    Designation
                    <input className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
                  </label>
                </div>
                <label className="text-sm font-medium">
                  Punch branch
                  <select
                    required
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.branch_id}
                    onChange={(e) => setForm({ ...form, branch_id: e.target.value })}
                  >
                    <option value="">Select branch</option>
                    {branches.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium">
                  Monthly salary (₹)
                  <input
                    type="number"
                    min={0}
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.monthly_salary}
                    onChange={(e) => setForm({ ...form, monthly_salary: Number(e.target.value) })}
                  />
                </label>
                <label className="text-sm font-medium">
                  {editingId ? "New password (optional)" : "Temporary password"}
                  <input
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder={editingId ? "Leave blank to keep current" : ""}
                  />
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.available_for_leads} onChange={(e) => setForm({ ...form, available_for_leads: e.target.checked })} />
                  Available for lead assignment
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.finance_access} onChange={(e) => setForm({ ...form, finance_access: e.target.checked })} />
                  Grant finance access
                </label>
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    setEditingId(null);
                  }}
                  className="flex-1 rounded-xl border border-cloud-200 px-4 py-2.5 text-sm"
                >
                  Cancel
                </button>
                <button disabled={busy} className="flex-1 rounded-xl bg-navy-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">
                  {busy ? "Saving…" : editingId ? "Save changes" : "Create staff"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
