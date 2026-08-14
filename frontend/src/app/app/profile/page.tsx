"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function avatarFallback(name: string) {
  return `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(name.replace(/\s/g, ""))}&backgroundColor=0a1628`;
}

export default function ProfilePage() {
  const { user, refreshMe, logout } = useAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [pwd, setPwd] = useState({ current: "", next: "", confirm: "" });

  async function onUpload(file: File | null) {
    if (!file || !user) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await api<any>("/api/v1/auth/me/photo", { method: "POST", body });
      setPreview(res.data.photo_url);
      await refreshMe();
      setMessage("Profile photo updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onChangePassword(e: React.FormEvent) {
    e.preventDefault();
    if (pwd.next !== pwd.confirm) {
      setError("New passwords do not match");
      return;
    }
    if (pwd.next.length < 8) {
      setError("New password must be at least 8 characters");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api("/api/v1/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: pwd.current,
          new_password: pwd.next,
        }),
      });
      setPwd({ current: "", next: "", confirm: "" });
      setMessage("Password changed successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password");
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  const photo = preview || user.photo_url || avatarFallback(user.full_name);

  return (
    <RequireAuth>
      <AppShell title="My Profile" subtitle="Photo, password and account">
        <div className="mx-auto max-w-lg space-y-4">
          {message && <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
          {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

          <div className="glass-panel rounded-3xl p-6 text-center">
            <div className="relative mx-auto h-36 w-36">
              <div className="absolute -inset-1 rounded-full bg-gradient-to-br from-brass-400 via-sky-400 to-brass-500 opacity-70 blur-sm" />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo}
                alt={user.full_name}
                className="relative h-full w-full rounded-full border-4 border-white object-cover shadow-lg"
              />
            </div>
            <h2 className="mt-4 font-[family-name:var(--font-display)] text-2xl text-navy-900">{user.full_name}</h2>
            <p className="text-sm text-muted">{user.role.display_name}</p>
            <p className="mt-1 text-sm text-muted">{user.email}</p>

            <label className="mt-5 inline-flex cursor-pointer rounded-xl px-5 py-2.5 text-sm font-semibold" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
              {busy ? "Uploading…" : "Upload photo"}
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                className="hidden"
                disabled={busy}
                onChange={(e) => onUpload(e.target.files?.[0] || null)}
              />
            </label>
            <p className="mt-2 text-xs text-muted">JPEG, PNG, WebP or GIF · max 5 MB</p>
          </div>

          <form onSubmit={onChangePassword} className="glass-panel rounded-3xl p-6 text-left">
            <h3 className="font-semibold text-navy-900">Change password</h3>
            <div className="mt-3 grid gap-3">
              <input
                required
                type="password"
                placeholder="Current password"
                className="rounded-xl border border-cloud-200 px-3 py-2 text-sm"
                value={pwd.current}
                onChange={(e) => setPwd({ ...pwd, current: e.target.value })}
              />
              <input
                required
                type="password"
                placeholder="New password"
                className="rounded-xl border border-cloud-200 px-3 py-2 text-sm"
                value={pwd.next}
                onChange={(e) => setPwd({ ...pwd, next: e.target.value })}
              />
              <input
                required
                type="password"
                placeholder="Confirm new password"
                className="rounded-xl border border-cloud-200 px-3 py-2 text-sm"
                value={pwd.confirm}
                onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })}
              />
              <button disabled={busy} className="rounded-xl py-2.5 text-sm font-semibold disabled:opacity-60" style={{ color: "#fff", backgroundColor: "#0a1628" }}>
                Update password
              </button>
            </div>
          </form>

          <button
            type="button"
            onClick={async () => {
              await logout();
              router.push("/login");
            }}
            className="w-full rounded-xl border border-cloud-200 px-4 py-2.5 text-sm font-medium text-navy-900"
          >
            Sign out
          </button>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
