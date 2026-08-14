"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function ParentDocumentsPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [selected, setSelected] = useState("");
  const [docs, setDocs] = useState<any[]>([]);
  const [certs, setCerts] = useState<any[]>([]);

  useEffect(() => {
    api<any>("/api/v1/dashboard").then((res) => {
      const list = res.data.students || [];
      setStudents(list);
      if (list[0]) setSelected(list[0].student_id);
    }).catch(() => null);
  }, []);

  useEffect(() => {
    if (!selected) return;
    Promise.all([
      api<{ items: any[] }>(`/api/v1/students/${selected}/documents`),
      api<{ items: any[] }>(`/api/v1/students/${selected}/certificates`),
    ]).then(([d, c]) => {
      setDocs(d.data.items);
      setCerts(c.data.items);
    }).catch(() => {
      setDocs([]);
      setCerts([]);
    });
  }, [selected]);

  return (
    <RequireAuth roles={["parent"]}>
      <AppShell title="Documents" subtitle="Certificates and files for your ward">
        {students.length > 1 && (
          <select className="mb-4 w-full rounded-xl border border-cloud-200 px-3 py-2.5 text-sm" value={selected} onChange={(e) => setSelected(e.target.value)}>
            {students.map((s) => (
              <option key={s.student_id} value={s.student_id}>{s.name}</option>
            ))}
          </select>
        )}
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 font-semibold">Certificates</h2>
            <div className="space-y-2">
              {certs.map((c) => (
                <div key={c.id} className="glass-panel rounded-xl px-4 py-3 text-sm">
                  <div className="font-medium">{c.title}</div>
                  <div className="text-xs text-muted">{c.certificate_code}</div>
                  {c.file_url && <a href={c.file_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sky-500">Open file</a>}
                </div>
              ))}
              {!certs.length && <div className="text-sm text-muted">No certificates yet.</div>}
            </div>
          </section>
          <section>
            <h2 className="mb-2 font-semibold">Documents</h2>
            <div className="space-y-2">
              {docs.map((d) => (
                <div key={d.id} className="glass-panel flex justify-between rounded-xl px-4 py-3 text-sm">
                  <div>
                    <div className="font-medium">{d.title}</div>
                    <div className="text-xs text-muted">{d.document_type}</div>
                  </div>
                  {d.file_url && <a href={d.file_url} target="_blank" rel="noreferrer" className="text-sky-500">Open</a>}
                </div>
              ))}
              {!docs.length && <div className="text-sm text-muted">No documents yet.</div>}
            </div>
          </section>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
