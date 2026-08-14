"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function AdminDocumentsPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [studentId, setStudentId] = useState("");
  const [docs, setDocs] = useState<any[]>([]);
  const [certs, setCerts] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [docForm, setDocForm] = useState({ title: "", document_type: "certificate", file: null as File | null });
  const [certForm, setCertForm] = useState({ title: "", course_id: "", completion_date: "", file: null as File | null });

  useEffect(() => {
    api<{ items: any[] }>("/api/v1/students").then((r) => {
      setStudents(r.data.items);
      if (r.data.items[0]) setStudentId(r.data.items[0].id);
    }).catch(() => null);
    api<{ items: any[] }>("/api/v1/courses").then((r) => setCourses(r.data.items)).catch(() => null);
  }, []);

  async function loadStudentAssets(id: string) {
    if (!id) return;
    const [d, c] = await Promise.all([
      api<{ items: any[] }>(`/api/v1/students/${id}/documents`),
      api<{ items: any[] }>(`/api/v1/students/${id}/certificates`),
    ]);
    setDocs(d.data.items);
    setCerts(c.data.items);
  }

  useEffect(() => {
    loadStudentAssets(studentId).catch(() => {
      setDocs([]);
      setCerts([]);
    });
  }, [studentId]);

  async function uploadDoc(e: React.FormEvent) {
    e.preventDefault();
    if (!studentId || !docForm.file) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const body = new FormData();
      body.append("file", docForm.file);
      body.append("title", docForm.title);
      body.append("document_type", docForm.document_type);
      await api(`/api/v1/students/${studentId}/documents`, { method: "POST", body });
      setDocForm({ title: "", document_type: "certificate", file: null });
      setMessage("Document uploaded.");
      await loadStudentAssets(studentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function issueCert(e: React.FormEvent) {
    e.preventDefault();
    if (!studentId) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const body = new FormData();
      body.append("title", certForm.title);
      body.append("course_id", certForm.course_id);
      body.append("completion_date", certForm.completion_date);
      if (certForm.file) body.append("file", certForm.file);
      await api(`/api/v1/students/${studentId}/certificates`, { method: "POST", body });
      setCertForm({ title: "", course_id: courses[0]?.id || "", completion_date: "", file: null });
      setMessage("Certificate issued.");
      await loadStudentAssets(studentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Issue failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteDoc(id: string) {
    if (!confirm("Delete this document?")) return;
    await api(`/api/v1/documents/${id}`, { method: "DELETE" });
    await loadStudentAssets(studentId);
  }

  async function deleteCert(id: string) {
    if (!confirm("Delete this certificate?")) return;
    await api(`/api/v1/certificates/${id}`, { method: "DELETE" });
    await loadStudentAssets(studentId);
  }

  return (
    <RequireAuth roles={["super_admin", "admin"]}>
      <AppShell title="Student Documents" subtitle="Upload certificates and files for students">
        <label className="mb-4 block text-sm font-medium">
          Student
          <select className="mt-1 w-full max-w-md rounded-xl border border-cloud-200 px-3 py-2.5" value={studentId} onChange={(e) => setStudentId(e.target.value)}>
            {students.map((s) => (
              <option key={s.id} value={s.id}>{s.name} · {s.student_code}</option>
            ))}
          </select>
        </label>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="grid gap-5 lg:grid-cols-2">
          <form onSubmit={uploadDoc} className="glass-panel rounded-2xl p-5">
            <h2 className="font-semibold text-navy-900">Upload document</h2>
            <div className="mt-3 grid gap-3">
              <input required placeholder="Title" className="rounded-xl border border-cloud-200 px-3 py-2" value={docForm.title} onChange={(e) => setDocForm({ ...docForm, title: e.target.value })} />
              <select className="rounded-xl border border-cloud-200 px-3 py-2" value={docForm.document_type} onChange={(e) => setDocForm({ ...docForm, document_type: e.target.value })}>
                <option value="certificate">Certificate</option>
                <option value="id_proof">ID proof</option>
                <option value="medical">Medical</option>
                <option value="transcript">Transcript</option>
                <option value="general">General</option>
              </select>
              <input required type="file" onChange={(e) => setDocForm({ ...docForm, file: e.target.files?.[0] || null })} />
              <button disabled={busy} className="rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                Upload
              </button>
            </div>
          </form>

          <form onSubmit={issueCert} className="glass-panel rounded-2xl p-5">
            <h2 className="font-semibold text-navy-900">Issue certificate</h2>
            <div className="mt-3 grid gap-3">
              <input required placeholder="Certificate title" className="rounded-xl border border-cloud-200 px-3 py-2" value={certForm.title} onChange={(e) => setCertForm({ ...certForm, title: e.target.value })} />
              <select required className="rounded-xl border border-cloud-200 px-3 py-2" value={certForm.course_id} onChange={(e) => setCertForm({ ...certForm, course_id: e.target.value })}>
                <option value="">Select course</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <input required type="date" className="rounded-xl border border-cloud-200 px-3 py-2" value={certForm.completion_date} onChange={(e) => setCertForm({ ...certForm, completion_date: e.target.value })} />
              <input type="file" onChange={(e) => setCertForm({ ...certForm, file: e.target.files?.[0] || null })} />
              <button disabled={busy} className="rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                Issue certificate
              </button>
            </div>
          </form>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          <div>
            <h3 className="mb-2 font-semibold text-navy-900">Documents</h3>
            <div className="space-y-2">
              {docs.map((d) => (
                <div key={d.id} className="glass-panel flex items-center justify-between gap-2 rounded-xl px-4 py-3 text-sm">
                  <div>
                    <div className="font-medium">{d.title}</div>
                    <div className="text-xs text-muted">{d.document_type} · {d.file_name}</div>
                    {d.file_url && (
                      <a href={d.file_url} target="_blank" rel="noreferrer" className="text-xs text-sky-500">Open</a>
                    )}
                  </div>
                  <button onClick={() => deleteDoc(d.id)} className="text-xs text-red-700">Delete</button>
                </div>
              ))}
              {!docs.length && <div className="text-sm text-muted">No documents.</div>}
            </div>
          </div>
          <div>
            <h3 className="mb-2 font-semibold text-navy-900">Certificates</h3>
            <div className="space-y-2">
              {certs.map((c) => (
                <div key={c.id} className="glass-panel flex items-center justify-between gap-2 rounded-xl px-4 py-3 text-sm">
                  <div>
                    <div className="font-medium">{c.title}</div>
                    <div className="text-xs text-muted">{c.certificate_code} · {c.course}</div>
                    <a href={c.verify_url} className="text-xs text-sky-500">Verify</a>
                  </div>
                  <button onClick={() => deleteCert(c.id)} className="text-xs text-red-700">Delete</button>
                </div>
              ))}
              {!certs.length && <div className="text-sm text-muted">No certificates.</div>}
            </div>
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
