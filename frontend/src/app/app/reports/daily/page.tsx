"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { TopPerformerSpotlight } from "@/components/Brand";
import { FieldRow } from "@/components/FieldRow";
import { api } from "@/lib/api";

type Report = {
  date: string;
  staff_count: number;
  totals: Record<string, number>;
  top_performer?: any;
  items: any[];
};

export default function DailyReportPage() {
  const [report, setReport] = useState<Report | null>(null);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState("");

  async function load(d = date) {
    setError("");
    try {
      const res = await api<Report>(`/api/v1/staff/daily-report?date=${d}`);
      setReport(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title="Daily Staff Report" subtitle="Outcome-based productivity for the selected day">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="text-sm font-medium text-navy-800">
            Report date
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-1 block rounded-xl border border-cloud-200 bg-white px-3 py-2"
            />
          </label>
          <button onClick={() => load(date)} className="rounded-xl bg-navy-900 px-4 py-2.5 text-sm font-semibold text-white">
            Load report
          </button>
        </div>

        {error && <div className="mb-3 text-sm text-red-600">{error}</div>}

        {report && (
          <div className="space-y-5">
            <TopPerformerSpotlight performer={report.top_performer} />

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Staff reported", report.staff_count],
                ["Calls", report.totals.calls_completed],
                ["Follow-ups done", report.totals.followups_completed],
                ["Admissions", report.totals.admissions],
              ].map(([label, value]) => (
                <div key={String(label)} className="glass-panel rounded-2xl p-4">
                  <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
                  <div className="mt-1 text-2xl font-semibold text-navy-900">{value}</div>
                </div>
              ))}
            </div>

            <div className="space-y-3 md:hidden">
              {report.items.map((row) => (
                <div key={row.staff_id} className="glass-panel rounded-2xl p-4">
                  <div className="flex items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={row.photo_url} alt="" className="h-10 w-10 rounded-full object-cover" />
                    <div className="min-w-0">
                      <div className="font-semibold text-navy-900">{row.name}</div>
                      <div className="text-xs capitalize text-muted">{row.role}</div>
                    </div>
                    <div className="ml-auto font-semibold text-brass-500">{row.score}</div>
                  </div>
                  <dl className="mt-3 space-y-2 border-t border-cloud-100 pt-3">
                    <FieldRow label="Calls" value={row.calls_completed} />
                    <FieldRow label="Connected" value={row.connected_calls} />
                    <FieldRow label="Follow-ups" value={row.followups_completed} />
                    <FieldRow label="Missed" value={<span className="text-hot">{row.followups_missed}</span>} />
                    <FieldRow label="Hot leads" value={row.hot_leads} />
                    <FieldRow label="Registrations" value={row.registrations} />
                    <FieldRow label="Admissions" value={row.admissions} />
                  </dl>
                </div>
              ))}
              {!report.items.length && (
                <div className="rounded-2xl border border-dashed border-cloud-200 px-4 py-8 text-center text-sm text-muted">
                  No performance rows for this date yet.
                </div>
              )}
            </div>

            <div className="glass-panel hidden overflow-hidden rounded-2xl md:block">
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-cloud-50 text-xs uppercase tracking-wider text-muted">
                    <tr>
                      <th className="px-4 py-3">Staff</th>
                      <th className="px-4 py-3">Calls</th>
                      <th className="px-4 py-3">Connected</th>
                      <th className="px-4 py-3">Follow-ups</th>
                      <th className="px-4 py-3">Missed</th>
                      <th className="px-4 py-3">Hot</th>
                      <th className="px-4 py-3">Reg</th>
                      <th className="px-4 py-3">Adm</th>
                      <th className="px-4 py-3">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.items.map((row) => (
                      <tr key={row.staff_id} className="border-t border-cloud-100">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={row.photo_url} alt={row.name} className="h-9 w-9 rounded-full object-cover" />
                            <div>
                              <div className="font-medium text-navy-900">{row.name}</div>
                              <div className="text-xs capitalize text-muted">{row.role}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">{row.calls_completed}</td>
                        <td className="px-4 py-3">{row.connected_calls}</td>
                        <td className="px-4 py-3">{row.followups_completed}</td>
                        <td className="px-4 py-3 text-hot">{row.followups_missed}</td>
                        <td className="px-4 py-3">{row.hot_leads}</td>
                        <td className="px-4 py-3">{row.registrations}</td>
                        <td className="px-4 py-3">{row.admissions}</td>
                        <td className="px-4 py-3 font-semibold text-brass-500">{row.score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!report.items.length && (
                <div className="px-4 py-8 text-center text-sm text-muted">No performance rows for this date yet.</div>
              )}
            </div>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
