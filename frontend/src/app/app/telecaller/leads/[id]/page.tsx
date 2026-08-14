"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Phone } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatLabel, tempClass } from "@/lib/utils";

const OUTCOMES = [
  "connected",
  "not_answered",
  "busy",
  "switched_off",
  "wrong_number",
  "call_later",
] as const;

const TEMPS = ["hot", "warm", "cold"] as const;

export default function TelecallerLeadDetail() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [lead, setLead] = useState<any>(null);
  const [step, setStep] = useState<"ready" | "outcome" | "details">("ready");
  const [outcome, setOutcome] = useState<string>("connected");
  const [temperature, setTemperature] = useState<string>("warm");
  const [feedback, setFeedback] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [notInterested, setNotInterested] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const res = await api(`/api/v1/leads/${params.id}`);
    setLead(res.data);
  }

  useEffect(() => {
    load();
  }, [params.id]);

  async function save() {
    setSaving(true);
    setMessage("");
    try {
      await api(`/api/v1/leads/${params.id}/activities`, {
        method: "POST",
        body: JSON.stringify({
          call_outcome: outcome,
          temperature: outcome === "connected" && !notInterested ? temperature : null,
          feedback: feedback || null,
          next_follow_up_at: followUp ? new Date(followUp).toISOString() : null,
          not_interested: notInterested,
          duration_seconds: outcome === "connected" ? 240 : 0,
        }),
      });
      setMessage("Saved");
      await load();
      setStep("ready");
      setFeedback("");
      setFollowUp("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  if (!lead) {
    return (
      <RequireAuth roles={["telecaller"]}>
        <AppShell title="Lead"><div className="text-muted">Loading…</div></AppShell>
      </RequireAuth>
    );
  }

  return (
    <RequireAuth roles={["telecaller"]}>
      <AppShell title={lead.name} subtitle={lead.lead_code}>
        <div className="glass-panel rounded-3xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <a href={`tel:${lead.phone}`} className="text-2xl font-semibold text-navy-900">
                {lead.phone}
              </a>
              <div className="mt-2 text-sm text-muted">
                Course: {lead.course_name || "—"} · Source: {formatLabel(lead.source)}
              </div>
              <div className="mt-1 text-sm text-muted">Assigned to: {lead.assigned_staff_name || "You"}</div>
            </div>
            {lead.temperature && (
              <span className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${tempClass(lead.temperature)}`}>
                {lead.temperature}
              </span>
            )}
          </div>

          <div className="mt-4 rounded-xl bg-cloud-50 px-3 py-2 text-sm">
            Lead Score: <strong>{lead.score}/100</strong> {lead.score >= 70 ? "🔥" : ""}
          </div>

          {step === "ready" && (
            <a
              href={`tel:${lead.phone}`}
              onClick={() => setStep("outcome")}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-sky-500 px-4 py-4 text-lg font-semibold text-white shadow-lg shadow-sky-500/25"
            >
              <Phone className="h-5 w-5" /> CALL NOW
            </a>
          )}

          {step === "outcome" && (
            <div className="mt-6 space-y-3 animate-rise">
              <h3 className="font-semibold text-navy-900">Call Outcome</h3>
              <div className="grid grid-cols-2 gap-2">
                {OUTCOMES.map((o) => (
                  <button
                    key={o}
                    onClick={() => {
                      setOutcome(o);
                      if (o === "connected") setStep("details");
                      else {
                        setTemperature("");
                        setStep("details");
                      }
                    }}
                    className={`rounded-xl border px-3 py-3 text-sm ${
                      outcome === o ? "border-sky-500 bg-sky-500/10" : "border-cloud-200 bg-white"
                    }`}
                  >
                    {formatLabel(o)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === "details" && (
            <div className="mt-6 space-y-4 animate-rise">
              {outcome === "connected" && (
                <>
                  <h3 className="font-semibold text-navy-900">Lead Interest</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {TEMPS.map((t) => (
                      <button
                        key={t}
                        onClick={() => {
                          setNotInterested(false);
                          setTemperature(t);
                        }}
                        className={`rounded-xl border px-3 py-3 text-sm font-semibold uppercase ${
                          temperature === t && !notInterested ? tempClass(t) + " border-transparent" : "border-cloud-200"
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                    <button
                      onClick={() => setNotInterested(true)}
                      className={`rounded-xl border px-3 py-3 text-sm col-span-2 ${
                        notInterested ? "border-hot bg-hot/10 text-hot" : "border-cloud-200"
                      }`}
                    >
                      NOT INTERESTED
                    </button>
                  </div>
                </>
              )}

              <label className="block text-sm font-medium">
                Feedback
                <textarea
                  className="mt-1.5 w-full rounded-xl border border-cloud-200 bg-white px-3 py-2.5 text-sm"
                  rows={4}
                  placeholder="Student completed 12th and is interested in CPL…"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                />
              </label>

              <label className="block text-sm font-medium">
                Next Follow-up
                <input
                  type="datetime-local"
                  className="mt-1.5 w-full rounded-xl border border-cloud-200 bg-white px-3 py-2.5 text-sm"
                  value={followUp}
                  onChange={(e) => setFollowUp(e.target.value)}
                />
              </label>

              <button
                disabled={saving}
                onClick={save}
                className="w-full rounded-2xl bg-navy-900 py-3.5 font-semibold text-white disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button onClick={() => setStep("ready")} className="w-full text-sm text-muted">
                Cancel
              </button>
            </div>
          )}

          {message && <p className="mt-3 text-sm text-sky-500">{message}</p>}
        </div>

        <div className="mt-5">
          <h3 className="mb-3 font-semibold text-navy-900">Activity History</h3>
          <div className="space-y-3">
            {(lead.activities || [])
              .slice()
              .reverse()
              .map((a: any) => (
                <div key={a.id} className="glass-panel rounded-2xl p-4 text-sm">
                  <div className="font-medium text-navy-900">
                    {new Date(a.created_at).toLocaleString()} — {formatLabel(a.activity_type)}
                    {a.duration_seconds ? ` — ${Math.round(a.duration_seconds / 60)} min` : ""}
                  </div>
                  {a.feedback && <p className="mt-1 text-muted">{a.feedback}</p>}
                  {a.temperature && (
                    <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[11px] uppercase ${tempClass(a.temperature)}`}>
                      {a.temperature}
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>

        <button onClick={() => router.back()} className="mt-4 text-sm text-muted">
          ← Back
        </button>
      </AppShell>
    </RequireAuth>
  );
}
