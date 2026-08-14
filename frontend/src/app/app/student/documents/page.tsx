"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function StudentDocuments() {
  const [docs, setDocs] = useState<any[]>([]);
  const [certs, setCerts] = useState<any[]>([]);

  useEffect(() => {
    api<any>("/api/v1/students/me/profile")
      .then(async (profile) => {
        const id = profile.data.id;
        const [d, c] = await Promise.all([
          api<{ items: any[] }>(`/api/v1/students/${id}/documents`),
          api<{ items: any[] }>(`/api/v1/students/${id}/certificates`),
        ]);
        setDocs(d.data.items);
        setCerts(c.data.items);
      })
      .catch(() => null);
  }, []);

  return (
    <RequireAuth roles={["student"]}>
      <AppShell title="Documents & Certificates" subtitle="Files uploaded by the academy for you">
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 font-semibold text-navy-900">Certificates</h2>
            <div className="space-y-2">
              {certs.map((c) => (
                <div key={c.id} className="glass-panel rounded-xl px-4 py-3 text-sm">
                  <div className="font-medium text-navy-900">{c.title}</div>
                  <div className="text-xs text-muted">{c.certificate_code} · {c.course} · {c.completion_date}</div>
                  <div className="mt-2 flex flex-wrap gap-3">
                    {c.file_url && (
                      <a href={c.file_url} target="_blank" rel="noreferrer" className="font-medium text-sky-500">
                        Open / download file
                      </a>
                    )}
                    <a href={c.verify_url} className="text-sky-500">Verify publicly</a>
                  </div>
                </div>
              ))}
              {!certs.length && <div className="text-sm text-muted">No certificates uploaded yet.</div>}
            </div>
          </section>
          <section>
            <h2 className="mb-2 font-semibold text-navy-900">Documents</h2>
            <div className="space-y-2">
              {docs.map((d) => (
                <div key={d.id} className="glass-panel flex flex-wrap items-center justify-between gap-2 rounded-xl px-4 py-3 text-sm">
                  <div>
                    <div className="font-medium">{d.title}</div>
                    <div className="text-xs text-muted">{d.document_type} · {d.file_name}</div>
                  </div>
                  {d.can_download && d.file_url && (
                    <a href={d.file_url} target="_blank" rel="noreferrer" className="font-medium text-sky-500">
                      Open file
                    </a>
                  )}
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
