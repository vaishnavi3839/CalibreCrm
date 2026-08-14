"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

type PunchResult = {
  punch_type: string;
  punched_at: string;
  is_late: boolean;
  late_minutes: number;
  on_campus: boolean | null;
  distance_m: number | null;
  grooming_ok: boolean | null;
  grooming_notes: string | null;
  grooming_issues?: string[];
  grooming_ai_ready?: boolean;
  effects: string[];
  branch?: { name: string; code: string };
};

type PunchRow = {
  id: string;
  punch_type: string;
  punched_at: string;
  is_late: boolean;
  late_minutes: number;
  on_campus: boolean | null;
  grooming_ok: boolean | null;
};

type Step = "scan" | "selfie";
type Popup = "attendance" | "grooming" | "done" | null;

export default function PunchPage() {
  const readerId = useId().replace(/:/g, "") + "-qr-reader";
  const videoRef = useRef<HTMLVideoElement>(null);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const handledRef = useRef(false);
  const [step, setStep] = useState<Step>("scan");
  const [popup, setPopup] = useState<Popup>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [qrToken, setQrToken] = useState("");
  const [cameraOn, setCameraOn] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number; accuracy?: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<PunchResult | null>(null);
  const [history, setHistory] = useState<PunchRow[]>([]);

  async function loadHistory() {
    const res = await api<{ items: PunchRow[] }>("/api/v1/punch/me");
    setHistory(res.data.items);
  }

  useEffect(() => {
    loadHistory().catch(() => undefined);
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        setCoords({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
      () => undefined,
      { enableHighAccuracy: true, timeout: 15000 }
    );
  }, []);

  async function stopScanner() {
    const scanner = scannerRef.current;
    scannerRef.current = null;
    setCameraOn(false);
    if (!scanner) return;
    try {
      if (scanner.isScanning) await scanner.stop();
    } catch {
      /* ignore */
    }
    try {
      await scanner.clear();
    } catch {
      /* ignore */
    }
  }

  async function startQrCamera() {
    setError("");
    handledRef.current = false;
    await stopScanner();

    // Ensure the reader div exists in DOM
    await new Promise((r) => setTimeout(r, 50));
    const el = document.getElementById(readerId);
    if (!el) {
      setError("Scanner view not ready. Tap Start camera again.");
      return;
    }
    el.innerHTML = "";

    try {
      const scanner = new Html5Qrcode(readerId, { verbose: false });
      scannerRef.current = scanner;

      const onSuccess = async (decoded: string) => {
        if (handledRef.current) return;
        handledRef.current = true;
        const token = decoded.trim();
        if (!token) return;
        setQrToken(token);
        setError("");
        await stopScanner();
        setPopup("attendance");
      };

      const config = {
        fps: 10,
        qrbox: (viewW: number, viewH: number) => {
          const size = Math.min(Math.floor(viewW * 0.75), Math.floor(viewH * 0.75), 280);
          return { width: size, height: size };
        },
        aspectRatio: 1,
      };

      // Try back camera first, then any camera (needed on laptops)
      const cameras = await Html5Qrcode.getCameras().catch(() => []);
      const back =
        cameras.find((c) => /back|rear|environment/i.test(c.label)) ||
        cameras[cameras.length - 1];

      try {
        if (back?.id) {
          await scanner.start(back.id, config, onSuccess, () => undefined);
        } else {
          await scanner.start({ facingMode: "environment" }, config, onSuccess, () => undefined);
        }
      } catch {
        // Fallback: first available / user-facing
        if (cameras[0]?.id) {
          await scanner.start(cameras[0].id, config, onSuccess, () => undefined);
        } else {
          await scanner.start({ facingMode: "user" }, config, onSuccess, () => undefined);
        }
      }

      setCameraOn(true);
    } catch (err) {
      setCameraOn(false);
      const msg = err instanceof Error ? err.message : "Camera failed";
      setError(
        `Could not open camera for QR scan. Allow camera permission and try again. (${msg})`
      );
    }
  }

  // Cleanup when leaving scan step / unmount
  useEffect(() => {
    return () => {
      stopScanner();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (step !== "scan") {
      stopScanner();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  // After "Attendance taken", auto-advance to grooming prompt
  useEffect(() => {
    if (popup !== "attendance") return;
    const t = window.setTimeout(() => setPopup("grooming"), 1600);
    return () => window.clearTimeout(t);
  }, [popup]);

  // After grooming prompt, open face camera (or user can tap Continue)
  useEffect(() => {
    if (popup !== "grooming") return;
    const t = window.setTimeout(() => {
      setPopup(null);
      setStep("selfie");
    }, 2200);
    return () => window.clearTimeout(t);
  }, [popup]);

  function continueToGroomingSelfie() {
    setPopup(null);
    setStep("selfie");
  }

  // Selfie camera
  useEffect(() => {
    if (step !== "selfie") return;
    let active: MediaStream | null = null;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then((s) => {
        active = s;
        setStream(s);
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError("Allow front camera for selfie"));

    return () => {
      active?.getTracks().forEach((t) => t.stop());
      setStream(null);
    };
  }, [step]);

  useEffect(() => {
    if (videoRef.current && stream) videoRef.current.srcObject = stream;
  }, [stream]);

  function captureSelfie(): Blob | null {
    const video = videoRef.current;
    if (!video) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL("image/jpeg", 0.85);
    const bin = atob(data.split(",")[1]);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new Blob([arr], { type: "image/jpeg" });
  }

  async function onPunch() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      if (!qrToken.trim()) throw new Error("Scan the branch QR first");
      const selfie = captureSelfie();
      if (!selfie) throw new Error("Could not capture selfie");

      const form = new FormData();
      form.append("qr_token", qrToken.trim());
      if (coords) {
        form.append("latitude", String(coords.lat));
        form.append("longitude", String(coords.lng));
        if (coords.accuracy != null) form.append("accuracy_m", String(coords.accuracy));
      }
      form.append("selfie", selfie, "selfie.jpg");

      const res = await api<PunchResult>("/api/v1/punch", { method: "POST", body: form });
      setResult(res.data);
      await loadHistory();
      stream?.getTracks().forEach((t) => t.stop());
      setStream(null);
      // Require a fresh QR scan for the next IN or OUT punch
      setQrToken("");
      setPopup("done");
      setStep("scan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Punch failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth>
      <AppShell title="QR Punch" subtitle="IN and OUT both need a QR scan → selfie → punch">
        {popup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/55 p-4 backdrop-blur-[2px]">
            <div className="w-full max-w-sm animate-rise rounded-2xl bg-white p-6 text-center shadow-xl">
              {popup === "attendance" ? (
                <>
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-700">
                    ✓
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-navy-900">QR verified</h3>
                  <p className="mt-2 text-sm text-muted">
                    Next: scan your face for a grooming check.
                  </p>
                </>
              ) : popup === "grooming" ? (
                <>
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-sky-100 text-2xl text-sky-800">
                    ◉
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-navy-900">
                    Scan your face for a grooming check
                  </h3>
                  <p className="mt-2 text-sm text-muted">
                    Face the camera clearly. Hair and grooming will be checked next.
                  </p>
                  <button
                    type="button"
                    onClick={continueToGroomingSelfie}
                    className="mt-5 w-full rounded-xl px-4 py-3 text-sm font-semibold text-white"
                    style={{ backgroundColor: "#0a1628" }}
                  >
                    Continue to face scan
                  </button>
                </>
              ) : (
                <>
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-700">
                    ✓
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-navy-900">Attendance taken</h3>
                  <p className="mt-2 text-sm text-muted">
                    {result
                      ? `${result.punch_type.toUpperCase()}${
                          result.is_late ? ` · LATE +${result.late_minutes}m` : " · on time"
                        }${
                          result.grooming_ok === false
                            ? " · Grooming failed"
                            : result.grooming_ok
                              ? " · Grooming OK"
                              : ""
                        }`
                      : "Punch saved successfully."}
                  </p>
                  <button
                    type="button"
                    onClick={() => setPopup(null)}
                    className="mt-5 w-full rounded-xl px-4 py-3 text-sm font-semibold text-white"
                    style={{ backgroundColor: "#0a1628" }}
                  >
                    Done
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        <div className="mb-4 flex gap-2 text-sm">
          <span
            className={`rounded-full px-3 py-1 ${step === "scan" && !popup ? "bg-navy-900 text-white" : "bg-cloud-100 text-muted"}`}
          >
            1. Scan QR (IN or OUT)
          </span>
          <span
            className={`rounded-full px-3 py-1 ${step === "selfie" || popup === "grooming" ? "bg-navy-900 text-white" : "bg-cloud-100 text-muted"}`}
          >
            2. Face / grooming
          </span>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-cloud-200 bg-white p-5">
            {step === "scan" ? (
              <>
                <h3 className="font-semibold text-navy-900">Scan branch QR</h3>
                <p className="mt-1 text-sm text-muted">
                  Scan for <strong>IN</strong> when arriving and again for <strong>OUT</strong> when leaving.
                </p>

                {result && (
                  <div className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">
                    <div>
                      Last punch: <strong>{result.punch_type.toUpperCase()}</strong>
                      {result.branch ? ` · ${result.branch.name}` : ""}
                      {result.is_late ? ` · LATE +${result.late_minutes}m` : " · on time"}
                      . Scan QR again for the next punch.
                    </div>
                    <div className="mt-1">
                      Grooming:{" "}
                      {result.grooming_ok === true
                        ? "OK"
                        : result.grooming_ok === false
                          ? "Failed"
                          : "Not checked"}
                      {result.grooming_notes ? ` — ${result.grooming_notes}` : ""}
                    </div>
                  </div>
                )}

                <div
                  id={readerId}
                  className="mt-4 min-h-[280px] overflow-hidden rounded-xl bg-black [&_video]:w-full [&_video]:rounded-xl"
                />

                {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
                {cameraOn && (
                  <p className="mt-2 text-sm text-emerald-700">Camera on — hold steady on the QR…</p>
                )}

                <button
                  type="button"
                  onClick={startQrCamera}
                  className="mt-4 w-full rounded-xl px-4 py-3 text-sm font-semibold text-white"
                  style={{ backgroundColor: "#0a1628" }}
                >
                  {cameraOn ? "Restart camera" : "Start camera & scan QR"}
                </button>
              </>
            ) : (
              <>
                <h3 className="font-semibold text-navy-900">Scan your face for grooming</h3>
                <p className="mt-1 text-sm text-muted">
                  Face the camera clearly. AI checks <strong>hair</strong>, facial grooming, and
                  professional appearance. Failed grooming = ₹500 fine (bad photo alone = retake, no fine).
                </p>
                <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                  ✓ Attendance QR verified — complete face scan to finish punch
                </p>

                <div className="mt-4 overflow-hidden rounded-xl bg-black">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="aspect-[4/3] w-full object-cover"
                  />
                </div>

                <p className="mt-2 text-xs text-muted">
                  GPS:{" "}
                  {coords
                    ? `${coords.lat.toFixed(5)}, ${coords.lng.toFixed(5)}`
                    : "waiting…"}
                </p>

                {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
                {result && (
                  <div className="mt-3 rounded-xl bg-sky-50 p-3 text-sm text-navy-900">
                    <div className="font-semibold">
                      Punched {result.punch_type.toUpperCase()}
                      {result.branch ? ` · ${result.branch.name}` : ""}
                      {result.is_late ? ` · LATE +${result.late_minutes}m` : " · on time"}
                    </div>
                    <div className="mt-1 text-muted">
                      Campus: {result.on_campus == null ? "n/a" : result.on_campus ? "Yes" : "No"}
                    </div>
                    <div className="mt-1">
                      Grooming:{" "}
                      {result.grooming_ok === true
                        ? "OK"
                        : result.grooming_ok === false
                          ? "Failed"
                          : "Not checked"}
                      {result.grooming_notes ? ` — ${result.grooming_notes}` : ""}
                      {result.grooming_issues && result.grooming_issues.length > 0
                        ? ` [${result.grooming_issues.join(", ")}]`
                        : ""}
                    </div>
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  <button
                    type="button"
                    className="rounded-xl border border-cloud-200 px-4 py-3 text-sm"
                    onClick={() => {
                      stream?.getTracks().forEach((t) => t.stop());
                      setResult(null);
                      setQrToken("");
                      setPopup(null);
                      setStep("scan");
                    }}
                  >
                    Scan again
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={onPunch}
                    className="flex-1 rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: "#0a1628" }}
                  >
                    {busy ? "Punching…" : "Punch IN / OUT"}
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="rounded-2xl border border-cloud-200 bg-white p-5">
            <h3 className="font-semibold text-navy-900">Recent punches</h3>
            <div className="mt-3 space-y-2">
              {history.length === 0 && <p className="text-sm text-muted">No punches yet</p>}
              {history.map((h) => (
                <div
                  key={h.id}
                  className="flex items-center justify-between rounded-xl border border-cloud-100 px-3 py-2 text-sm"
                >
                  <div>
                    <span className="font-medium uppercase">{h.punch_type}</span>
                    {h.is_late && <span className="ml-2 text-red-600">Late +{h.late_minutes}m</span>}
                    <div className="text-xs text-muted">{new Date(h.punched_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
