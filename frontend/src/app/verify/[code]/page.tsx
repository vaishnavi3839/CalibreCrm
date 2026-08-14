"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export default function CertificateVerifyPage() {
  const params = useParams<{ code: string }>();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/api/v1/certificates/verify/${params.code}`, {}, false)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.message));
  }, [params.code]);

  return (
    <div className="aviation-grid min-h-screen px-4 py-16">
      <div className="mx-auto max-w-lg glass-panel rounded-3xl p-8 text-center">
        <div className="text-xs uppercase tracking-[0.2em] text-sky-500">Calibre Aviation Academy</div>
        <h1 className="mt-3 font-[family-name:var(--font-display)] text-3xl text-navy-900">Certificate Verification</h1>
        {error && <p className="mt-6 text-hot">{error}</p>}
        {data && (
          <div className="mt-6 space-y-3">
            {data.verified ? (
              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-4 py-2 text-emerald-700">
                <CheckCircle2 className="h-5 w-5" /> Verified
              </div>
            ) : (
              <div className="text-hot">Invalid</div>
            )}
            <div className="text-sm text-muted">Certificate ID</div>
            <div className="font-semibold text-navy-900">{data.certificate_id}</div>
            <div className="pt-2 text-sm text-muted">Student</div>
            <div className="font-medium">{data.student_name}</div>
            <div className="pt-2 text-sm text-muted">Course</div>
            <div className="font-medium">{data.course}</div>
            <div className="pt-2 text-sm text-muted">Completion</div>
            <div className="font-medium">{data.completion_date}</div>
          </div>
        )}
      </div>
    </div>
  );
}
