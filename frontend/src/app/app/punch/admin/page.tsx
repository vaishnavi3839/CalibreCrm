"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

type Settings = {
  staff_start: string;
  staff_end: string;
  student_start: string;
  student_end: string;
  late_grace_minutes: number;
  staff_late_warnings_for_half_day: number;
  staff_warnings_for_half_salary: number;
  grooming_fine: number;
  working_days_per_month: number;
  academy_lat: number;
  academy_lng: number;
  geofence_radius_m: number;
  require_selfie: boolean;
  require_gps_for_staff: boolean;
  grooming_ai_ready?: boolean;
  grooming_ai_provider?: string | null;
  grooming_ai_model?: string | null;
};

type Presence = {
  staff_id: string;
  name: string;
  employee_code: string;
  status: string;
  last_punched_at?: string;
  on_campus?: boolean | null;
  distance_m?: number | null;
};

export default function PunchAdminPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [qrImage, setQrImage] = useState("");
  const [qrPayload, setQrPayload] = useState("");
  const [presence, setPresence] = useState<Presence[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [s, q, p] = await Promise.all([
      api<Settings>("/api/v1/punch/settings"),
      api<{ qr_image: string; payload: string }>("/api/v1/punch/qr"),
      api<{ items: Presence[] }>("/api/v1/punch/presence"),
    ]);
    setSettings(s.data);
    setQrImage(q.data.qr_image);
    setQrPayload(q.data.payload);
    setPresence(p.data.items);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setBusy(true);
    setError("");
    try {
      const res = await api<Settings>("/api/v1/punch/settings", {
        method: "PUT",
        body: JSON.stringify(settings),
      });
      setSettings(res.data);
      setMessage("Settings saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function rotateQr() {
    setBusy(true);
    try {
      const res = await api<{ qr_image: string; payload: string }>("/api/v1/punch/qr/rotate", {
        method: "POST",
      });
      setQrImage(res.data.qr_image);
      setQrPayload(res.data.payload);
      setMessage("QR rotated — print/display the new code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rotate failed");
    } finally {
      setBusy(false);
    }
  }

  function useMyLocation() {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setSettings((s) =>
          s
            ? {
                ...s,
                academy_lat: pos.coords.latitude,
                academy_lng: pos.coords.longitude,
              }
            : s
        );
      },
      () => setError("Could not read location"),
      { enableHighAccuracy: true }
    );
  }

  if (!settings) {
    return (
      <RequireAuth roles={["super_admin", "admin"]}>
        <AppShell title="Punch & GPS settings">{error || "Loading…"}</AppShell>
      </RequireAuth>
    );
  }

  return (
    <RequireAuth roles={["super_admin", "admin"]}>
      <AppShell title="Punch Control" subtitle="QR display, timings, academy GPS, late & salary rules">
        {message && <p className="mb-3 text-sm text-emerald-700">{message}</p>}
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        <div
          className={`mb-4 rounded-xl border p-3 text-sm ${
            settings.grooming_ai_ready
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-amber-200 bg-amber-50 text-amber-950"
          }`}
        >
          {settings.grooming_ai_ready ? (
            <>
              Grooming AI is <strong>on</strong> ({settings.grooming_ai_provider} ·{" "}
              {settings.grooming_ai_model}). Selfies are checked for hair, facial grooming, and
              appearance.
            </>
          ) : (
            <>
              Grooming AI is <strong>off</strong> — hair/appearance are not checked yet. Add{" "}
              <code className="rounded bg-white/70 px-1">GEMINI_API_KEY</code> (free from{" "}
              <a
                className="underline"
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
              >
                Google AI Studio
              </a>
              ) to backend <code className="rounded bg-white/70 px-1">.env</code>, then restart the
              API.
            </>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-cloud-200 bg-white p-5 text-center">
            <h3 className="font-semibold text-navy-900">Academy Punch QR</h3>
            <p className="mt-1 text-sm text-muted">Display this at the gate for everyone to scan</p>
            {qrImage && <img src={qrImage} alt="Punch QR" className="mx-auto mt-4 h-56 w-56" />}
            <p className="mt-2 break-all text-xs text-muted">{qrPayload}</p>
            <button
              type="button"
              disabled={busy}
              onClick={rotateQr}
              className="mt-4 rounded-xl border border-cloud-200 px-4 py-2 text-sm font-medium"
            >
              Rotate QR
            </button>
          </div>

          <form onSubmit={saveSettings} className="rounded-2xl border border-cloud-200 bg-white p-5">
            <h3 className="font-semibold text-navy-900">Timings & rules</h3>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              {(
                [
                  ["staff_start", "Staff start"],
                  ["staff_end", "Staff end"],
                  ["student_start", "Student start"],
                  ["student_end", "Student end"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block">
                  {label}
                  <input
                    type="time"
                    className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                    value={settings[key]}
                    onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
                  />
                </label>
              ))}
              <label className="block">
                Grace (min)
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.late_grace_minutes}
                  onChange={(e) =>
                    setSettings({ ...settings, late_grace_minutes: Number(e.target.value) })
                  }
                />
              </label>
              <label className="block">
                Late → half-day cut after
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.staff_late_warnings_for_half_day}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      staff_late_warnings_for_half_day: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label className="block">
                Warnings → half salary after
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.staff_warnings_for_half_salary}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      staff_warnings_for_half_salary: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label className="block">
                Grooming fine (₹)
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.grooming_fine}
                  onChange={(e) => setSettings({ ...settings, grooming_fine: Number(e.target.value) })}
                />
              </label>
            </div>

            <h4 className="mt-5 font-medium text-navy-900">Academy GPS geofence</h4>
            <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
              <label className="block">
                Latitude
                <input
                  type="number"
                  step="any"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.academy_lat}
                  onChange={(e) => setSettings({ ...settings, academy_lat: Number(e.target.value) })}
                />
              </label>
              <label className="block">
                Longitude
                <input
                  type="number"
                  step="any"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.academy_lng}
                  onChange={(e) => setSettings({ ...settings, academy_lng: Number(e.target.value) })}
                />
              </label>
              <label className="block col-span-2">
                Radius (meters)
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                  value={settings.geofence_radius_m}
                  onChange={(e) =>
                    setSettings({ ...settings, geofence_radius_m: Number(e.target.value) })
                  }
                />
              </label>
            </div>
            <button type="button" onClick={useMyLocation} className="mt-2 text-sm text-sky-700 underline">
              Use my current location as academy
            </button>

            <button
              type="submit"
              disabled={busy}
              className="mt-5 w-full rounded-xl px-4 py-3 text-sm font-semibold text-white"
              style={{ backgroundColor: "#0a1628" }}
            >
              Save settings
            </button>
          </form>
        </div>

        <div className="mt-6 rounded-2xl border border-cloud-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-navy-900">Staff presence (GPS)</h3>
            <button type="button" className="text-sm text-sky-700" onClick={() => load().catch(() => undefined)}>
              Refresh
            </button>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="py-2">Code</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Last punch</th>
                  <th>Distance</th>
                </tr>
              </thead>
              <tbody>
                {presence.map((p) => (
                  <tr key={p.staff_id} className="border-t border-cloud-100">
                    <td className="py-2">{p.employee_code}</td>
                    <td>{p.name}</td>
                    <td className="capitalize">{p.status.replaceAll("_", " ")}</td>
                    <td>{p.last_punched_at ? new Date(p.last_punched_at).toLocaleString() : "—"}</td>
                    <td>{p.distance_m != null ? `${Math.round(p.distance_m)}m` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
