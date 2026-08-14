"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api, API_BASE } from "@/lib/api";
import { formatLabel, tempClass } from "@/lib/utils";

const SOURCES = [
  "website",
  "instagram",
  "facebook",
  "google_ads",
  "whatsapp",
  "walk_in",
  "referral",
  "youtube",
  "event",
  "college_visit",
  "existing_student",
  "other",
];

const emptyForm = {
  name: "",
  phone: "",
  email: "",
  location: "",
  age: "",
  course_id: "",
  source: "website",
  notes: "",
  assign_mode: "auto" as "auto" | "manual" | "none",
  staff_id: "",
};

type PreviewRow = {
  row_number: number;
  status: string;
  name: string;
  phone: string;
  email?: string | null;
  location?: string | null;
  age?: number | null;
  course?: string | null;
  course_id?: string | null;
  source: string;
  notes?: string | null;
  errors: string[];
  warnings: string[];
  duplicates: { id: string; lead_code: string; name: string; phone: string }[];
};

type PreviewData = {
  filename: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  columns_detected: string[];
  rows: PreviewRow[];
};

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("caa_access");
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<any[]>([]);
  const [staff, setStaff] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [temperature, setTemperature] = useState("");
  const [open, setOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [autoAssignImport, setAutoAssignImport] = useState(true);
  const [skipDuplicates, setSkipDuplicates] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (temperature) params.set("temperature", temperature);
    const res = await api<{ items: any[] }>(`/api/v1/leads?${params.toString()}`);
    setLeads(res.data.items);
  }

  useEffect(() => {
    load();
    api<{ items: any[] }>("/api/v1/staff?role=telecaller")
      .then((r) => setStaff(r.data.items.filter((s) => s.is_available_for_leads !== false)))
      .catch(() => null);
    api<{ items: any[] }>("/api/v1/courses")
      .then((r) => setCourses(r.data.items))
      .catch(() => null);
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        name: form.name,
        phone: form.phone,
        email: form.email || null,
        location: form.location || null,
        age: form.age ? Number(form.age) : null,
        course_id: form.course_id || null,
        source: form.source,
        notes: form.notes || null,
        auto_assign: form.assign_mode === "auto",
      };
      const res = await api<any>("/api/v1/leads", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const leadId = res.data.id;
      if (form.assign_mode === "manual" && form.staff_id) {
        await api(`/api/v1/leads/${leadId}/assign`, {
          method: "POST",
          body: JSON.stringify({ staff_id: form.staff_id }),
        });
        setMessage(`Lead created and assigned manually. ${res.message || ""}`);
      } else if (form.assign_mode === "auto") {
        setMessage(`Lead created and auto-distributed (round robin). ${res.message || ""}`);
      } else {
        setMessage(`Lead created as unassigned. Assign it later from the lead page.`);
      }

      setForm(emptyForm);
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create lead");
    } finally {
      setBusy(false);
    }
  }

  async function downloadTemplate() {
    setError("");
    try {
      const token = getAccessToken();
      const res = await fetch(`${API_BASE}/api/v1/leads/import/template`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Could not download template");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "calibre_leads_import_template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Template download failed");
    }
  }

  async function onFileSelected(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError("");
    setMessage("");
    setPreview(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await api<PreviewData>("/api/v1/leads/import/preview", {
        method: "POST",
        body,
      });
      setPreview(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read file");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function commitImport() {
    if (!preview) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const res = await api<{
        created: number;
        assigned: number;
        skipped: number;
        failed: number;
      }>("/api/v1/leads/import/commit", {
        method: "POST",
        body: JSON.stringify({
          rows: preview.rows,
          auto_assign: autoAssignImport,
          skip_invalid: true,
          skip_duplicates: skipDuplicates,
        }),
      });
      setMessage(
        `Imported ${res.data.created} lead(s)` +
          (autoAssignImport ? `, ${res.data.assigned} auto-assigned` : "") +
          (res.data.skipped ? `, ${res.data.skipped} skipped` : "") +
          (res.data.failed ? `, ${res.data.failed} failed` : "") +
          "."
      );
      setPreview(null);
      setImportOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  function closeImport() {
    setImportOpen(false);
    setPreview(null);
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title="Lead Management" subtitle="Add leads and distribute them to telecallers">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, phone, email, lead ID"
            className="flex-1 rounded-xl border border-cloud-200 bg-white px-3 py-2.5 text-sm"
          />
          <select
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
            className="rounded-xl border border-cloud-200 bg-white px-3 py-2.5 text-sm"
          >
            <option value="">All temperatures</option>
            <option value="hot">HOT</option>
            <option value="warm">WARM</option>
            <option value="cold">COLD</option>
          </select>
          <button
            onClick={load}
            className="rounded-xl bg-navy-900 px-4 py-2.5 text-sm font-medium"
            style={{ color: "#fff", backgroundColor: "#0a1628" }}
          >
            Filter
          </button>
          <button
            onClick={() => {
              setPreview(null);
              setImportOpen(true);
            }}
            className="rounded-xl border border-cloud-200 bg-white px-4 py-2.5 text-sm font-semibold text-navy-900"
          >
            Import Excel
          </button>
          <button
            onClick={() => setOpen(true)}
            className="rounded-xl px-4 py-2.5 text-sm font-semibold"
            style={{ color: "#fff", backgroundColor: "#0a1628" }}
          >
            + Add Lead
          </button>
        </div>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="mb-4 rounded-2xl border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm text-navy-800">
          <strong>Distribution:</strong> With <em>Auto (round robin)</em>, leads go in turn to telecallers who are
          marked <em>Available for lead assignment</em> (Staff page). Example: Lead 1 → Priya, Lead 2 → Arjun, Lead 3 → Meera, then repeat.
        </div>

        <div className="glass-panel overflow-hidden rounded-2xl">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-cloud-50 text-xs uppercase tracking-wider text-muted">
                <tr>
                  <th className="px-4 py-3">Lead</th>
                  <th className="px-4 py-3">Phone</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Temp</th>
                  <th className="px-4 py-3">Score</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id} className="border-t border-cloud-100 hover:bg-cloud-50/70">
                    <td className="px-4 py-3">
                      <Link href={`/app/leads/${lead.id}`} className="font-medium text-navy-900 hover:text-sky-500">
                        {lead.name}
                      </Link>
                      <div className="text-xs text-muted">{lead.lead_code}</div>
                    </td>
                    <td className="px-4 py-3">{lead.phone}</td>
                    <td className="px-4 py-3">{formatLabel(lead.status)}</td>
                    <td className="px-4 py-3">
                      {lead.temperature ? (
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${tempClass(lead.temperature)}`}>
                          {lead.temperature}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium">{lead.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={onCreate} className="glass-panel max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">Add Lead</h2>
              <p className="mt-1 text-sm text-muted">Create a CRM lead and choose how it is assigned.</p>

              <div className="mt-4 grid gap-3">
                <label className="text-sm font-medium">
                  Name *
                  <input required className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Phone *
                  <input required className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Email
                  <input type="email" className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-sm font-medium">
                    Location
                    <input className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
                  </label>
                  <label className="text-sm font-medium">
                    Age
                    <input type="number" min={10} max={80} className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} />
                  </label>
                </div>
                <label className="text-sm font-medium">
                  Course interested in
                  <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })}>
                    <option value="">Select course</option>
                    {courses.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium">
                  Lead source *
                  <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}>
                    {SOURCES.map((s) => (
                      <option key={s} value={s}>{formatLabel(s)}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium">
                  Notes
                  <textarea rows={3} className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </label>

                <div className="rounded-2xl bg-cloud-50 p-3">
                  <div className="text-sm font-semibold text-navy-900">Assignment</div>
                  <div className="mt-2 space-y-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input type="radio" checked={form.assign_mode === "auto"} onChange={() => setForm({ ...form, assign_mode: "auto" })} />
                      Auto distribute (round robin)
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="radio" checked={form.assign_mode === "manual"} onChange={() => setForm({ ...form, assign_mode: "manual" })} />
                      Assign to specific telecaller
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="radio" checked={form.assign_mode === "none"} onChange={() => setForm({ ...form, assign_mode: "none" })} />
                      Leave unassigned
                    </label>
                  </div>
                  {form.assign_mode === "manual" && (
                    <select
                      required
                      className="mt-3 w-full rounded-xl border border-cloud-200 px-3 py-2"
                      value={form.staff_id}
                      onChange={(e) => setForm({ ...form, staff_id: e.target.value })}
                    >
                      <option value="">Select telecaller</option>
                      {staff.map((s) => (
                        <option key={s.id} value={s.id}>{s.name} ({s.employee_code})</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              <div className="mt-5 flex gap-2">
                <button type="button" onClick={() => setOpen(false)} className="flex-1 rounded-xl border border-cloud-200 px-4 py-2.5 text-sm">
                  Cancel
                </button>
                <button disabled={busy} className="flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                  {busy ? "Saving…" : "Create lead"}
                </button>
              </div>
            </form>
          </div>
        )}

        {importOpen && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <div className="glass-panel max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">Import leads from Excel</h2>
              <p className="mt-1 text-sm text-muted">
                Upload .xlsx, .xls, or .csv. Required columns: <strong>name</strong>, <strong>phone</strong>. Optional: email, location, age, course, source, notes.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={downloadTemplate}
                  className="rounded-xl border border-cloud-200 bg-white px-4 py-2 text-sm font-medium"
                >
                  Download template
                </button>
                <label className="cursor-pointer rounded-xl px-4 py-2 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                  {busy ? "Reading…" : "Choose file"}
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    disabled={busy}
                    onChange={(e) => onFileSelected(e.target.files?.[0] || null)}
                  />
                </label>
              </div>

              {preview && (
                <div className="mt-5 space-y-4">
                  <div className="rounded-2xl bg-cloud-50 px-4 py-3 text-sm">
                    <div className="font-medium text-navy-900">{preview.filename}</div>
                    <div className="mt-1 text-muted">
                      {preview.total_rows} rows · {preview.valid_rows} valid · {preview.invalid_rows} invalid · {preview.duplicate_rows} possible duplicates
                    </div>
                  </div>

                  <div className="max-h-64 overflow-auto rounded-2xl border border-cloud-100">
                    <table className="min-w-full text-left text-xs">
                      <thead className="sticky top-0 bg-cloud-50 text-[10px] uppercase tracking-wider text-muted">
                        <tr>
                          <th className="px-3 py-2">Row</th>
                          <th className="px-3 py-2">Status</th>
                          <th className="px-3 py-2">Name</th>
                          <th className="px-3 py-2">Phone</th>
                          <th className="px-3 py-2">Issues</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.rows.map((row) => (
                          <tr key={row.row_number} className="border-t border-cloud-100">
                            <td className="px-3 py-2">{row.row_number}</td>
                            <td className="px-3 py-2">
                              <span
                                className={
                                  row.status === "valid"
                                    ? "text-emerald-700"
                                    : row.status === "duplicate"
                                      ? "text-amber-700"
                                      : "text-red-700"
                                }
                              >
                                {row.status}
                              </span>
                            </td>
                            <td className="px-3 py-2">{row.name || "—"}</td>
                            <td className="px-3 py-2">{row.phone || "—"}</td>
                            <td className="px-3 py-2 text-muted">
                              {[...row.errors, ...row.warnings].join("; ") || "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="space-y-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={autoAssignImport} onChange={(e) => setAutoAssignImport(e.target.checked)} />
                      Auto-distribute imported leads (round robin)
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={skipDuplicates} onChange={(e) => setSkipDuplicates(e.target.checked)} />
                      Skip rows flagged as duplicates
                    </label>
                    <p className="text-xs text-muted">Invalid rows are always skipped.</p>
                  </div>
                </div>
              )}

              <div className="mt-5 flex gap-2">
                <button type="button" onClick={closeImport} className="flex-1 rounded-xl border border-cloud-200 px-4 py-2.5 text-sm">
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={busy || !preview || preview.valid_rows + preview.duplicate_rows === 0}
                  onClick={commitImport}
                  className="flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-60"
                  style={{ color: "#fff", backgroundColor: "#0a1628" }}
                >
                  {busy ? "Importing…" : "Confirm import"}
                </button>
              </div>
            </div>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
