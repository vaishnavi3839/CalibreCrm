"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

type Branch = {
  id: string;
  code: string;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  geofence_radius_m: number;
  punch_payload: string;
  qr_image?: string;
  staff_start: string;
  staff_end: string;
  student_start: string;
  student_end: string;
};

type BranchForm = {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  geofence_radius_m: number;
  maps_paste: string;
  staff_start: string;
  staff_end: string;
  student_start: string;
  student_end: string;
};

const emptyForm = (): BranchForm => ({
  name: "",
  address: "",
  latitude: 28.6139,
  longitude: 77.209,
  geofence_radius_m: 200,
  maps_paste: "",
  staff_start: "09:00",
  staff_end: "18:00",
  student_start: "09:00",
  student_end: "17:00",
});

function parseMapsPaste(value: string): { lat: number; lng: number } | null {
  const m = value.trim().match(/(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)/);
  if (!m) return null;
  const lat = Number(m[1]);
  const lng = Number(m[2]);
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
  return { lat, lng };
}

function downloadQr(branch: Branch) {
  if (!branch.qr_image) return;
  const a = document.createElement("a");
  a.href = branch.qr_image;
  a.download = `punch-qr-${branch.name.replace(/\s+/g, "-")}.png`;
  a.click();
}

export default function BranchesPage() {
  const [items, setItems] = useState<Branch[]>([]);
  const [form, setForm] = useState<BranchForm>(emptyForm());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const res = await api<{ items: Branch[] }>("/api/v1/branches");
    setItems(res.data.items);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  function applyMapsPaste(value: string, into: BranchForm): BranchForm {
    const parsed = parseMapsPaste(value);
    if (!parsed) return { ...into, maps_paste: value };
    return { ...into, maps_paste: value, latitude: parsed.lat, longitude: parsed.lng };
  }

  function openCreate() {
    setEditingId(null);
    setForm(emptyForm());
    setOpen(true);
  }

  function openEdit(b: Branch) {
    setEditingId(b.id);
    setForm({
      name: b.name,
      address: b.address || "",
      latitude: b.latitude,
      longitude: b.longitude,
      geofence_radius_m: b.geofence_radius_m,
      maps_paste: `${b.latitude}, ${b.longitude}`,
      staff_start: b.staff_start || "09:00",
      staff_end: b.staff_end || "18:00",
      student_start: b.student_start || "09:00",
      student_end: b.student_end || "17:00",
    });
    setOpen(true);
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const parsed = parseMapsPaste(form.maps_paste);
      const latitude = parsed?.lat ?? form.latitude;
      const longitude = parsed?.lng ?? form.longitude;
      const payload = {
        name: form.name,
        address: form.address || null,
        latitude,
        longitude,
        geofence_radius_m: form.geofence_radius_m,
        staff_start: form.staff_start,
        staff_end: form.staff_end,
        student_start: form.student_start,
        student_end: form.student_end,
      };

      if (editingId) {
        await api(`/api/v1/branches/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setMessage(`Saved “${form.name}”`);
      } else {
        await api("/api/v1/branches", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setMessage(`Branch “${form.name}” created with punch QR`);
      }
      setOpen(false);
      setForm(emptyForm());
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  function downloadAll() {
    items.forEach((b, i) => {
      setTimeout(() => downloadQr(b), i * 250);
    });
    setMessage(`Downloading ${items.length} branch QR codes…`);
  }

  return (
    <RequireAuth roles={["super_admin", "admin"]}>
      <AppShell
        title="Branches & Punch QR"
        subtitle="Add campus by name, set Maps location + in/out timings, download QR"
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-muted">{items.length} branches saved</p>
            <p className="text-xs text-muted">Use branch names when assigning staff/students.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {items.length > 0 && (
              <button
                type="button"
                onClick={downloadAll}
                className="rounded-xl border border-cloud-200 bg-white px-4 py-2 text-sm font-medium"
              >
                Download all QRs
              </button>
            )}
            <button
              type="button"
              onClick={openCreate}
              className="rounded-xl px-4 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: "#0a1628" }}
            >
              + Add branch
            </button>
          </div>
        </div>

        {message && <p className="mb-3 text-sm text-emerald-700">{message}</p>}
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((b) => (
            <div key={b.id} className="rounded-2xl border border-cloud-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="text-lg font-semibold text-navy-900">{b.name}</div>
                  <div className="mt-1 text-sm text-navy-800">{b.address || "No address"}</div>
                  <div className="mt-2 rounded-xl bg-cloud-50 px-3 py-2 text-xs text-muted">
                    <div>
                      Location: {b.latitude}, {b.longitude} · {b.geofence_radius_m}m
                    </div>
                    <div className="mt-1 font-medium text-navy-800">
                      Staff in/out: {b.staff_start} – {b.staff_end}
                    </div>
                    <div className="font-medium text-navy-800">
                      Student in/out: {b.student_start} – {b.student_end}
                    </div>
                  </div>
                </div>
                <div className="text-center">
                  {b.qr_image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={b.qr_image}
                      alt={`${b.name} punch QR`}
                      className="mx-auto h-36 w-36 rounded-xl border border-cloud-100 bg-white p-2"
                    />
                  ) : (
                    <div className="grid h-36 w-36 place-items-center rounded-xl border text-xs text-muted">
                      No QR
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-lg px-3 py-2 text-xs font-semibold text-white"
                  style={{ backgroundColor: "#0a1628" }}
                  onClick={() => downloadQr(b)}
                >
                  Download QR
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-cloud-200 px-3 py-2 text-xs font-medium"
                  onClick={() => openEdit(b)}
                >
                  Edit name / location / timings
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-cloud-200 px-3 py-2 text-xs"
                  onClick={async () => {
                    navigator.geolocation.getCurrentPosition(async (pos) => {
                      try {
                        await api(`/api/v1/branches/${b.id}`, {
                          method: "PUT",
                          body: JSON.stringify({
                            latitude: pos.coords.latitude,
                            longitude: pos.coords.longitude,
                          }),
                        });
                        setMessage(`GPS set for ${b.name}`);
                        await load();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "GPS update failed");
                      }
                    });
                  }}
                >
                  Use my GPS here
                </button>
              </div>
            </div>
          ))}
        </div>

        {open && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-navy-950/50 p-4">
            <form
              onSubmit={onSave}
              className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-6"
            >
              <h2 className="text-lg font-semibold text-navy-900">
                {editingId ? "Edit branch" : "Add branch"}
              </h2>
              <p className="mt-1 text-sm text-muted">
                Enter the campus name only. Set location and in/out times, then save.
              </p>

              <div className="mt-4 grid gap-3 text-sm">
                <label className="font-medium">
                  Branch name
                  <input
                    required
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Main campus address"
                  />
                </label>
                <label className="font-medium">
                  Address (optional)
                  <input
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.address}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                  />
                </label>

                <div className="rounded-xl border border-cloud-200 p-3">
                  <div className="font-medium text-navy-900">In / out timings</div>
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <label>
                      Staff start
                      <input
                        type="time"
                        required
                        className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                        value={form.staff_start}
                        onChange={(e) => setForm({ ...form, staff_start: e.target.value })}
                      />
                    </label>
                    <label>
                      Staff end
                      <input
                        type="time"
                        required
                        className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                        value={form.staff_end}
                        onChange={(e) => setForm({ ...form, staff_end: e.target.value })}
                      />
                    </label>
                    <label>
                      Student start
                      <input
                        type="time"
                        required
                        className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                        value={form.student_start}
                        onChange={(e) => setForm({ ...form, student_start: e.target.value })}
                      />
                    </label>
                    <label>
                      Student end
                      <input
                        type="time"
                        required
                        className="mt-1 w-full rounded-lg border border-cloud-200 px-2 py-2"
                        value={form.student_end}
                        onChange={(e) => setForm({ ...form, student_end: e.target.value })}
                      />
                    </label>
                  </div>
                </div>

                <label className="font-medium">
                  Paste from Google Maps
                  <input
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.maps_paste}
                    onChange={(e) => setForm(applyMapsPaste(e.target.value, form))}
                    placeholder="28.7041, 77.1025"
                  />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="font-medium">
                    Latitude
                    <input
                      type="number"
                      step="any"
                      required
                      className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                      value={form.latitude}
                      onChange={(e) => setForm({ ...form, latitude: Number(e.target.value) })}
                    />
                  </label>
                  <label className="font-medium">
                    Longitude
                    <input
                      type="number"
                      step="any"
                      required
                      className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                      value={form.longitude}
                      onChange={(e) => setForm({ ...form, longitude: Number(e.target.value) })}
                    />
                  </label>
                </div>
                <label className="font-medium">
                  Punch radius (meters)
                  <input
                    type="number"
                    className="mt-1 w-full rounded-xl border border-cloud-200 px-3 py-2"
                    value={form.geofence_radius_m}
                    onChange={(e) => setForm({ ...form, geofence_radius_m: Number(e.target.value) })}
                  />
                </label>
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  type="button"
                  className="flex-1 rounded-xl border border-cloud-200 px-4 py-2.5 text-sm"
                  onClick={() => {
                    setOpen(false);
                    setEditingId(null);
                  }}
                >
                  Cancel
                </button>
                <button
                  disabled={busy}
                  className="flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: "#0a1628" }}
                >
                  {busy ? "Saving…" : "Save branch"}
                </button>
              </div>
            </form>
          </div>
        )}
      </AppShell>
    </RequireAuth>
  );
}
