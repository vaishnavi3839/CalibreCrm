"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatLabel, tempClass } from "@/lib/utils";

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const [lead, setLead] = useState<any>(null);
  const [staff, setStaff] = useState<any[]>([]);
  const [staffId, setStaffId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const res = await api(`/api/v1/leads/${params.id}`);
    setLead(res.data);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    api<{ items: any[] }>("/api/v1/staff?role=telecaller")
      .then((r) => setStaff(r.data.items))
      .catch(() => null);
  }, [params.id]);

  async function assignManual() {
    if (!staffId) return;
    setMessage("");
    setError("");
    try {
      await api(`/api/v1/leads/${params.id}/assign`, {
        method: "POST",
        body: JSON.stringify({ staff_id: staffId }),
      });
      setMessage("Lead assigned manually.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assign failed");
    }
  }

  async function assignAuto() {
    setMessage("");
    setError("");
    try {
      await api(`/api/v1/leads/${params.id}/auto-assign`, { method: "POST" });
      setMessage("Lead auto-assigned via round robin.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Auto-assign failed");
    }
  }

  if (!lead) {
    return (
      <RequireAuth roles={["super_admin", "admin", "rm"]}>
        <AppShell title="Lead"><div className="text-muted">{error || "Loading…"}</div></AppShell>
      </RequireAuth>
    );
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title={lead.name} subtitle={lead.lead_code}>
        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="glass-panel rounded-2xl p-5 lg:col-span-2">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-2xl font-semibold text-navy-900">{lead.phone}</div>
                <div className="mt-1 text-sm text-muted">{lead.email || "No email"} · {lead.location || "No location"}</div>
                <div className="mt-2 text-sm text-muted">
                  Course: {lead.course_name || "—"} · Source: {formatLabel(lead.source)}
                </div>
                <div className="mt-1 text-sm text-muted">Assigned to: {lead.assigned_staff_name || "Unassigned"}</div>
              </div>
              {lead.temperature && (
                <span className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${tempClass(lead.temperature)}`}>
                  {lead.temperature}
                </span>
              )}
            </div>
            <div className="mt-4 rounded-xl bg-cloud-50 px-3 py-2 text-sm">
              Status: <strong>{formatLabel(lead.status)}</strong> · Score: <strong>{lead.score}/100</strong>
            </div>
            {lead.notes && <p className="mt-3 text-sm text-navy-800">{lead.notes}</p>}
          </div>

          <div className="glass-panel rounded-2xl p-5">
            <h3 className="font-semibold text-navy-900">Distribute / Reassign</h3>
            <p className="mt-1 text-xs text-muted">Manual pick or next telecaller in round robin.</p>
            <select
              className="mt-3 w-full rounded-xl border border-cloud-200 px-3 py-2 text-sm"
              value={staffId}
              onChange={(e) => setStaffId(e.target.value)}
            >
              <option value="">Select telecaller</option>
              {staff.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <button
              onClick={assignManual}
              className="mt-3 w-full rounded-xl px-4 py-2.5 text-sm font-semibold"
              style={{ color: "#fff", backgroundColor: "#0a1628" }}
            >
              Assign manually
            </button>
            <button
              onClick={assignAuto}
              className="mt-2 w-full rounded-xl border border-sky-500/40 bg-sky-500/10 px-4 py-2.5 text-sm font-semibold text-sky-500"
            >
              Auto-assign (round robin)
            </button>
          </div>
        </div>

        <div className="mt-5">
          <h3 className="mb-3 font-semibold text-navy-900">Activity timeline</h3>
          <div className="space-y-3">
            {(lead.activities || [])
              .slice()
              .reverse()
              .map((a: any) => (
                <div key={a.id} className="glass-panel rounded-2xl p-4 text-sm">
                  <div className="font-medium text-navy-900">
                    {new Date(a.created_at).toLocaleString()} — {formatLabel(a.activity_type)}
                  </div>
                  {a.feedback && <p className="mt-1 text-muted">{a.feedback}</p>}
                </div>
              ))}
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
