"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Slip = {
  staff_id: string;
  employee_code: string;
  name: string;
  email: string;
  month_key: string;
  base_salary: number;
  total_deductions: number;
  net_salary: number;
  late_days: number;
  warnings: number;
  present_days: number;
  deductions: { type: string; amount: number; reason: string }[];
};

export default function SalaryPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [items, setItems] = useState<Slip[]>([]);
  const [error, setError] = useState("");
  const isAdmin = ["super_admin", "admin", "accountant"].includes(user?.role.name || "");

  async function load() {
    const res = await api<{ items: Slip[] }>(`/api/v1/punch/salary?month=${month}`);
    setItems(res.data.items);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [month]);

  function downloadCsv() {
    window.open(`/api/v1/punch/salary/download?month=${month}`, "_blank");
  }

  return (
    <RequireAuth>
      <AppShell
        title="Monthly Salary"
        subtitle="Attendance-based salary with late & grooming deductions"
      >
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <label className="text-sm">
            Month{" "}
            <input
              type="month"
              className="ml-2 rounded-lg border border-cloud-200 px-2 py-1.5"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            />
          </label>
          {isAdmin && (
            <button
              type="button"
              className="rounded-xl px-4 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: "#0a1628" }}
              onClick={() => {
                const token = localStorage.getItem("caa_access");
                fetch(`/api/v1/punch/salary/download?month=${month}`, {
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                })
                  .then(async (r) => {
                    if (!r.ok) throw new Error("Download failed");
                    const blob = await r.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `salary-${month}.csv`;
                    a.click();
                    URL.revokeObjectURL(url);
                  })
                  .catch((err) => setError(err.message));
              }}
            >
              Download CSV
            </button>
          )}
        </div>
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        <div className="space-y-4">
          {items.map((s) => (
            <div key={s.staff_id} className="rounded-2xl border border-cloud-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-navy-900">
                    {s.name} <span className="text-muted">({s.employee_code})</span>
                  </div>
                  <div className="text-sm text-muted">{s.email}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs uppercase tracking-wide text-muted">Net salary</div>
                  <div className="text-2xl font-semibold text-navy-900">₹{s.net_salary.toLocaleString()}</div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-5">
                <div>
                  <div className="text-muted">Base</div>
                  <div>₹{s.base_salary.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-muted">Present</div>
                  <div>{s.present_days} days</div>
                </div>
                <div>
                  <div className="text-muted">Late / warnings</div>
                  <div>
                    {s.late_days} / {s.warnings}
                  </div>
                </div>
                <div>
                  <div className="text-muted">Deductions</div>
                  <div className="text-red-600">−₹{s.total_deductions.toLocaleString()}</div>
                </div>
              </div>
              {s.deductions?.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm text-muted">
                  {s.deductions.map((d, i) => (
                    <li key={`${d.type}-${i}`}>
                      <span className="font-medium text-navy-800">{d.type}</span>: ₹{d.amount} — {d.reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          {items.length === 0 && <p className="text-sm text-muted">No salary rows for this month</p>}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
