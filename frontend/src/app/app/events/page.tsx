"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

const EVENT_TYPES = ["general", "open_day", "seminar", "campus", "webinar", "holiday", "other"];

export default function EventsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    title: "",
    description: "",
    event_type: "general",
    start_at: "",
    end_at: "",
    location: "",
  });

  async function load() {
    const res = await api<{ items: any[] }>("/api/v1/events");
    setItems(res.data.items);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api("/api/v1/events", {
        method: "POST",
        body: JSON.stringify({
          title: form.title,
          description: form.description || null,
          event_type: form.event_type,
          start_at: new Date(form.start_at).toISOString(),
          end_at: form.end_at ? new Date(form.end_at).toISOString() : null,
          location: form.location || null,
        }),
      });
      setMessage("Event created.");
      setForm({ title: "", description: "", event_type: "general", start_at: "", end_at: "", location: "" });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create event");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin", "admin", "rm"]}>
      <AppShell title="Events" subtitle="Academy events, open days and campus programmes">
        <div className="mb-4 flex justify-end">
          <button
            onClick={() => setOpen(true)}
            className="rounded-xl px-4 py-2.5 text-sm font-semibold"
            style={{ color: "#fff", backgroundColor: "#0a1628" }}
          >
            + Add Event
          </button>
        </div>

        {message && <div className="mb-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
        {error && <div className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="space-y-3">
          {items.map((ev) => (
            <div key={ev.id} className="glass-panel rounded-2xl p-5 transition hover:-translate-y-0.5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-xs uppercase tracking-wider text-brass-500">{ev.event_type}</div>
                  <h3 className="mt-1 text-lg font-semibold text-navy-900">{ev.title}</h3>
                  {ev.description && <p className="mt-1 text-sm text-muted">{ev.description}</p>}
                </div>
                <div className="text-right text-sm text-muted">
                  <div>{new Date(ev.start_at).toLocaleString()}</div>
                  {ev.location && <div className="mt-1">{ev.location}</div>}
                </div>
              </div>
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No upcoming events yet.</div>}
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form onSubmit={onCreate} className="glass-panel max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl p-6">
              <h2 className="text-lg font-semibold text-navy-900">Add Event</h2>
              <div className="mt-4 grid gap-3">
                <label className="text-sm font-medium">
                  Title *
                  <input required className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Type
                  <select className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })}>
                    {EVENT_TYPES.map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium">
                  Starts *
                  <input required type="datetime-local" className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.start_at} onChange={(e) => setForm({ ...form, start_at: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Ends
                  <input type="datetime-local" className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.end_at} onChange={(e) => setForm({ ...form, end_at: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Location
                  <input className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
                </label>
                <label className="text-sm font-medium">
                  Description
                  <textarea rows={3} className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                </label>
              </div>
              <div className="mt-5 flex gap-2">
                <button type="button" onClick={() => setOpen(false)} className="flex-1 rounded-xl border border-cloud-200 px-4 py-2.5 text-sm">Cancel</button>
                <button disabled={busy} className="flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                  {busy ? "Saving…" : "Create event"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
