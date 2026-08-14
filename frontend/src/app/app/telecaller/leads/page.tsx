"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatLabel, tempClass } from "@/lib/utils";

type Lead = {
  id: string;
  name: string;
  phone: string;
  status: string;
  temperature?: string | null;
  score: number;
  lead_code: string;
};

export default function TelecallerLeads() {
  const [leads, setLeads] = useState<Lead[]>([]);

  useEffect(() => {
    api<{ items: Lead[] }>("/api/v1/leads?limit=50").then((res) => setLeads(res.data.items));
  }, []);

  return (
    <RequireAuth roles={["telecaller"]}>
      <AppShell title="My Leads" subtitle="Tap a lead to call and update">
        <div className="space-y-3">
          {leads.map((lead) => (
            <Link
              key={lead.id}
              href={`/app/telecaller/leads/${lead.id}`}
              className="glass-panel block rounded-2xl p-4 transition active:scale-[0.99]"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-navy-900">{lead.name}</div>
                  <div className="mt-0.5 text-sm text-muted">{lead.phone}</div>
                  <div className="mt-2 text-xs text-muted">{lead.lead_code} · {formatLabel(lead.status)}</div>
                </div>
                <div className="text-right">
                  {lead.temperature && (
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${tempClass(lead.temperature)}`}>
                      {lead.temperature}
                    </span>
                  )}
                  <div className="mt-2 text-sm font-medium text-navy-800">{lead.score}/100</div>
                </div>
              </div>
            </Link>
          ))}
          {!leads.length && <div className="text-sm text-muted">No assigned leads yet.</div>}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
